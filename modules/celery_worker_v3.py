#!/usr/bin/env python3
"""
MON-S02: Celery Worker V3 с поддержкой идемпотентности и дедупликации
"""

import os
import time
import uuid
import random
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from pathlib import Path
import structlog

# Celery imports
try:
    from celery import Celery, Task
    from celery.result import AsyncResult
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

# Redis imports  
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Project imports
from modules.task_deduplicator import TaskDeduplicator, deduplicate_task, register_new_task

logger = structlog.get_logger(__name__)

@dataclass
class IdempotentTaskResult:
    """Результат идемпотентной задачи"""
    task_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed', 'duplicate'
    processing_time: Optional[float] = None
    rows_extracted: Optional[int] = None
    rows_processed: Optional[int] = None
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    is_duplicate: bool = False
    original_task_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)

class CeleryWorkerV3:
    """Celery Worker V3 с поддержкой идемпотентности"""
    
    def __init__(self, mock_mode: bool = False, 
                 redis_url: str = "redis://localhost:6379/0",
                 deduplication_ttl: int = 3600):
        self.mock_mode = mock_mode
        self.logger = logger.bind(component="CeleryWorkerV3")
        
        # Инициализация дедупликации
        if REDIS_AVAILABLE and not mock_mode:
            try:
                redis_client = redis.from_url(redis_url, decode_responses=True)
                self.deduplicator = TaskDeduplicator(
                    redis_client=redis_client,
                    default_ttl=deduplication_ttl
                )
            except Exception as e:
                self.logger.warning("Failed to initialize Redis", error=str(e))
                self.deduplicator = None
        else:
            self.deduplicator = None
    
    def submit_file_async(self, file_path: Union[str, Path], 
                         user_id: Optional[str] = None) -> IdempotentTaskResult:
        """Подает файл на идемпотентную обработку"""
        
        file_path_str = str(file_path)
        
        # Проверяем дублирование
        if self.deduplicator:
            try:
                is_duplicate, existing_task_id, existing_result = deduplicate_task(
                    task_type='process_file',
                    file_path=file_path,
                    user_id=user_id,
                    deduplicator=self.deduplicator
                )
                
                if is_duplicate:
                    self.logger.info("Duplicate detected", 
                                   file_path=file_path_str,
                                   existing_task_id=existing_task_id)
                    
                    return IdempotentTaskResult(
                        task_id=existing_task_id,
                        status='duplicate' if not existing_result else 'completed',
                        is_duplicate=True,
                        original_task_id=existing_task_id,
                        result_data=existing_result
                    )
            except Exception as e:
                self.logger.warning("Deduplication check failed", error=str(e))
        
        # Создаем новую задачу
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # Регистрируем в системе дедупликации
        if self.deduplicator:
            try:
                register_new_task(
                    task_id=task_id,
                    task_type='process_file',
                    file_path=file_path,
                    user_id=user_id,
                    deduplicator=self.deduplicator
                )
            except Exception as e:
                self.logger.warning("Failed to register task", error=str(e))
        
        return IdempotentTaskResult(
            task_id=task_id,
            status='pending',
            is_duplicate=False
        )
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получает результат задачи"""
        
        if self.deduplicator:
            result = self.deduplicator.get_task_result(task_id)
            if result:
                return result
        
        return None
    
    def get_deduplication_stats(self) -> Dict[str, Any]:
        """Получает статистику дедупликации"""
        
        if not self.deduplicator:
            return {'deduplication_enabled': False}
        
        try:
            stats = self.deduplicator.get_task_stats()
            stats['deduplication_enabled'] = True
            return stats
        except Exception as e:
            return {'deduplication_enabled': True, 'error': str(e)} 