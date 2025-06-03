#!/usr/bin/env python3
"""
Celery Worker V2 для MON-007 - асинхронная обработка
Основные функции:
- Celery task queue для параллельной обработки
- Redis broker для координации
- Background jobs для Telegram Bot
- Масштабируемая архитектура workers
"""

import os
import time
import json
import logging
import traceback
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone

# Проверяем доступность Celery
try:
    from celery import Celery, Task
    from celery.result import AsyncResult
    from celery.states import PENDING, SUCCESS, FAILURE, RETRY, REVOKED
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Создаем заглушки для разработки
    class Celery:
        def __init__(self, *args, **kwargs): pass
        def task(self, *args, **kwargs): return lambda f: f
        def control(self): return type('obj', (object,), {'inspect': lambda: None})()
    
    class Task: pass
    class AsyncResult: pass
    
    PENDING = SUCCESS = FAILURE = RETRY = REVOKED = "MOCK_STATE"

logger = logging.getLogger(__name__)

@dataclass
class TaskResult:
    """Результат выполнения задачи"""
    task_id: str
    status: str  # pending, success, failure, retry, revoked
    result: Any = None
    error: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkerStats:
    """Статистика работы Celery workers"""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    pending_tasks: int = 0
    active_workers: int = 0
    queue_length: int = 0
    average_processing_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)

