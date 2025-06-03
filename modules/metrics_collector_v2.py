#!/usr/bin/env python3
"""
Metrics Collector V2 для MON-006 - наблюдаемость и мониторинг
Основные функции:
- Prometheus метрики для мониторинга
- Structured logging с контекстом
- Performance tracing и измерения
- Real-time monitoring компонентов
"""

import os
import time
import json
import logging
import threading
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
from functools import wraps
import traceback
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@dataclass
class MetricsStats:
    """Статистика метрик для MON-006"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_processing_time_ms: int = 0
    average_processing_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    errors: List[str] = field(default_factory=list)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OperationTrace:
    """Трейс операции для детального мониторинга"""
    operation_id: str
    operation_name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: int = 0
    status: str = "running"  # running, success, failed
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    memory_delta_mb: float = 0.0

class MetricsCollectorV2:
    """
    Metrics Collector V2 для MON-006 мониторинга
    
    Ключевые функции:
    - 📊 Prometheus метрики
    - 📝 Structured logging 
    - 🔍 Performance tracing
    - 📈 Real-time monitoring
    """
    
    def __init__(self, enable_prometheus: bool = True, enable_tracing: bool = True,
                 metrics_port: int = 8000):
        # Статистика
        self.stats = MetricsStats()
        
        # Настройки
        self.enable_prometheus = enable_prometheus
        self.enable_tracing = enable_tracing
        self.metrics_port = metrics_port
        
        # Трейсинг
        self.active_traces: Dict[str, OperationTrace] = {}
        self.completed_traces: List[OperationTrace] = []
        self.trace_lock = threading.Lock()
        
        # Метрики счетчики
        self._operation_counter = 0
        self._memory_tracker = {}
        
        # Проверяем зависимости
        self._check_dependencies()
        
        # Инициализируем Prometheus метрики
        self._init_prometheus_metrics()
        
        # Настраиваем structured logging
        self._init_structured_logging()
        
        logger.info("✅ MetricsCollectorV2 инициализирован с MON-006 мониторингом")
    
    def _check_dependencies(self):
        """Проверка зависимостей MON-006"""
        self.prometheus_available = False
        self.structlog_available = False
        self.psutil_available = False
        
        try:
            import prometheus_client
            self.prometheus_available = True
            logger.info("✅ Prometheus доступен для метрик")
        except ImportError:
            logger.warning("⚠️ Prometheus не найден, метрики ограничены")
        
        try:
            import structlog
            self.structlog_available = True
            logger.info("✅ Structlog доступен для structured logging")
        except ImportError:
            logger.warning("⚠️ Structlog не найден, используем стандартный logging")
        
        try:
            import psutil
            self.psutil_available = True
            logger.info("✅ psutil доступен для мониторинга ресурсов")
        except ImportError:
            logger.warning("⚠️ psutil не найден, мониторинг ресурсов ограничен")
    
    def _init_prometheus_metrics(self):
        """Инициализация Prometheus метрик"""
        if not self.prometheus_available or not self.enable_prometheus:
            logger.info("📝 Prometheus недоступен, используем внутренние метрики")
            self.prometheus_metrics = None
            return
        
        try:
            from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
            
            # Основные метрики
            self.operation_counter = Counter(
                'monito_operations_total',
                'Total number of operations',
                ['operation_type', 'status', 'component']
            )
            
            self.operation_duration = Histogram(
                'monito_operation_duration_seconds',
                'Duration of operations in seconds',
                ['operation_type', 'component'],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
            )
            
            self.memory_usage = Gauge(
                'monito_memory_usage_mb',
                'Memory usage in MB',
                ['component']
            )
            
            self.data_processed = Counter(
                'monito_data_processed_total',
                'Total amount of data processed',
                ['data_type', 'component']
            )
            
            self.quality_score = Gauge(
                'monito_data_quality_score',
                'Data quality score (0.0-1.0)',
                ['component']
            )
            
            self.cache_operations = Counter(
                'monito_cache_operations_total',
                'Cache operations',
                ['operation', 'result', 'component']
            )
            
            # Системная информация
            self.system_info = Info(
                'monito_system_info',
                'System information'
            )
            
            # Запускаем HTTP сервер для метрик
            if self.metrics_port:
                start_http_server(self.metrics_port)
                logger.info(f"✅ Prometheus метрики доступны на порту {self.metrics_port}")
            
            self.prometheus_metrics = {
                'operation_counter': self.operation_counter,
                'operation_duration': self.operation_duration,
                'memory_usage': self.memory_usage,
                'data_processed': self.data_processed,
                'quality_score': self.quality_score,
                'cache_operations': self.cache_operations,
                'system_info': self.system_info
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Prometheus метрик: {e}")
            self.prometheus_metrics = None
    
    def _init_structured_logging(self):
        """Настройка structured logging"""
        if not self.structlog_available:
            logger.info("📝 Structlog недоступен, используем стандартный logging")
            self.structured_logger = None
            return
        
        try:
            import structlog
            
            # Настройка structured logging
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            
            self.structured_logger = structlog.get_logger("monito")
            logger.info("✅ Structured logging настроен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки structured logging: {e}")
            self.structured_logger = None
    
    def start_operation_trace(self, operation_name: str, component: str = "unknown", 
                            metadata: Dict[str, Any] = None) -> str:
        """
        MON-006.1: Начало трейсинга операции
        
        Args:
            operation_name: Название операции
            component: Компонент системы
            metadata: Дополнительные метаданные
        
        Returns:
            str: ID операции для завершения трейса
        """
        if not self.enable_tracing:
            return f"trace_{int(time.time() * 1000)}"
        
        try:
            with self.trace_lock:
                self._operation_counter += 1
                operation_id = f"op_{self._operation_counter}_{int(time.time() * 1000)}"
                
                # Измеряем память в начале
                initial_memory = self._get_memory_usage()
                
                trace = OperationTrace(
                    operation_id=operation_id,
                    operation_name=operation_name,
                    start_time=time.time(),
                    metadata=metadata or {},
                    memory_delta_mb=0.0
                )
                
                trace.metadata.update({
                    'component': component,
                    'initial_memory_mb': initial_memory,
                    'pid': os.getpid(),
                    'thread_id': threading.get_ident()
                })
                
                self.active_traces[operation_id] = trace
                
                # Логирование начала операции
                self._log_structured(
                    "operation_started",
                    operation_id=operation_id,
                    operation_name=operation_name,
                    component=component,
                    initial_memory_mb=initial_memory,
                    metadata=metadata
                )
                
                # Prometheus метрика
                if self.prometheus_metrics:
                    self.operation_counter.labels(
                        operation_type=operation_name,
                        status='started',
                        component=component
                    ).inc()
                
                logger.debug(f"🔍 Начат трейс операции: {operation_name} ({operation_id})")
                return operation_id
                
        except Exception as e:
            logger.error(f"❌ Ошибка начала трейсинга: {e}")
            return f"error_trace_{int(time.time() * 1000)}"
    
    def end_operation_trace(self, operation_id: str, status: str = "success", 
                          result_metadata: Dict[str, Any] = None, error: str = ""):
        """
        MON-006.2: Завершение трейсинга операции
        
        Args:
            operation_id: ID операции
            status: Статус завершения (success/failed)
            result_metadata: Метаданные результата
            error: Сообщение об ошибке
        """
        if not self.enable_tracing or operation_id not in self.active_traces:
            return
        
        try:
            with self.trace_lock:
                trace = self.active_traces[operation_id]
                trace.end_time = time.time()
                trace.duration_ms = int((trace.end_time - trace.start_time) * 1000)
                trace.status = status
                trace.error_message = error
                
                # Измеряем изменение памяти
                final_memory = self._get_memory_usage()
                initial_memory = trace.metadata.get('initial_memory_mb', 0)
                trace.memory_delta_mb = final_memory - initial_memory
                
                # Добавляем метаданные результата
                if result_metadata:
                    trace.metadata.update(result_metadata)
                
                # Обновляем статистику
                self.stats.total_operations += 1
                self.stats.total_processing_time_ms += trace.duration_ms
                
                if status == "success":
                    self.stats.successful_operations += 1
                else:
                    self.stats.failed_operations += 1
                    if error:
                        self.stats.errors.append(f"{trace.operation_name}: {error}")
                
                # Обновляем среднее время
                if self.stats.total_operations > 0:
                    self.stats.average_processing_time_ms = (
                        self.stats.total_processing_time_ms / self.stats.total_operations
                    )
                
                # Обновляем пиковую память
                if final_memory > self.stats.peak_memory_mb:
                    self.stats.peak_memory_mb = final_memory
                
                # Логирование завершения
                self._log_structured(
                    "operation_completed",
                    operation_id=operation_id,
                    operation_name=trace.operation_name,
                    component=trace.metadata.get('component', 'unknown'),
                    duration_ms=trace.duration_ms,
                    status=status,
                    memory_delta_mb=trace.memory_delta_mb,
                    final_memory_mb=final_memory,
                    error_message=error,
                    result_metadata=result_metadata
                )
                
                # Prometheus метрики
                if self.prometheus_metrics:
                    # Счетчик операций
                    self.operation_counter.labels(
                        operation_type=trace.operation_name,
                        status=status,
                        component=trace.metadata.get('component', 'unknown')
                    ).inc()
                    
                    # Длительность операции
                    self.operation_duration.labels(
                        operation_type=trace.operation_name,
                        component=trace.metadata.get('component', 'unknown')
                    ).observe(trace.duration_ms / 1000.0)
                    
                    # Использование памяти
                    self.memory_usage.labels(
                        component=trace.metadata.get('component', 'unknown')
                    ).set(final_memory)
                
                # Перемещаем в завершенные трейсы
                self.completed_traces.append(trace)
                del self.active_traces[operation_id]
                
                # Ограничиваем количество сохраненных трейсов
                if len(self.completed_traces) > 1000:
                    self.completed_traces = self.completed_traces[-500:]
                
                logger.debug(f"✅ Завершен трейс операции: {trace.operation_name} "
                           f"({trace.duration_ms}ms, {status})")
                
        except Exception as e:
            logger.error(f"❌ Ошибка завершения трейсинга: {e}")
    
    @contextmanager
    def trace_operation(self, operation_name: str, component: str = "unknown", 
                       metadata: Dict[str, Any] = None):
        """
        MON-006.3: Контекстный менеджер для трейсинга операций
        
        Usage:
            with metrics.trace_operation("excel_parsing", "pre_processor"):
                # код операции
                pass
        """
        operation_id = self.start_operation_trace(operation_name, component, metadata)
        
        try:
            yield operation_id
            self.end_operation_trace(operation_id, "success")
        except Exception as e:
            self.end_operation_trace(operation_id, "failed", error=str(e))
            raise
    
    def measure_performance(self, func: Callable = None, operation_name: str = None, 
                          component: str = "unknown"):
        """
        MON-006.4: Декоратор для измерения производительности функций
        
        Usage:
            @metrics.measure_performance(operation_name="parse_excel", component="pre_processor")
            def parse_excel_file(file_path):
                # код функции
                pass
        """
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                op_name = operation_name or f.__name__
                
                with self.trace_operation(op_name, component):
                    result = f(*args, **kwargs)
                    
                    # Добавляем метаданные результата если возможно
                    result_metadata = {}
                    if hasattr(result, '__len__'):
                        try:
                            result_metadata['result_size'] = len(result)
                        except:
                            pass
                    
                    return result
            
            return wrapper
        
        if func is None:
            return decorator
        else:
            return decorator(func)
    
    def record_data_quality(self, component: str, quality_score: float, 
                          data_info: Dict[str, Any] = None):
        """
        MON-006.5: Запись метрик качества данных
        
        Args:
            component: Компонент системы
            quality_score: Оценка качества (0.0-1.0)
            data_info: Дополнительная информация о данных
        """
        try:
            # Обновляем внутреннюю статистику
            if 'quality_scores' not in self.stats.custom_metrics:
                self.stats.custom_metrics['quality_scores'] = {}
            
            self.stats.custom_metrics['quality_scores'][component] = {
                'score': quality_score,
                'timestamp': time.time(),
                'data_info': data_info or {}
            }
            
            # Логирование
            self._log_structured(
                "data_quality_recorded",
                component=component,
                quality_score=quality_score,
                data_info=data_info
            )
            
            # Prometheus метрика
            if self.prometheus_metrics:
                self.quality_score.labels(component=component).set(quality_score)
            
            logger.debug(f"📊 Записана метрика качества: {component} = {quality_score:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка записи метрики качества: {e}")
    
    def record_cache_operation(self, component: str, operation: str, result: str,
                             details: Dict[str, Any] = None):
        """
        MON-006.6: Запись метрик кэширования
        
        Args:
            component: Компонент системы
            operation: Тип операции (get, set, delete, clear)
            result: Результат (hit, miss, success, failed)
            details: Дополнительные детали
        """
        try:
            # Логирование
            self._log_structured(
                "cache_operation",
                component=component,
                operation=operation,
                result=result,
                details=details
            )
            
            # Prometheus метрика
            if self.prometheus_metrics:
                self.cache_operations.labels(
                    operation=operation,
                    result=result,
                    component=component
                ).inc()
            
            logger.debug(f"💾 Записана операция кэша: {component}/{operation} = {result}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка записи метрики кэша: {e}")
    
    def record_data_processed(self, component: str, data_type: str, count: int,
                            size_bytes: int = 0):
        """
        MON-006.7: Запись метрик обработанных данных
        
        Args:
            component: Компонент системы
            data_type: Тип данных (rows, files, products, etc.)
            count: Количество обработанных элементов
            size_bytes: Размер данных в байтах
        """
        try:
            # Логирование
            self._log_structured(
                "data_processed",
                component=component,
                data_type=data_type,
                count=count,
                size_bytes=size_bytes
            )
            
            # Prometheus метрика
            if self.prometheus_metrics:
                self.data_processed.labels(
                    data_type=data_type,
                    component=component
                ).inc(count)
            
            logger.debug(f"📈 Записаны обработанные данные: {component}/{data_type} = {count}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка записи метрики данных: {e}")
    
    def _log_structured(self, event: str, **kwargs):
        """Structured logging с контекстом"""
        try:
            if self.structured_logger:
                self.structured_logger.info(event, **kwargs)
            else:
                # Fallback на обычный logging
                logger.info(f"[{event}] {json.dumps(kwargs, default=str)}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка structured logging: {e}")
    
    def _get_memory_usage(self) -> float:
        """Получение текущего использования памяти в MB"""
        try:
            if self.psutil_available:
                import psutil
                process = psutil.Process()
                return process.memory_info().rss / 1024 / 1024
            else:
                # Простая оценка через sys
                import sys
                return sys.getsizeof(self) / 1024 / 1024
                
        except Exception:
            return 0.0
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        MON-006.8: Получение сводки всех метрик
        
        Returns:
            Dict с полной статистикой мониторинга
        """
        try:
            # Активные трейсы
            active_operations = []
            with self.trace_lock:
                for trace in self.active_traces.values():
                    active_operations.append({
                        'operation_id': trace.operation_id,
                        'operation_name': trace.operation_name,
                        'component': trace.metadata.get('component', 'unknown'),
                        'duration_ms': int((time.time() - trace.start_time) * 1000),
                        'status': trace.status
                    })
            
            # Последние завершенные операции
            recent_operations = []
            for trace in self.completed_traces[-10:]:
                recent_operations.append({
                    'operation_name': trace.operation_name,
                    'component': trace.metadata.get('component', 'unknown'),
                    'duration_ms': trace.duration_ms,
                    'status': trace.status,
                    'memory_delta_mb': trace.memory_delta_mb
                })
            
            # Системная информация
            system_info = {
                'current_memory_mb': self._get_memory_usage(),
                'pid': os.getpid(),
                'active_threads': threading.active_count()
            }
            
            return {
                'mon_006_metrics': {
                    'prometheus_enabled': self.prometheus_available and self.enable_prometheus,
                    'tracing_enabled': self.enable_tracing,
                    'structured_logging_enabled': self.structured_logger is not None,
                    'metrics_port': self.metrics_port if self.prometheus_metrics else None
                },
                'performance_stats': {
                    'total_operations': self.stats.total_operations,
                    'successful_operations': self.stats.successful_operations,
                    'failed_operations': self.stats.failed_operations,
                    'success_rate': (
                        self.stats.successful_operations / max(self.stats.total_operations, 1)
                    ),
                    'average_processing_time_ms': self.stats.average_processing_time_ms,
                    'peak_memory_mb': self.stats.peak_memory_mb,
                    'errors_count': len(self.stats.errors)
                },
                'active_operations': active_operations,
                'recent_operations': recent_operations,
                'system_info': system_info,
                'custom_metrics': self.stats.custom_metrics,
                'version': 'MetricsCollectorV2_MON006'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения метрик: {e}")
            return {'error': str(e), 'version': 'MetricsCollectorV2_MON006'}
    
    def export_traces_to_file(self, file_path: str, format: str = "json") -> bool:
        """
        MON-006.9: Экспорт трейсов в файл для анализа
        
        Args:
            file_path: Путь к файлу
            format: Формат экспорта (json, csv)
        
        Returns:
            bool: Успешность операции
        """
        try:
            with self.trace_lock:
                traces_data = []
                
                for trace in self.completed_traces:
                    trace_dict = {
                        'operation_id': trace.operation_id,
                        'operation_name': trace.operation_name,
                        'component': trace.metadata.get('component', 'unknown'),
                        'start_time': datetime.fromtimestamp(trace.start_time, timezone.utc).isoformat(),
                        'end_time': datetime.fromtimestamp(trace.end_time, timezone.utc).isoformat(),
                        'duration_ms': trace.duration_ms,
                        'status': trace.status,
                        'memory_delta_mb': trace.memory_delta_mb,
                        'error_message': trace.error_message,
                        'metadata': trace.metadata
                    }
                    traces_data.append(trace_dict)
                
                if format.lower() == "json":
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(traces_data, f, indent=2, ensure_ascii=False)
                elif format.lower() == "csv":
                    import csv
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        if traces_data:
                            fieldnames = traces_data[0].keys()
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            for trace in traces_data:
                                # Преобразуем сложные поля в строки
                                trace_csv = trace.copy()
                                trace_csv['metadata'] = json.dumps(trace['metadata'])
                                writer.writerow(trace_csv)
                
                logger.info(f"✅ Экспортировано {len(traces_data)} трейсов в {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта трейсов: {e}")
            return False
    
    def clear_metrics(self):
        """Очистка накопленных метрик и трейсов"""
        try:
            with self.trace_lock:
                self.completed_traces.clear()
                self.stats = MetricsStats()
                self._operation_counter = 0
                
            logger.info("✅ Метрики и трейсы очищены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки метрик: {e}")


# Глобальный экземпляр для удобства использования
_global_metrics_collector = None

def get_global_metrics_collector() -> MetricsCollectorV2:
    """Получение глобального экземпляра MetricsCollector"""
    global _global_metrics_collector
    
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollectorV2()
    
    return _global_metrics_collector

def init_global_metrics(enable_prometheus: bool = True, enable_tracing: bool = True,
                       metrics_port: int = 8000) -> MetricsCollectorV2:
    """Инициализация глобального MetricsCollector с настройками"""
    global _global_metrics_collector
    
    _global_metrics_collector = MetricsCollectorV2(
        enable_prometheus=enable_prometheus,
        enable_tracing=enable_tracing,
        metrics_port=metrics_port
    )
    
    return _global_metrics_collector

# Convenience функции для быстрого использования
def trace_operation(operation_name: str, component: str = "unknown", 
                   metadata: Dict[str, Any] = None):
    """Быстрый доступ к трейсингу операций"""
    return get_global_metrics_collector().trace_operation(operation_name, component, metadata)

def measure_performance(operation_name: str = None, component: str = "unknown"):
    """Быстрый доступ к декоратору измерения производительности"""
    return get_global_metrics_collector().measure_performance(
        operation_name=operation_name, component=component
    ) 