#!/usr/bin/env python3
"""
MON-S02: Task Deduplicator
Система дедупликации и идемпотентности задач для Celery
"""

import hashlib
import json
import time
import redis
from typing import Dict, Any, Optional, Union, Tuple, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class TaskFingerprint:
    """Отпечаток задачи для дедупликации"""
    task_type: str
    file_path: str
    file_size: int
    file_hash: str
    user_id: Optional[str] = None
    additional_params: Optional[Dict[str, Any]] = None
    
    def to_key(self) -> str:
        """Генерирует уникальный ключ для Redis"""
        data = {
            'task_type': self.task_type,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'user_id': self.user_id or 'anonymous',
            'params': self.additional_params or {}
        }
        
        # Создаем стабильный JSON string
        json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        
        # MD5 hash для компактности
        hash_obj = hashlib.md5(json_str.encode('utf-8'))
        return f"task_fingerprint:{hash_obj.hexdigest()}"

@dataclass 
class TaskState:
    """Состояние задачи в системе дедупликации"""
    task_id: str
    fingerprint: TaskFingerprint
    status: str  # 'pending', 'processing', 'completed', 'failed'
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь для Redis"""
        return {
            'task_id': self.task_id,
            'fingerprint': asdict(self.fingerprint),
            'status': self.status,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'result': self.result,
            'error': self.error,
            'retry_count': self.retry_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskState':
        """Создает экземпляр из словаря Redis"""
        fingerprint_data = data['fingerprint']
        fingerprint = TaskFingerprint(**fingerprint_data)
        
        return cls(
            task_id=data['task_id'],
            fingerprint=fingerprint,
            status=data['status'],
            created_at=data['created_at'],
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            result=data.get('result'),
            error=data.get('error'),
            retry_count=data.get('retry_count', 0)
        )

class TaskDeduplicator:
    """Основной класс для дедупликации задач"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None, 
                 default_ttl: int = 3600, max_retry_count: int = 3):
        """
        Args:
            redis_client: Redis клиент (по умолчанию localhost)
            default_ttl: TTL для записей в Redis (в секундах)
            max_retry_count: Максимальное количество повторных попыток
        """
        self.redis = redis_client or redis.Redis(
            host='localhost', port=6379, db=0, decode_responses=True
        )
        self.default_ttl = default_ttl
        self.max_retry_count = max_retry_count
        self.logger = logger.bind(component="TaskDeduplicator")
        
    def compute_file_fingerprint(self, file_path: Union[str, Path], 
                                task_type: str = 'process_file',
                                user_id: Optional[str] = None,
                                additional_params: Optional[Dict[str, Any]] = None) -> TaskFingerprint:
        """Вычисляет отпечаток файла для задачи"""
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        # Получаем статистику файла
        stat = file_path.stat()
        file_size = stat.st_size
        
        # Вычисляем hash файла (первые и последние 8KB + размер для больших файлов)
        file_hash = self._compute_file_hash(file_path)
        
        fingerprint = TaskFingerprint(
            task_type=task_type,
            file_path=str(file_path.absolute()),
            file_size=file_size,
            file_hash=file_hash,
            user_id=user_id,
            additional_params=additional_params
        )
        
        self.logger.info("Computed file fingerprint", 
                        fingerprint_key=fingerprint.to_key(),
                        file_size=file_size,
                        task_type=task_type)
        
        return fingerprint
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Быстрое вычисление hash файла для больших файлов"""
        
        hash_md5 = hashlib.md5()
        file_size = file_path.stat().st_size
        
        with open(file_path, 'rb') as f:
            # Для небольших файлов читаем целиком
            if file_size <= 1024 * 1024:  # 1MB
                hash_md5.update(f.read())
            else:
                # Для больших файлов читаем начало, конец и размер
                chunk_size = 8192
                
                # Начало файла
                hash_md5.update(f.read(chunk_size))
                
                # Середина файла
                f.seek(file_size // 2)
                hash_md5.update(f.read(chunk_size))
                
                # Конец файла
                if file_size > chunk_size * 2:
                    f.seek(-chunk_size, 2)
                    hash_md5.update(f.read(chunk_size))
                
                # Добавляем размер файла для уникальности
                hash_md5.update(str(file_size).encode())
        
        return hash_md5.hexdigest()
    
    def check_duplicate_task(self, fingerprint: TaskFingerprint) -> Optional[TaskState]:
        """Проверяет наличие дублирующейся задачи"""
        
        key = fingerprint.to_key()
        
        try:
            task_data = self.redis.get(key)
            if not task_data:
                return None
            
            task_state = TaskState.from_dict(json.loads(task_data))
            
            # Проверяем не устарела ли задача
            current_time = time.time()
            age = current_time - task_state.created_at
            
            if age > self.default_ttl:
                # Задача устарела, удаляем
                self.redis.delete(key)
                self.logger.info("Removed expired task", 
                               task_id=task_state.task_id, age=age)
                return None
            
            self.logger.info("Found duplicate task",
                           task_id=task_state.task_id,
                           status=task_state.status,
                           age=age)
            
            return task_state
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.warning("Invalid task data in Redis", 
                              key=key, error=str(e))
            # Удаляем поврежденные данные
            self.redis.delete(key)
            return None
    
    def register_task(self, task_id: str, fingerprint: TaskFingerprint) -> TaskState:
        """Регистрирует новую задачу в системе дедупликации"""
        
        task_state = TaskState(
            task_id=task_id,
            fingerprint=fingerprint,
            status='pending',
            created_at=time.time()
        )
        
        key = fingerprint.to_key()
        
        # Сохраняем с TTL
        task_data = json.dumps(task_state.to_dict())
        self.redis.setex(key, self.default_ttl, task_data)
        
        # Также создаем обратный индекс по task_id
        reverse_key = f"task_id:{task_id}"
        self.redis.setex(reverse_key, self.default_ttl, key)
        
        self.logger.info("Registered new task",
                        task_id=task_id,
                        fingerprint_key=key)
        
        return task_state
    
    def update_task_status(self, task_id: str, status: str, 
                          result: Optional[Dict[str, Any]] = None,
                          error: Optional[str] = None) -> bool:
        """Обновляет статус задачи"""
        
        # Находим ключ по task_id
        reverse_key = f"task_id:{task_id}"
        fingerprint_key = self.redis.get(reverse_key)
        
        if not fingerprint_key:
            self.logger.warning("Task not found for status update", task_id=task_id)
            return False
        
        try:
            task_data = self.redis.get(fingerprint_key)
            if not task_data:
                return False
            
            task_state = TaskState.from_dict(json.loads(task_data))
            
            # Обновляем статус
            task_state.status = status
            current_time = time.time()
            
            if status == 'processing' and not task_state.started_at:
                task_state.started_at = current_time
            elif status in ['completed', 'failed']:
                task_state.completed_at = current_time
                if result:
                    task_state.result = result
                if error:
                    task_state.error = error
            
            # Сохраняем обновленное состояние
            updated_data = json.dumps(task_state.to_dict())
            self.redis.setex(fingerprint_key, self.default_ttl, updated_data)
            
            self.logger.info("Updated task status",
                           task_id=task_id,
                           status=status,
                           duration=current_time - task_state.created_at)
            
            return True
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error("Failed to update task status",
                            task_id=task_id, error=str(e))
            return False
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получает результат выполнения задачи"""
        
        reverse_key = f"task_id:{task_id}"
        fingerprint_key = self.redis.get(reverse_key)
        
        if not fingerprint_key:
            return None
        
        try:
            task_data = self.redis.get(fingerprint_key)
            if not task_data:
                return None
            
            task_state = TaskState.from_dict(json.loads(task_data))
            
            if task_state.status == 'completed' and task_state.result:
                return task_state.result
            elif task_state.status == 'failed' and task_state.error:
                return {'error': task_state.error, 'failed': True}
            
            return None
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.warning("Failed to get task result",
                              task_id=task_id, error=str(e))
            return None
    
    def should_retry_task(self, task_id: str) -> bool:
        """Определяет нужно ли повторить задачу"""
        
        reverse_key = f"task_id:{task_id}"
        fingerprint_key = self.redis.get(reverse_key)
        
        if not fingerprint_key:
            return True  # Если задача не найдена, можно попробовать
        
        try:
            task_data = self.redis.get(fingerprint_key)
            if not task_data:
                return True
            
            task_state = TaskState.from_dict(json.loads(task_data))
            
            # Не повторяем если задача уже завершена успешно
            if task_state.status == 'completed':
                return False
            
            # Не повторяем если превышен лимит попыток
            if task_state.retry_count >= self.max_retry_count:
                self.logger.warning("Max retry count exceeded",
                                  task_id=task_id,
                                  retry_count=task_state.retry_count)
                return False
            
            # Увеличиваем счетчик попыток
            task_state.retry_count += 1
            updated_data = json.dumps(task_state.to_dict())
            self.redis.setex(fingerprint_key, self.default_ttl, updated_data)
            
            return True
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.warning("Failed to check retry status",
                              task_id=task_id, error=str(e))
            return True
    
    def cleanup_expired_tasks(self) -> int:
        """Очищает устаревшие задачи из Redis"""
        
        current_time = time.time()
        cleaned_count = 0
        
        # Находим все ключи отпечатков
        pattern = "task_fingerprint:*"
        
        try:
            for key in self.redis.scan_iter(match=pattern, count=100):
                task_data = self.redis.get(key)
                if not task_data:
                    continue
                
                try:
                    task_state = TaskState.from_dict(json.loads(task_data))
                    age = current_time - task_state.created_at
                    
                    if age > self.default_ttl:
                        # Удаляем основной ключ
                        self.redis.delete(key)
                        # Удаляем обратный индекс
                        reverse_key = f"task_id:{task_state.task_id}"
                        self.redis.delete(reverse_key)
                        
                        cleaned_count += 1
                        
                except (json.JSONDecodeError, KeyError, TypeError):
                    # Удаляем поврежденные данные
                    self.redis.delete(key)
                    cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info("Cleaned expired tasks", count=cleaned_count)
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error("Failed to cleanup expired tasks", error=str(e))
            return 0
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Получает статистику задач в системе"""
        
        stats = {
            'total_tasks': 0,
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0,
            'average_age': 0,
            'oldest_task': None,
            'newest_task': None
        }
        
        current_time = time.time()
        ages = []
        oldest_time = float('inf')
        newest_time = 0
        
        try:
            pattern = "task_fingerprint:*"
            
            for key in self.redis.scan_iter(match=pattern, count=100):
                task_data = self.redis.get(key)
                if not task_data:
                    continue
                
                try:
                    task_state = TaskState.from_dict(json.loads(task_data))
                    stats['total_tasks'] += 1
                    stats[task_state.status] += 1
                    
                    age = current_time - task_state.created_at
                    ages.append(age)
                    
                    if task_state.created_at < oldest_time:
                        oldest_time = task_state.created_at
                        stats['oldest_task'] = task_state.task_id
                    
                    if task_state.created_at > newest_time:
                        newest_time = task_state.created_at
                        stats['newest_task'] = task_state.task_id
                    
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            
            if ages:
                stats['average_age'] = sum(ages) / len(ages)
            
            return stats
            
        except Exception as e:
            self.logger.error("Failed to get task stats", error=str(e))
            return stats

# Convenience функции для использования с Celery

def deduplicate_task(task_type: str, file_path: Union[str, Path],
                    user_id: Optional[str] = None,
                    additional_params: Optional[Dict[str, Any]] = None,
                    deduplicator: Optional[TaskDeduplicator] = None) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Проверяет дублирование задачи и возвращает результат
    
    Returns:
        Tuple[is_duplicate, existing_task_id, existing_result]
    """
    
    if deduplicator is None:
        deduplicator = TaskDeduplicator()
    
    try:
        fingerprint = deduplicator.compute_file_fingerprint(
            file_path, task_type, user_id, additional_params
        )
        
        existing_task = deduplicator.check_duplicate_task(fingerprint)
        
        if existing_task:
            # Проверяем статус существующей задачи
            if existing_task.status == 'completed':
                return True, existing_task.task_id, existing_task.result
            elif existing_task.status in ['pending', 'processing']:
                return True, existing_task.task_id, None
            elif existing_task.status == 'failed':
                # Для провалившихся задач проверяем нужно ли повторить
                if deduplicator.should_retry_task(existing_task.task_id):
                    return False, None, None
                else:
                    return True, existing_task.task_id, {'error': existing_task.error, 'failed': True}
        
        return False, None, None
        
    except Exception as e:
        logger.error("Failed to check task duplication", 
                    file_path=str(file_path), error=str(e))
        # В случае ошибки разрешаем выполнение задачи
        return False, None, None

def register_new_task(task_id: str, task_type: str, file_path: Union[str, Path],
                     user_id: Optional[str] = None,
                     additional_params: Optional[Dict[str, Any]] = None,
                     deduplicator: Optional[TaskDeduplicator] = None) -> bool:
    """Регистрирует новую задачу в системе дедупликации"""
    
    if deduplicator is None:
        deduplicator = TaskDeduplicator()
    
    try:
        fingerprint = deduplicator.compute_file_fingerprint(
            file_path, task_type, user_id, additional_params
        )
        
        deduplicator.register_task(task_id, fingerprint)
        return True
        
    except Exception as e:
        logger.error("Failed to register new task",
                    task_id=task_id, file_path=str(file_path), error=str(e))
        return False 