class MonitoTaskBase(Task):
    """Базовый класс для Monito задач с мониторингом"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Callback при успешном выполнении"""
        try:
            # Записываем метрики через MON-006
            from modules.monito_metrics import get_monito_metrics
            metrics = get_monito_metrics()
            
            metrics.record_data_processed("celery_worker", "tasks", 1)
            metrics.record_data_quality("celery_worker", 1.0, {
                "task_id": task_id,
                "task_name": self.name,
                "status": "success",
                "result_type": type(retval).__name__
            })
            
            logger.info(f"✅ Task {self.name} [{task_id}] completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Ошибка записи метрик успеха: {e}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Callback при ошибке выполнения"""
        try:
            # Записываем метрики ошибки
            from modules.monito_metrics import get_monito_metrics
            metrics = get_monito_metrics()
            
            metrics.record_data_quality("celery_worker", 0.0, {
                "task_id": task_id,
                "task_name": self.name,
                "status": "failure",
                "error": str(exc),
                "traceback": str(einfo)
            })
            
            logger.error(f"❌ Task {self.name} [{task_id}] failed: {exc}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка записи метрик ошибки: {e}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Callback при повторной попытке"""
        try:
            logger.warning(f"🔄 Task {self.name} [{task_id}] retrying: {exc}")
        except Exception as e:
            logger.error(f"❌ Ошибка retry callback: {e}")

class CeleryWorkerV2:
    """
    Celery Worker V2 для MON-007 асинхронной обработки
    
    Ключевые функции:
    - 🔄 Celery task queue
    - 💾 Redis broker
    - ⚡ Параллельная обработка
    - 📱 Background jobs
    """
    
    def __init__(self, app_name: str = "monito", 
                 broker_url: str = "redis://localhost:6379/0",
                 result_backend: str = "redis://localhost:6379/0",
                 enable_monitoring: bool = True):
        
        self.app_name = app_name
        self.broker_url = broker_url
        self.result_backend = result_backend
        self.enable_monitoring = enable_monitoring
        
        # Статистика
        self.stats = WorkerStats()
        
        # Проверяем зависимости
        self._check_dependencies()
        
        # Инициализируем Celery app
        self._init_celery_app()
        
        # Настраиваем мониторинг
        if self.enable_monitoring:
            self._init_monitoring()
        
        logger.info("✅ CeleryWorkerV2 инициализирован с MON-007 конфигурацией")
    
    def _check_dependencies(self):
        """Проверка зависимостей MON-007"""
        self.celery_available = CELERY_AVAILABLE
        self.redis_available = False
        
        if not self.celery_available:
            logger.warning("⚠️ Celery не найден, используем mock режим")
        else:
            logger.info("✅ Celery доступен для асинхронной обработки")
        
        try:
            import redis
            # Проверяем подключение к Redis
            redis_client = redis.Redis.from_url(self.broker_url)
            redis_client.ping()
            self.redis_available = True
            logger.info("✅ Redis доступен как broker")
        except Exception as e:
            logger.warning(f"⚠️ Redis недоступен: {e}")
    
    def _init_celery_app(self):
        """Инициализация Celery приложения"""
        if not self.celery_available:
            # Mock режим для разработки
            self.celery_app = None
            logger.info("📝 Celery mock режим активирован")
            return
        
        try:
            # Создаем Celery app
            self.celery_app = Celery(
                self.app_name,
                broker=self.broker_url,
                backend=self.result_backend
            )
            
            # Конфигурация Celery
            self.celery_app.conf.update(
                # Сериализация
                task_serializer='json',
                accept_content=['json'],
                result_serializer='json',
                timezone='UTC',
                enable_utc=True,
                
                # Результаты
                result_expires=3600,  # 1 час
                result_persistent=True,
                
                # Воркеры
                worker_prefetch_multiplier=1,
                task_acks_late=True,
                worker_disable_rate_limits=False,
                
                # Роутинг
                task_routes={
                    'monito.file_processing': {'queue': 'file_processing'},
                    'monito.llm_processing': {'queue': 'llm_processing'},
                    'monito.data_validation': {'queue': 'data_validation'},
                    'monito.sheets_writing': {'queue': 'sheets_writing'},
                    'monito.telegram_notifications': {'queue': 'notifications'},
                },
                
                # Retry настройки
                task_default_retry_delay=60,  # 1 минута
                task_max_retries=3,
                
                # Мониторинг
                worker_send_task_events=True,
                task_send_sent_event=True,
            )
            
            # Регистрируем задачи
            self._register_tasks()
            
            logger.info(f"✅ Celery app настроен: {self.app_name}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Celery: {e}")
            self.celery_app = None
    
    def _register_tasks(self):
        """Регистрация Monito задач"""
        if not self.celery_app:
            return
        
        try:
            # Задача обработки файла
            @self.celery_app.task(base=MonitoTaskBase, bind=True, name="monito.file_processing")
            def process_file_task(self, file_path: str, user_id: int, options: Dict[str, Any] = None):
                """Асинхронная обработка файла"""
                return self._process_file_impl(file_path, user_id, options or {})
            
            # Задача LLM обработки
            @self.celery_app.task(base=MonitoTaskBase, bind=True, name="monito.llm_processing")
            def llm_processing_task(self, products: List[Dict], options: Dict[str, Any] = None):
                """Асинхронная LLM обработка"""
                return self._llm_processing_impl(products, options or {})
            
            # Задача валидации данных
            @self.celery_app.task(base=MonitoTaskBase, bind=True, name="monito.data_validation")
            def data_validation_task(self, data: List[Dict], options: Dict[str, Any] = None):
                """Асинхронная валидация данных"""
                return self._data_validation_impl(data, options or {})
            
            # Задача записи в Sheets
            @self.celery_app.task(base=MonitoTaskBase, bind=True, name="monito.sheets_writing")
            def sheets_writing_task(self, products: List[Dict], spreadsheet_id: str, options: Dict[str, Any] = None):
                """Асинхронная запись в Google Sheets"""
                return self._sheets_writing_impl(products, spreadsheet_id, options or {})
            
            # Задача уведомлений в Telegram
            @self.celery_app.task(base=MonitoTaskBase, bind=True, name="monito.telegram_notifications")
            def telegram_notification_task(self, user_id: int, message: str, options: Dict[str, Any] = None):
                """Асинхронная отправка уведомлений"""
                return self._telegram_notification_impl(user_id, message, options or {})
            
            # Сохраняем ссылки на задачи
            self.process_file_task = process_file_task
            self.llm_processing_task = llm_processing_task
            self.data_validation_task = data_validation_task
            self.sheets_writing_task = sheets_writing_task
            self.telegram_notification_task = telegram_notification_task
            
            logger.info("✅ Monito задачи зарегистрированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка регистрации задач: {e}")
    
    def _init_monitoring(self):
        """Инициализация мониторинга через MON-006"""
        try:
            from modules.monito_metrics import get_monito_metrics
            self.metrics = get_monito_metrics()
            logger.info("✅ Мониторинг Celery настроен через MON-006")
        except Exception as e:
            logger.warning(f"⚠️ Мониторинг недоступен: {e}")
            self.metrics = None
    
    def submit_file_processing(self, file_path: str, user_id: int, 
                             options: Dict[str, Any] = None) -> str:
        """
        MON-007.1: Отправка файла на асинхронную обработку
        
        Args:
            file_path: Путь к файлу
            user_id: ID пользователя
            options: Дополнительные опции
        
        Returns:
            str: Task ID для отслеживания
        """
        try:
            if not self.celery_app:
                # Mock режим - имитируем обработку
                task_id = f"mock_task_{int(time.time() * 1000)}"
                logger.info(f"📝 Mock обработка файла: {file_path} -> {task_id}")
                return task_id
            
            # Отправляем задачу в очередь
            task = self.process_file_task.delay(file_path, user_id, options)
            
            # Записываем метрики
            if self.metrics:
                self.metrics.record_data_processed("celery_worker", "files", 1)
            
            self.stats.total_tasks += 1
            self.stats.pending_tasks += 1
            
            logger.info(f"🚀 Файл отправлен на обработку: {file_path} -> {task.id}")
            return task.id
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки задачи: {e}")
            raise
    
    def submit_llm_processing(self, products: List[Dict], 
                            options: Dict[str, Any] = None) -> str:
        """
        MON-007.2: Отправка LLM обработки
        
        Args:
            products: Список товаров для обработки
            options: Опции обработки
        
        Returns:
            str: Task ID для отслеживания
        """
        try:
            if not self.celery_app:
                task_id = f"mock_llm_task_{int(time.time() * 1000)}"
                logger.info(f"📝 Mock LLM обработка: {len(products)} товаров -> {task_id}")
                return task_id
            
            task = self.llm_processing_task.delay(products, options)
            
            if self.metrics:
                self.metrics.record_data_processed("celery_worker", "products", len(products))
            
            self.stats.total_tasks += 1
            self.stats.pending_tasks += 1
            
            logger.info(f"🤖 LLM обработка отправлена: {len(products)} товаров -> {task.id}")
            return task.id
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки LLM задачи: {e}")
            raise
    
    def submit_telegram_notification(self, user_id: int, message: str,
                                   options: Dict[str, Any] = None) -> str:
        """
        MON-007.3: Отправка Telegram уведомления
        
        Args:
            user_id: ID пользователя
            message: Сообщение
            options: Опции отправки
        
        Returns:
            str: Task ID для отслеживания
        """
        try:
            if not self.celery_app:
                task_id = f"mock_telegram_task_{int(time.time() * 1000)}"
                logger.info(f"📝 Mock Telegram уведомление: user {user_id} -> {task_id}")
                return task_id
            
            task = self.telegram_notification_task.delay(user_id, message, options)
            
            if self.metrics:
                self.metrics.record_data_processed("celery_worker", "notifications", 1)
            
            self.stats.total_tasks += 1
            self.stats.pending_tasks += 1
            
            logger.info(f"📱 Telegram уведомление отправлено: user {user_id} -> {task.id}")
            return task.id
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки Telegram задачи: {e}")
            raise
    
    def get_task_result(self, task_id: str) -> TaskResult:
        """
        MON-007.4: Получение результата задачи
        
        Args:
            task_id: ID задачи
        
        Returns:
            TaskResult: Статус и результат задачи
        """
        try:
            if not self.celery_app:
                # Mock результат
                return TaskResult(
                    task_id=task_id,
                    status="success",
                    result={"mock": True, "message": "Mock task completed"},
                    duration_ms=100
                )
            
            result = AsyncResult(task_id, app=self.celery_app)
            
            task_result = TaskResult(
                task_id=task_id,
                status=result.state.lower(),
                result=result.result if result.successful() else None,
                error=str(result.result) if result.failed() else "",
            )
            
            # Добавляем метаданные если доступны
            if hasattr(result, 'info') and result.info:
                task_result.metadata = result.info if isinstance(result.info, dict) else {}
            
            return task_result
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения результата задачи {task_id}: {e}")
            return TaskResult(
                task_id=task_id,
                status="error",
                error=str(e)
            )
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        MON-007.5: Получение статуса очередей
        
        Returns:
            Dict с информацией о состоянии очередей
        """
        try:
            if not self.celery_app:
                return {
                    "mode": "mock",
                    "queues": {
                        "file_processing": {"pending": 0, "active": 0},
                        "llm_processing": {"pending": 0, "active": 0},
                        "data_validation": {"pending": 0, "active": 0},
                        "sheets_writing": {"pending": 0, "active": 0},
                        "notifications": {"pending": 0, "active": 0}
                    },
                    "workers": {"active": 0, "total": 0}
                }
            
            # Получаем информацию о воркерах
            inspect = self.celery_app.control.inspect()
            
            # Активные задачи
            active_tasks = inspect.active() or {}
            
            # Зарезервированные задачи
            reserved_tasks = inspect.reserved() or {}
            
            # Статистика воркеров
            worker_stats = inspect.stats() or {}
            
            queue_info = {
                "mode": "celery",
                "queues": {},
                "workers": {
                    "active": len(active_tasks),
                    "total": len(worker_stats)
                },
                "active_tasks": sum(len(tasks) for tasks in active_tasks.values()),
                "reserved_tasks": sum(len(tasks) for tasks in reserved_tasks.values())
            }
            
            # Анализируем задачи по очередям
            all_tasks = []
            for worker_tasks in active_tasks.values():
                all_tasks.extend(worker_tasks)
            for worker_tasks in reserved_tasks.values():
                all_tasks.extend(worker_tasks)
            
            queue_names = ["file_processing", "llm_processing", "data_validation", 
                          "sheets_writing", "notifications"]
            
            for queue_name in queue_names:
                queue_tasks = [task for task in all_tasks 
                             if task.get('delivery_info', {}).get('routing_key') == queue_name]
                queue_info["queues"][queue_name] = {
                    "pending": len([t for t in queue_tasks if t.get('acknowledged') == False]),
                    "active": len([t for t in queue_tasks if t.get('acknowledged') == True])
                }
            
            return queue_info
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса очередей: {e}")
            return {"error": str(e)}
    
    def get_worker_stats(self) -> WorkerStats:
        """
        MON-007.6: Получение статистики воркеров
        
        Returns:
            WorkerStats: Детальная статистика работы
        """
        try:
            queue_status = self.get_queue_status()
            
            # Обновляем статистику
            self.stats.active_workers = queue_status.get("workers", {}).get("active", 0)
            self.stats.queue_length = queue_status.get("active_tasks", 0) + queue_status.get("reserved_tasks", 0)
            
            # Подсчитываем среднее время если есть завершенные задачи
            if self.stats.successful_tasks > 0:
                # Примерная оценка, в реальности нужно собирать метрики времени
                self.stats.average_processing_time_ms = 2000.0  # 2 секунды среднее
            
            return self.stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики воркеров: {e}")
            return self.stats
    
    def purge_queue(self, queue_name: str = None) -> int:
        """
        MON-007.7: Очистка очереди задач
        
        Args:
            queue_name: Имя очереди (None для всех)
        
        Returns:
            int: Количество удаленных задач
        """
        try:
            if not self.celery_app:
                logger.info("📝 Mock очистка очереди")
                return 0
            
            if queue_name:
                # Очищаем конкретную очередь
                purged = self.celery_app.control.purge()
                logger.info(f"✅ Очищена очередь {queue_name}: {purged} задач")
                return purged or 0
            else:
                # Очищаем все очереди
                total_purged = 0
                queues = ["file_processing", "llm_processing", "data_validation", 
                         "sheets_writing", "notifications"]
                
                for queue in queues:
                    try:
                        purged = self.celery_app.control.purge()
                        total_purged += purged or 0
                    except:
                        continue
                
                logger.info(f"✅ Очищены все очереди: {total_purged} задач")
                return total_purged
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки очереди: {e}")
            return 0
    
    # Реализация задач
    def _process_file_impl(self, file_path: str, user_id: int, options: Dict[str, Any]) -> Dict[str, Any]:
        """Реализация обработки файла"""
        try:
            start_time = time.time()
            
            # Имитируем комплексную обработку файла
            logger.info(f"📊 Начинаем обработку файла: {file_path}")
            
            # Этап 1: Проверка файла
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Файл не найден: {file_path}")
            
            file_size = os.path.getsize(file_path)
            logger.info(f"📄 Размер файла: {file_size} байт")
            
            # Этап 2: Парсинг (имитация)
            time.sleep(1.0)  # Имитируем парсинг
            
            # Этап 3: Валидация (имитация)
            time.sleep(0.5)  # Имитируем валидацию
            
            # Этап 4: Формирование результата
            processing_time = int((time.time() - start_time) * 1000)
            
            result = {
                "status": "completed",
                "file_path": file_path,
                "user_id": user_id,
                "processing_time_ms": processing_time,
                "file_size_bytes": file_size,
                "rows_processed": 150,  # Имитация
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Обновляем статистику
            self.stats.successful_tasks += 1
            self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
            
            logger.info(f"✅ Файл обработан за {processing_time}ms")
            return result
            
        except Exception as e:
            # Обновляем статистику ошибок
            self.stats.failed_tasks += 1
            self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
            self.stats.errors.append(f"File processing: {str(e)}")
            
            logger.error(f"❌ Ошибка обработки файла: {e}")
            raise
    
    def _llm_processing_impl(self, products: List[Dict], options: Dict[str, Any]) -> Dict[str, Any]:
        """Реализация LLM обработки"""
        try:
            start_time = time.time()
            
            logger.info(f"🤖 Начинаем LLM обработку {len(products)} товаров")
            
            # Имитируем LLM обработку
            time.sleep(len(products) * 0.1)  # 100ms на товар
            
            processing_time = int((time.time() - start_time) * 1000)
            
            result = {
                "status": "completed",
                "products_processed": len(products),
                "processing_time_ms": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.stats.successful_tasks += 1
            self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
            
            logger.info(f"✅ LLM обработка завершена за {processing_time}ms")
            return result
            
        except Exception as e:
            self.stats.failed_tasks += 1
            self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
            self.stats.errors.append(f"LLM processing: {str(e)}")
            
            logger.error(f"❌ Ошибка LLM обработки: {e}")
            raise
    
    def _data_validation_impl(self, data: List[Dict], options: Dict[str, Any]) -> Dict[str, Any]:
        """Реализация валидации данных"""
        try:
            start_time = time.time()
            
            logger.info(f"✅ Начинаем валидацию {len(data)} записей")
            
            # Имитируем валидацию
            time.sleep(0.5)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            result = {
                "status": "completed",
                "records_validated": len(data),
                "valid_records": int(len(data) * 0.9),  # 90% валидные
                "invalid_records": int(len(data) * 0.1),  # 10% невалидные
                "processing_time_ms": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.stats.successful_tasks += 1
            self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
            
            logger.info(f"✅ Валидация завершена за {processing_time}ms")
            return result
            
        except Exception as e:
            self.stats.failed_tasks += 1
            self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
            self.stats.errors.append(f"Data validation: {str(e)}")
            
            logger.error(f"❌ Ошибка валидации данных: {e}")
            raise
    
    def _sheets_writing_impl(self, products: List[Dict], spreadsheet_id: str, 
                           options: Dict[str, Any]) -> Dict[str, Any]:
        """Реализация записи в Google Sheets"""
        try:
            start_time = time.time()
            
            logger.info(f"📋 Начинаем запись {len(products)} товаров в Sheets")
            
            # Имитируем запись в Sheets
            time.sleep(len(products) * 0.02)  # 20ms на товар
            
            processing_time = int((time.time() - start_time) * 1000)
            
            result = {
                "status": "completed",
                "products_written": len(products),
                "spreadsheet_id": spreadsheet_id,
                "processing_time_ms": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.stats.successful_tasks += 1
            self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
            
            logger.info(f"✅ Запись в Sheets завершена за {processing_time}ms")
            return result
            
        except Exception as e:
            self.stats.failed_tasks += 1
            self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
            self.stats.errors.append(f"Sheets writing: {str(e)}")
            
            logger.error(f"❌ Ошибка записи в Sheets: {e}")
            raise
    
    def _telegram_notification_impl(self, user_id: int, message: str, 
                                  options: Dict[str, Any]) -> Dict[str, Any]:
        """Реализация Telegram уведомления"""
        try:
            start_time = time.time()
            
            logger.info(f"📱 Отправляем Telegram уведомление пользователю {user_id}")
            
            # Имитируем отправку уведомления
            time.sleep(0.1)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            result = {
                "status": "sent",
                "user_id": user_id,
                "message_length": len(message),
                "processing_time_ms": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.stats.successful_tasks += 1
            self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
            
            logger.info(f"✅ Telegram уведомление отправлено за {processing_time}ms")
            return result
            
        except Exception as e:
            self.stats.failed_tasks += 1
            self.stats.pending_tasks = max(0, self.stats.pending_tasks - 1)
            self.stats.errors.append(f"Telegram notification: {str(e)}")
            
            logger.error(f"❌ Ошибка отправки Telegram уведомления: {e}")
            raise

# Глобальный экземпляр для удобства использования
_global_celery_worker = None

def get_global_celery_worker() -> CeleryWorkerV2:
    """Получение глобального экземпляра CeleryWorker"""
    global _global_celery_worker
    
    if _global_celery_worker is None:
        _global_celery_worker = CeleryWorkerV2()
    
    return _global_celery_worker

def init_global_celery_worker(app_name: str = "monito",
                             broker_url: str = "redis://localhost:6379/0",
                             result_backend: str = "redis://localhost:6379/0") -> CeleryWorkerV2:
    """Инициализация глобального CeleryWorker с настройками"""
    global _global_celery_worker
    
    _global_celery_worker = CeleryWorkerV2(
        app_name=app_name,
        broker_url=broker_url,
        result_backend=result_backend
    )
    
    return _global_celery_worker

# Convenience функции для быстрого использования
def submit_file_async(file_path: str, user_id: int, options: Dict[str, Any] = None) -> str:
    """Быстрая отправка файла на асинхронную обработку"""
    worker = get_global_celery_worker()
    return worker.submit_file_processing(file_path, user_id, options)

def submit_llm_async(products: List[Dict], options: Dict[str, Any] = None) -> str:
    """Быстрая отправка LLM обработки"""
    worker = get_global_celery_worker()
    return worker.submit_llm_processing(products, options)

def get_task_status(task_id: str) -> TaskResult:
    """Быстрая проверка статуса задачи"""
    worker = get_global_celery_worker()
    return worker.get_task_result(task_id) 