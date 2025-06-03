#!/usr/bin/env python3
"""
MON-S03: Adaptive Scaler для динамического управления квотами
Автоматически адаптирует лимиты на основе нагрузки и производительности
"""

import time
import psutil
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .quota_manager import QuotaManager, QuotaLimits

# Logging setup с fallback
try:
    import structlog
    logger = structlog.get_logger(__name__)
    STRUCTLOG_AVAILABLE = True
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    STRUCTLOG_AVAILABLE = False

# Helper функции для логирования
def safe_log_info(log_obj, message, **kwargs):
    if STRUCTLOG_AVAILABLE:
        log_obj.info(message, **kwargs)
    else:
        extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        log_obj.info(f"{message} - {extra_info}" if extra_info else message)

def safe_log_error(log_obj, message, **kwargs):
    if STRUCTLOG_AVAILABLE:
        log_obj.error(message, **kwargs)
    else:
        extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        log_obj.error(f"{message} - {extra_info}" if extra_info else message)

def safe_logger_bind(component):
    if STRUCTLOG_AVAILABLE:
        return logger.bind(component=component)
    else:
        return logger

@dataclass
class SystemMetrics:
    """Системные метрики для принятия решений о скейлинге"""
    cpu_percent: float = 0.0            # Использование CPU
    memory_percent: float = 0.0         # Использование памяти
    disk_io_percent: float = 0.0        # Нагрузка на диск
    
    # Load metrics
    load_average_1m: float = 0.0        # Load average за 1 минуту
    load_average_5m: float = 0.0        # Load average за 5 минут
    load_average_15m: float = 0.0       # Load average за 15 минут
    
    # Network metrics
    network_io_mbps: float = 0.0        # Сетевая нагрузка
    
    # Application metrics
    active_tasks: int = 0               # Активных задач
    queue_size: int = 0                 # Размер очереди
    avg_task_duration: float = 0.0      # Среднее время выполнения задач
    error_rate: float = 0.0             # Процент ошибок
    
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь"""
        return {
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_io_percent': self.disk_io_percent,
            'load_average_1m': self.load_average_1m,
            'load_average_5m': self.load_average_5m,
            'load_average_15m': self.load_average_15m,
            'network_io_mbps': self.network_io_mbps,
            'active_tasks': self.active_tasks,
            'queue_size': self.queue_size,
            'avg_task_duration': self.avg_task_duration,
            'error_rate': self.error_rate,
            'timestamp': self.timestamp
        }

@dataclass
class ScalingRules:
    """Правила скейлинга"""
    
    # CPU thresholds
    cpu_scale_up_threshold: float = 70.0    # Увеличить лимиты при CPU > 70%
    cpu_scale_down_threshold: float = 30.0  # Уменьшить лимиты при CPU < 30%
    
    # Memory thresholds
    memory_scale_up_threshold: float = 80.0  # Увеличить при memory > 80%
    memory_scale_down_threshold: float = 40.0 # Уменьшить при memory < 40%
    
    # Queue thresholds
    queue_scale_up_threshold: int = 50      # Увеличить при очереди > 50
    queue_scale_down_threshold: int = 5     # Уменьшить при очереди < 5
    
    # Error rate thresholds
    error_rate_scale_down_threshold: float = 15.0  # Уменьшить при ошибках > 15%
    
    # Scaling factors
    scale_up_factor: float = 1.5           # Множитель при увеличении
    scale_down_factor: float = 0.75        # Множитель при уменьшении
    
    # Minimum cooldown between scaling actions (seconds)
    scaling_cooldown: int = 300            # 5 минут
    
    # Maximum scaling bounds
    min_concurrent_tasks: int = 1          # Минимум задач
    max_concurrent_tasks: int = 50         # Максимум задач
    min_files_per_hour: int = 10           # Минимум файлов в час
    max_files_per_hour: int = 1000         # Максимум файлов в час

class SystemMonitor:
    """Мониторинг системных метрик"""
    
    def __init__(self, collection_interval: float = 30.0):
        """
        Args:
            collection_interval: Интервал сбора метрик в секундах
        """
        self.collection_interval = collection_interval
        self.metrics_history: List[SystemMetrics] = []
        self.max_history_size = 100  # Храним последние 100 измерений
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Setup logger с fallback
        if STRUCTLOG_AVAILABLE:
            self.logger = logger.bind(component="SystemMonitor")
        else:
            self.logger = logger
    
    def start(self):
        """Запускает мониторинг"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        if STRUCTLOG_AVAILABLE:
            self.logger.info("System monitoring started", interval=self.collection_interval)
        else:
            self.logger.info(f"System monitoring started - interval={self.collection_interval}")
    
    def stop(self):
        """Останавливает мониторинг"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
    
    def _monitor_loop(self):
        """Цикл сбора метрик"""
        while self._running:
            try:
                metrics = self._collect_metrics()
                
                with self._lock:
                    self.metrics_history.append(metrics)
                    
                    # Ограничиваем размер истории
                    if len(self.metrics_history) > self.max_history_size:
                        self.metrics_history.pop(0)
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                if STRUCTLOG_AVAILABLE:
                    self.logger.error("Error collecting metrics", error=str(e))
                else:
                    self.logger.error(f"Error collecting metrics - error={str(e)}")
                time.sleep(self.collection_interval)
    
    def _collect_metrics(self) -> SystemMetrics:
        """Собирает текущие метрики системы"""
        
        # CPU и память
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Load average (только для Unix)
        try:
            load_avg = psutil.getloadavg()
            load_1m, load_5m, load_15m = load_avg
        except (AttributeError, OSError):
            # Windows не поддерживает getloadavg
            load_1m = load_5m = load_15m = 0.0
        
        # Disk I/O
        try:
            disk_io = psutil.disk_io_counters()
            # Простая метрика на основе read+write bytes
            disk_io_percent = min(100, (disk_io.read_bytes + disk_io.write_bytes) / (1024**3) * 10)
        except (AttributeError, OSError):
            disk_io_percent = 0.0
        
        # Network I/O
        try:
            net_io = psutil.net_io_counters()
            # Конвертируем в Mbps (примерная оценка)
            network_io_mbps = (net_io.bytes_sent + net_io.bytes_recv) / (1024**2) / 60  # MB/min
        except (AttributeError, OSError):
            network_io_mbps = 0.0
        
        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_io_percent=disk_io_percent,
            load_average_1m=load_1m,
            load_average_5m=load_5m,
            load_average_15m=load_15m,
            network_io_mbps=network_io_mbps
        )
    
    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """Возвращает последние метрики"""
        with self._lock:
            return self.metrics_history[-1] if self.metrics_history else None
    
    def get_average_metrics(self, window_minutes: int = 5) -> Optional[SystemMetrics]:
        """Возвращает средние метрики за указанный период"""
        
        current_time = time.time()
        window_seconds = window_minutes * 60
        
        with self._lock:
            # Фильтруем метрики по времени
            recent_metrics = [
                m for m in self.metrics_history
                if current_time - m.timestamp <= window_seconds
            ]
            
            if not recent_metrics:
                return None
            
            # Вычисляем средние значения
            avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
            avg_disk = sum(m.disk_io_percent for m in recent_metrics) / len(recent_metrics)
            avg_load_1m = sum(m.load_average_1m for m in recent_metrics) / len(recent_metrics)
            avg_load_5m = sum(m.load_average_5m for m in recent_metrics) / len(recent_metrics)
            avg_load_15m = sum(m.load_average_15m for m in recent_metrics) / len(recent_metrics)
            avg_network = sum(m.network_io_mbps for m in recent_metrics) / len(recent_metrics)
            
            return SystemMetrics(
                cpu_percent=avg_cpu,
                memory_percent=avg_memory,
                disk_io_percent=avg_disk,
                load_average_1m=avg_load_1m,
                load_average_5m=avg_load_5m,
                load_average_15m=avg_load_15m,
                network_io_mbps=avg_network
            )

class AdaptiveScaler:
    """Адаптивный скейлер квот на основе нагрузки системы"""
    
    def __init__(self, quota_manager: QuotaManager,
                 system_monitor: Optional[SystemMonitor] = None,
                 scaling_rules: Optional[ScalingRules] = None):
        """
        Args:
            quota_manager: Менеджер квот
            system_monitor: Монитор системы
            scaling_rules: Правила скейлинга
        """
        self.quota_manager = quota_manager
        self.system_monitor = system_monitor or SystemMonitor()
        self.scaling_rules = scaling_rules or ScalingRules()
        
        # История скейлинга
        self.scaling_history: List[Dict[str, Any]] = []
        self.last_scaling_time: float = 0.0
        
        # Текущие базовые лимиты
        self.base_limits = self.quota_manager.default_limits
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self.logger = logger.bind(component="AdaptiveScaler")
    
    def start(self):
        """Запускает адаптивный скейлинг"""
        if self._running:
            return
        
        # Запускаем системный мониторинг
        self.system_monitor.start()
        
        self._running = True
        self._thread = threading.Thread(target=self._scaling_loop, daemon=True)
        self._thread.start()
        
        self.logger.info("Adaptive scaling started")
    
    def stop(self):
        """Останавливает адаптивный скейлинг"""
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=5.0)
        
        self.system_monitor.stop()
        
        self.logger.info("Adaptive scaling stopped")
    
    def _scaling_loop(self):
        """Основной цикл скейлинга"""
        while self._running:
            try:
                self._evaluate_and_scale()
                time.sleep(60)  # Проверяем каждую минуту
                
            except Exception as e:
                self.logger.error("Error in scaling loop", error=str(e))
                time.sleep(60)
    
    def _evaluate_and_scale(self):
        """Оценивает состояние системы и принимает решение о скейлинге"""
        
        # Проверяем cooldown
        current_time = time.time()
        if current_time - self.last_scaling_time < self.scaling_rules.scaling_cooldown:
            return
        
        # Получаем метрики
        system_metrics = self.system_monitor.get_average_metrics(window_minutes=3)
        if not system_metrics:
            return
        
        # Получаем метрики приложения от quota manager
        app_stats = self.quota_manager.get_quota_stats()
        system_stats = app_stats.get('system_stats', {})
        
        # Обновляем метрики приложения
        system_metrics.active_tasks = system_stats.get('total_active_tasks', 0)
        system_metrics.queue_size = system_stats.get('total_queue_size', 0)
        
        # Принимаем решение о скейлинге
        scaling_decision = self._make_scaling_decision(system_metrics)
        
        if scaling_decision['action'] != 'none':
            self._apply_scaling(scaling_decision, system_metrics)
    
    def _make_scaling_decision(self, metrics: SystemMetrics) -> Dict[str, Any]:
        """Принимает решение о скейлинге на основе метрик"""
        
        rules = self.scaling_rules
        reasons = []
        
        # Анализируем метрики для принятия решения
        scale_up_score = 0
        scale_down_score = 0
        
        # CPU-based scaling
        if metrics.cpu_percent > rules.cpu_scale_up_threshold:
            scale_up_score += 2
            reasons.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
        elif metrics.cpu_percent < rules.cpu_scale_down_threshold:
            scale_down_score += 1
            reasons.append(f"Low CPU usage: {metrics.cpu_percent:.1f}%")
        
        # Memory-based scaling
        if metrics.memory_percent > rules.memory_scale_up_threshold:
            scale_up_score += 2
            reasons.append(f"High memory usage: {metrics.memory_percent:.1f}%")
        elif metrics.memory_percent < rules.memory_scale_down_threshold:
            scale_down_score += 1
            reasons.append(f"Low memory usage: {metrics.memory_percent:.1f}%")
        
        # Queue-based scaling
        if metrics.queue_size > rules.queue_scale_up_threshold:
            scale_up_score += 3  # Очередь - важный индикатор
            reasons.append(f"Large queue size: {metrics.queue_size}")
        elif metrics.queue_size < rules.queue_scale_down_threshold:
            scale_down_score += 1
            reasons.append(f"Small queue size: {metrics.queue_size}")
        
        # Error rate (только scale down)
        if metrics.error_rate > rules.error_rate_scale_down_threshold:
            scale_down_score += 3
            reasons.append(f"High error rate: {metrics.error_rate:.1f}%")
        
        # Load average
        cpu_count = psutil.cpu_count()
        if cpu_count and metrics.load_average_5m > cpu_count * 1.5:
            scale_up_score += 1
            reasons.append(f"High load average: {metrics.load_average_5m:.2f}")
        elif cpu_count and metrics.load_average_5m < cpu_count * 0.3:
            scale_down_score += 1
            reasons.append(f"Low load average: {metrics.load_average_5m:.2f}")
        
        # Принимаем решение
        if scale_up_score >= 3:
            action = 'scale_up'
            factor = rules.scale_up_factor
        elif scale_down_score >= 3 and scale_up_score == 0:
            action = 'scale_down'
            factor = rules.scale_down_factor
        else:
            action = 'none'
            factor = 1.0
        
        return {
            'action': action,
            'factor': factor,
            'reasons': reasons,
            'scale_up_score': scale_up_score,
            'scale_down_score': scale_down_score,
            'metrics': metrics.to_dict()
        }
    
    def _apply_scaling(self, decision: Dict[str, Any], metrics: SystemMetrics):
        """Применяет решение о скейлинге"""
        
        action = decision['action']
        factor = decision['factor']
        rules = self.scaling_rules
        
        # Вычисляем новые лимиты
        current_limits = self.quota_manager.default_limits
        
        new_max_concurrent = int(current_limits.max_concurrent_tasks * factor)
        new_max_files_hour = int(current_limits.max_files_per_hour * factor)
        
        # Применяем ограничения
        new_max_concurrent = max(rules.min_concurrent_tasks,
                               min(rules.max_concurrent_tasks, new_max_concurrent))
        new_max_files_hour = max(rules.min_files_per_hour,
                               min(rules.max_files_per_hour, new_max_files_hour))
        
        # Проверяем, изменились ли лимиты
        if (new_max_concurrent == current_limits.max_concurrent_tasks and
            new_max_files_hour == current_limits.max_files_per_hour):
            return  # Нет изменений
        
        # Создаем новые лимиты
        new_limits = QuotaLimits(
            max_files_per_hour=new_max_files_hour,
            max_files_per_day=current_limits.max_files_per_day,
            max_concurrent_tasks=new_max_concurrent,
            max_file_size_mb=current_limits.max_file_size_mb,
            max_queue_size=current_limits.max_queue_size,
            requests_per_minute=current_limits.requests_per_minute,
            max_memory_mb=current_limits.max_memory_mb,
            max_cpu_percent=current_limits.max_cpu_percent
        )
        
        # Применяем новые лимиты как default
        self.quota_manager.default_limits = new_limits
        
        # Также обновляем глобальный лимит
        if action == 'scale_up':
            self.quota_manager.global_max_concurrent = min(
                self.quota_manager.global_max_concurrent + 5, 100)
        elif action == 'scale_down':
            self.quota_manager.global_max_concurrent = max(
                self.quota_manager.global_max_concurrent - 2, 5)
        
        # Записываем в историю
        scaling_event = {
            'timestamp': time.time(),
            'action': action,
            'factor': factor,
            'reasons': decision['reasons'],
            'old_limits': current_limits.to_dict(),
            'new_limits': new_limits.to_dict(),
            'metrics': decision['metrics']
        }
        
        with self._lock:
            self.scaling_history.append(scaling_event)
            self.last_scaling_time = time.time()
            
            # Ограничиваем размер истории
            if len(self.scaling_history) > 50:
                self.scaling_history.pop(0)
        
        self.logger.info("Scaling applied",
                        action=action,
                        factor=factor,
                        old_concurrent=current_limits.max_concurrent_tasks,
                        new_concurrent=new_max_concurrent,
                        old_files_hour=current_limits.max_files_per_hour,
                        new_files_hour=new_max_files_hour,
                        reasons=decision['reasons'])
    
    def get_scaling_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Возвращает историю скейлинга"""
        with self._lock:
            return self.scaling_history[-limit:] if self.scaling_history else []
    
    def get_current_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус скейлера"""
        
        latest_metrics = self.system_monitor.get_latest_metrics()
        current_limits = self.quota_manager.default_limits
        quota_stats = self.quota_manager.get_quota_stats()
        
        return {
            'running': self._running,
            'current_limits': current_limits.to_dict(),
            'global_max_concurrent': self.quota_manager.global_max_concurrent,
            'latest_metrics': latest_metrics.to_dict() if latest_metrics else None,
            'quota_stats': quota_stats,
            'last_scaling': self.last_scaling_time,
            'scaling_cooldown_remaining': max(0, 
                self.scaling_rules.scaling_cooldown - (time.time() - self.last_scaling_time)),
            'recent_scaling_events': len(self.scaling_history)
        }

# Convenience functions

def create_adaptive_quota_system(redis_client=None, 
                                default_limits: Optional[QuotaLimits] = None,
                                scaling_rules: Optional[ScalingRules] = None) -> Tuple[QuotaManager, AdaptiveScaler]:
    """Создает полную систему адаптивных квот"""
    
    quota_manager = QuotaManager(
        redis_client=redis_client,
        default_limits=default_limits
    )
    
    system_monitor = SystemMonitor(collection_interval=30.0)
    
    adaptive_scaler = AdaptiveScaler(
        quota_manager=quota_manager,
        system_monitor=system_monitor,
        scaling_rules=scaling_rules
    )
    
    return quota_manager, adaptive_scaler 