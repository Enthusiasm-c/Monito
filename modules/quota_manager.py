#!/usr/bin/env python3
"""
MON-S03: Quota-Aware Concurrency Manager
Система управления квотами и лимитами для масштабируемой обработки
"""

import time
import json
import threading
from typing import Dict, Any, Optional, Union, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

# Redis imports for distributed quotas
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Logging setup с fallback
try:
    import structlog
    # Простая конфигурация structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger(__name__)
    STRUCTLOG_AVAILABLE = True
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    STRUCTLOG_AVAILABLE = False

@dataclass
class QuotaLimits:
    """Определение лимитов квот"""
    max_files_per_hour: int = 50        # Максимум файлов в час
    max_files_per_day: int = 200        # Максимум файлов в день
    max_concurrent_tasks: int = 3       # Максимум параллельных задач
    max_file_size_mb: float = 10.0      # Максимум размер файла в MB
    max_queue_size: int = 10            # Максимум файлов в очереди
    
    # Rate limiting
    requests_per_minute: int = 30       # Максимум запросов в минуту
    
    # Resource protection
    max_memory_mb: int = 500            # Максимум памяти на пользователя
    max_cpu_percent: float = 50.0       # Максимум CPU на пользователя
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь"""
        return {
            'max_files_per_hour': self.max_files_per_hour,
            'max_files_per_day': self.max_files_per_day,
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'max_file_size_mb': self.max_file_size_mb,
            'max_queue_size': self.max_queue_size,
            'requests_per_minute': self.requests_per_minute,
            'max_memory_mb': self.max_memory_mb,
            'max_cpu_percent': self.max_cpu_percent
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuotaLimits':
        """Создает из словаря"""
        return cls(**data)

@dataclass
class UserQuotaUsage:
    """Текущее использование квот пользователем"""
    user_id: str
    files_processed_hour: int = 0       # Файлов обработано за час
    files_processed_day: int = 0        # Файлов обработано за день
    active_tasks: int = 0               # Активных задач
    queue_size: int = 0                 # Размер очереди
    
    # Rate limiting tracking
    requests_this_minute: int = 0       # Запросов в текущую минуту
    last_request_time: float = field(default_factory=time.time)
    
    # Resource usage
    memory_usage_mb: float = 0.0        # Использование памяти
    cpu_usage_percent: float = 0.0      # Использование CPU
    
    # Time tracking
    hour_window_start: float = field(default_factory=time.time)
    day_window_start: float = field(default_factory=time.time)
    minute_window_start: float = field(default_factory=time.time)
    
    def reset_hour_window(self):
        """Сбрасывает окно часа"""
        self.files_processed_hour = 0
        self.hour_window_start = time.time()
    
    def reset_day_window(self):
        """Сбрасывает окно дня"""
        self.files_processed_day = 0
        self.day_window_start = time.time()
    
    def reset_minute_window(self):
        """Сбрасывает окно минуты"""
        self.requests_this_minute = 0
        self.minute_window_start = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь"""
        return {
            'user_id': self.user_id,
            'files_processed_hour': self.files_processed_hour,
            'files_processed_day': self.files_processed_day,
            'active_tasks': self.active_tasks,
            'queue_size': self.queue_size,
            'requests_this_minute': self.requests_this_minute,
            'last_request_time': self.last_request_time,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'hour_window_start': self.hour_window_start,
            'day_window_start': self.day_window_start,
            'minute_window_start': self.minute_window_start
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserQuotaUsage':
        """Создает из словаря"""
        return cls(**data)

@dataclass
class QuotaCheckResult:
    """Результат проверки квот"""
    allowed: bool
    user_id: str
    violation_reason: Optional[str] = None
    current_usage: Optional[Dict[str, Any]] = None
    limits: Optional[Dict[str, Any]] = None
    retry_after_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь"""
        return {
            'allowed': self.allowed,
            'user_id': self.user_id,
            'violation_reason': self.violation_reason,
            'current_usage': self.current_usage,
            'limits': self.limits,
            'retry_after_seconds': self.retry_after_seconds
        }

class QuotaManager:
    """Менеджер квот и лимитов конкурентности"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None,
                 default_limits: Optional[QuotaLimits] = None,
                 enable_global_limits: bool = True):
        """
        Args:
            redis_client: Redis клиент для распределенных квот
            default_limits: Лимиты по умолчанию
            enable_global_limits: Включить глобальные лимиты системы
        """
        self.redis = redis_client
        self.default_limits = default_limits or QuotaLimits()
        self.enable_global_limits = enable_global_limits
        
        # Local storage for quotas (fallback when Redis unavailable)
        self.local_usage: Dict[str, UserQuotaUsage] = {}
        self.user_limits: Dict[str, QuotaLimits] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Global system limits
        self.global_concurrent_tasks = 0
        self.global_max_concurrent = 20  # Максимум задач в системе
        
        # Setup logger с fallback
        if STRUCTLOG_AVAILABLE:
            self.logger = logger.bind(component="QuotaManager")
        else:
            self.logger = logger
        
        # Helper для совместимого логирования
        def log_info(message, **kwargs):
            if STRUCTLOG_AVAILABLE:
                self.logger.info(message, **kwargs)
            else:
                extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
                self.logger.info(f"{message} - {extra_info}")
        
        def log_warning(message, **kwargs):
            if STRUCTLOG_AVAILABLE:
                self.logger.warning(message, **kwargs)
            else:
                extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
                self.logger.warning(f"{message} - {extra_info}")
        
        self._log_info = log_info
        self._log_warning = log_warning
        
        self._log_info("QuotaManager initialized",
                      redis_enabled=self.redis is not None,
                      default_limits=self.default_limits.to_dict())
    
    def set_user_limits(self, user_id: str, limits: QuotaLimits):
        """Устанавливает индивидуальные лимиты для пользователя"""
        self.user_limits[user_id] = limits
        
        # Сохраняем в Redis если доступен
        if self.redis:
            try:
                key = f"user_limits:{user_id}"
                self.redis.setex(key, 86400, json.dumps(limits.to_dict()))  # TTL 24 часа
            except Exception as e:
                self._log_warning("Failed to store user limits in Redis", 
                                  user_id=user_id, error=str(e))
    
    def get_user_limits(self, user_id: str) -> QuotaLimits:
        """Получает лимиты для пользователя"""
        
        # Проверяем локальный кэш
        if user_id in self.user_limits:
            return self.user_limits[user_id]
        
        # Проверяем Redis
        if self.redis:
            try:
                key = f"user_limits:{user_id}"
                data = self.redis.get(key)
                if data:
                    limits_dict = json.loads(data)
                    limits = QuotaLimits.from_dict(limits_dict)
                    self.user_limits[user_id] = limits  # Кэшируем локально
                    return limits
            except Exception as e:
                self._log_warning("Failed to get user limits from Redis",
                                  user_id=user_id, error=str(e))
        
        # Возвращаем лимиты по умолчанию
        return self.default_limits
    
    def get_user_usage(self, user_id: str) -> UserQuotaUsage:
        """Получает текущее использование квот пользователем"""
        
        with self._lock:
            # Проверяем локальный кэш
            if user_id in self.local_usage:
                usage = self.local_usage[user_id]
                
                # Проверяем нужно ли сбросить окна времени
                current_time = time.time()
                
                # Сброс минутного окна
                if current_time - usage.minute_window_start >= 60:
                    usage.reset_minute_window()
                
                # Сброс часового окна
                if current_time - usage.hour_window_start >= 3600:
                    usage.reset_hour_window()
                
                # Сброс дневного окна
                if current_time - usage.day_window_start >= 86400:
                    usage.reset_day_window()
                
                return usage
            
            # Создаем новое использование
            usage = UserQuotaUsage(user_id=user_id)
            self.local_usage[user_id] = usage
            return usage
    
    def check_quota(self, user_id: str, file_size_mb: float = 0.0,
                   operation_type: str = 'file_processing') -> QuotaCheckResult:
        """Проверяет квоты перед выполнением операции"""
        
        limits = self.get_user_limits(user_id)
        usage = self.get_user_usage(user_id)
        
        current_time = time.time()
        
        # Проверка размера файла
        if file_size_mb > limits.max_file_size_mb:
            return QuotaCheckResult(
                allowed=False,
                user_id=user_id,
                violation_reason=f"File size {file_size_mb:.1f}MB exceeds limit {limits.max_file_size_mb}MB",
                current_usage=usage.to_dict(),
                limits=limits.to_dict()
            )
        
        # Проверка rate limiting (запросы в минуту)
        if usage.requests_this_minute >= limits.requests_per_minute:
            retry_after = int(60 - (current_time - usage.minute_window_start))
            return QuotaCheckResult(
                allowed=False,
                user_id=user_id,
                violation_reason=f"Rate limit exceeded: {usage.requests_this_minute}/{limits.requests_per_minute} requests per minute",
                current_usage=usage.to_dict(),
                limits=limits.to_dict(),
                retry_after_seconds=retry_after
            )
        
        # Проверка часовых лимитов
        if usage.files_processed_hour >= limits.max_files_per_hour:
            retry_after = int(3600 - (current_time - usage.hour_window_start))
            return QuotaCheckResult(
                allowed=False,
                user_id=user_id,
                violation_reason=f"Hourly limit exceeded: {usage.files_processed_hour}/{limits.max_files_per_hour} files",
                current_usage=usage.to_dict(),
                limits=limits.to_dict(),
                retry_after_seconds=retry_after
            )
        
        # Проверка дневных лимитов
        if usage.files_processed_day >= limits.max_files_per_day:
            retry_after = int(86400 - (current_time - usage.day_window_start))
            return QuotaCheckResult(
                allowed=False,
                user_id=user_id,
                violation_reason=f"Daily limit exceeded: {usage.files_processed_day}/{limits.max_files_per_day} files",
                current_usage=usage.to_dict(),
                limits=limits.to_dict(),
                retry_after_seconds=retry_after
            )
        
        # Проверка конкурентных задач пользователя
        if usage.active_tasks >= limits.max_concurrent_tasks:
            return QuotaCheckResult(
                allowed=False,
                user_id=user_id,
                violation_reason=f"Concurrent tasks limit exceeded: {usage.active_tasks}/{limits.max_concurrent_tasks} tasks",
                current_usage=usage.to_dict(),
                limits=limits.to_dict(),
                retry_after_seconds=30  # Проверить через 30 секунд
            )
        
        # Проверка размера очереди
        if usage.queue_size >= limits.max_queue_size:
            return QuotaCheckResult(
                allowed=False,
                user_id=user_id,
                violation_reason=f"Queue size limit exceeded: {usage.queue_size}/{limits.max_queue_size} files",
                current_usage=usage.to_dict(),
                limits=limits.to_dict(),
                retry_after_seconds=60
            )
        
        # Проверка глобальных лимитов системы
        if self.enable_global_limits and self.global_concurrent_tasks >= self.global_max_concurrent:
            return QuotaCheckResult(
                allowed=False,
                user_id=user_id,
                violation_reason=f"System overloaded: {self.global_concurrent_tasks}/{self.global_max_concurrent} global tasks",
                current_usage=usage.to_dict(),
                limits=limits.to_dict(),
                retry_after_seconds=60
            )
        
        # Все проверки пройдены
        return QuotaCheckResult(
            allowed=True,
            user_id=user_id,
            current_usage=usage.to_dict(),
            limits=limits.to_dict()
        )
    
    def reserve_quota(self, user_id: str, file_size_mb: float = 0.0) -> bool:
        """Резервирует квоту для выполнения операции"""
        
        with self._lock:
            usage = self.get_user_usage(user_id)
            
            # Увеличиваем счетчики
            usage.requests_this_minute += 1
            usage.active_tasks += 1
            usage.queue_size += 1
            usage.last_request_time = time.time()
            
            # Увеличиваем глобальный счетчик
            if self.enable_global_limits:
                self.global_concurrent_tasks += 1
            
            self._log_info("Quota reserved",
                           user_id=user_id,
                           file_size_mb=file_size_mb,
                           active_tasks=usage.active_tasks,
                           global_tasks=self.global_concurrent_tasks)
            
            return True
    
    def complete_task(self, user_id: str, success: bool = True) -> bool:
        """Завершает задачу и обновляет квоты"""
        
        with self._lock:
            usage = self.get_user_usage(user_id)
            
            # Уменьшаем счетчики
            if usage.active_tasks > 0:
                usage.active_tasks -= 1
            
            if usage.queue_size > 0:
                usage.queue_size -= 1
            
            # Увеличиваем счетчик обработанных файлов только при успехе
            if success:
                usage.files_processed_hour += 1
                usage.files_processed_day += 1
            
            # Уменьшаем глобальный счетчик
            if self.enable_global_limits and self.global_concurrent_tasks > 0:
                self.global_concurrent_tasks -= 1
            
            self._log_info("Task completed",
                           user_id=user_id,
                           success=success,
                           active_tasks=usage.active_tasks,
                           files_processed_hour=usage.files_processed_hour,
                           global_tasks=self.global_concurrent_tasks)
            
            return True
    
    def get_quota_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Получает статистику квот"""
        
        if user_id:
            # Статистика конкретного пользователя
            usage = self.get_user_usage(user_id)
            limits = self.get_user_limits(user_id)
            
            return {
                'user_id': user_id,
                'usage': usage.to_dict(),
                'limits': limits.to_dict(),
                'utilization': {
                    'hourly_percent': (usage.files_processed_hour / limits.max_files_per_hour) * 100,
                    'daily_percent': (usage.files_processed_day / limits.max_files_per_day) * 100,
                    'concurrent_percent': (usage.active_tasks / limits.max_concurrent_tasks) * 100,
                    'queue_percent': (usage.queue_size / limits.max_queue_size) * 100
                }
            }
        else:
            # Общая статистика системы
            total_users = len(self.local_usage)
            total_active_tasks = sum(usage.active_tasks for usage in self.local_usage.values())
            total_queue_size = sum(usage.queue_size for usage in self.local_usage.values())
            
            return {
                'system_stats': {
                    'total_users': total_users,
                    'total_active_tasks': total_active_tasks,
                    'total_queue_size': total_queue_size,
                    'global_concurrent_tasks': self.global_concurrent_tasks,
                    'global_max_concurrent': self.global_max_concurrent,
                    'system_utilization_percent': (self.global_concurrent_tasks / self.global_max_concurrent) * 100
                },
                'user_stats': [
                    {
                        'user_id': user_id,
                        'active_tasks': usage.active_tasks,
                        'files_processed_hour': usage.files_processed_hour,
                        'files_processed_day': usage.files_processed_day
                    }
                    for user_id, usage in self.local_usage.items()
                ]
            }
    
    def cleanup_expired_usage(self, max_age_hours: int = 24) -> int:
        """Очищает устаревшие записи использования"""
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        expired_users = []
        
        with self._lock:
            for user_id, usage in self.local_usage.items():
                # Проверяем активность пользователя
                if (usage.active_tasks == 0 and 
                    usage.queue_size == 0 and
                    current_time - usage.last_request_time > max_age_seconds):
                    expired_users.append(user_id)
            
            # Удаляем устаревшие записи
            for user_id in expired_users:
                del self.local_usage[user_id]
                if user_id in self.user_limits:
                    del self.user_limits[user_id]
        
        if expired_users:
            self._log_info("Cleaned up expired usage records",
                           count=len(expired_users),
                           user_ids=expired_users)
        
        return len(expired_users)

# Convenience функции для интеграции

def check_user_quota(user_id: str, file_size_mb: float = 0.0,
                    quota_manager: Optional[QuotaManager] = None) -> QuotaCheckResult:
    """Проверяет квоту пользователя"""
    
    if quota_manager is None:
        quota_manager = QuotaManager()
    
    return quota_manager.check_quota(user_id, file_size_mb)

def reserve_user_quota(user_id: str, file_size_mb: float = 0.0,
                      quota_manager: Optional[QuotaManager] = None) -> bool:
    """Резервирует квоту для пользователя"""
    
    if quota_manager is None:
        quota_manager = QuotaManager()
    
    return quota_manager.reserve_quota(user_id, file_size_mb)

def complete_user_task(user_id: str, success: bool = True,
                      quota_manager: Optional[QuotaManager] = None) -> bool:
    """Завершает задачу пользователя"""
    
    if quota_manager is None:
        quota_manager = QuotaManager()
    
    return quota_manager.complete_task(user_id, success) 