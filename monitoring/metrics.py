import json
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """Системные метрики"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float

@dataclass
class ProcessingMetrics:
    """Метрики обработки"""
    timestamp: float
    files_processed_total: int
    files_processed_last_hour: int
    success_rate: float
    avg_processing_time: float
    excel_success_rate: float
    pdf_success_rate: float
    ocr_accuracy: float
    errors_last_hour: int

@dataclass
class BusinessMetrics:
    """Бизнес метрики"""
    timestamp: float
    total_products: int
    total_suppliers: int
    new_products_today: int
    new_suppliers_today: int
    price_updates_today: int
    most_active_supplier: str
    categories_count: int

class MetricsCollector:
    """Сборщик метрик системы"""
    
    def __init__(self):
        self.metrics_file = "data/metrics.json"
        self.system_metrics_history = []
        self.processing_metrics_history = []
        self.business_metrics_history = []
        self.max_history_items = 1440  # 24 часа при сборе каждую минуту
        
    def collect_system_metrics(self) -> SystemMetrics:
        """Сбор системных метрик"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Память
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Диск
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            metrics = SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb
            )
            
            # Добавление в историю
            self.system_metrics_history.append(metrics)
            self._trim_history(self.system_metrics_history)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Ошибка сбора системных метрик: {e}")
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=0,
                memory_percent=0,
                memory_used_mb=0,
                memory_available_mb=0,
                disk_usage_percent=0,
                disk_free_gb=0
            )

    def collect_processing_metrics(self) -> ProcessingMetrics:
        """Сбор метрик обработки файлов"""
        try:
            from modules.data_manager import DataManager
            
            data_manager = DataManager()
            stats = data_manager.get_processing_stats()
            
            # Подсчет файлов за последний час
            files_last_hour = self._count_recent_files(hours=1)
            errors_last_hour = self._count_recent_errors(hours=1)
            
            metrics = ProcessingMetrics(
                timestamp=time.time(),
                files_processed_total=stats.get('files_processed', 0),
                files_processed_last_hour=files_last_hour,
                success_rate=stats.get('success_rate', 0),
                avg_processing_time=stats.get('avg_processing_time', 0),
                excel_success_rate=stats.get('excel_success_rate', 0),
                pdf_success_rate=stats.get('pdf_success_rate', 0),
                ocr_accuracy=stats.get('ocr_accuracy', 0),
                errors_last_hour=errors_last_hour
            )
            
            # Добавление в историю
            self.processing_metrics_history.append(metrics)
            self._trim_history(self.processing_metrics_history)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Ошибка сбора метрик обработки: {e}")
            return ProcessingMetrics(
                timestamp=time.time(),
                files_processed_total=0,
                files_processed_last_hour=0,
                success_rate=0,
                avg_processing_time=0,
                excel_success_rate=0,
                pdf_success_rate=0,
                ocr_accuracy=0,
                errors_last_hour=0
            )

    def collect_business_metrics(self) -> BusinessMetrics:
        """Сбор бизнес метрик"""
        try:
            from modules.data_manager import DataManager
            
            data_manager = DataManager()
            table_summary = data_manager.get_table_summary()
            
            # Подсчет активности за сегодня
            today_stats = self._get_today_activity()
            
            metrics = BusinessMetrics(
                timestamp=time.time(),
                total_products=table_summary.get('total_products', 0),
                total_suppliers=table_summary.get('total_suppliers', 0),
                new_products_today=today_stats.get('new_products', 0),
                new_suppliers_today=today_stats.get('new_suppliers', 0),
                price_updates_today=today_stats.get('price_updates', 0),
                most_active_supplier=today_stats.get('most_active_supplier', 'None'),
                categories_count=len(table_summary.get('categories', []))
            )
            
            # Добавление в историю
            self.business_metrics_history.append(metrics)
            self._trim_history(self.business_metrics_history)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Ошибка сбора бизнес метрик: {e}")
            return BusinessMetrics(
                timestamp=time.time(),
                total_products=0,
                total_suppliers=0,
                new_products_today=0,
                new_suppliers_today=0,
                price_updates_today=0,
                most_active_supplier='None',
                categories_count=0
            )

    def _count_recent_files(self, hours: int = 1) -> int:
        """Подсчет файлов обработанных за последние N часов"""
        try:
            # Здесь можно реализовать чтение логов или базы данных
            # Для простоты возвращаем 0
            return 0
        except:
            return 0

    def _count_recent_errors(self, hours: int = 1) -> int:
        """Подсчет ошибок за последние N часов"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Чтение лога ошибок
            error_count = 0
            log_file = "logs/app.log"
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if 'ERROR' in line or 'CRITICAL' in line:
                            # Простой подсчет без парсинга времени
                            error_count += 1
            
            return min(error_count, 100)  # Ограничиваем для безопасности
            
        except:
            return 0

    def _get_today_activity(self) -> Dict[str, Any]:
        """Получение активности за сегодня"""
        try:
            # Здесь можно реализовать анализ логов или базы данных
            # Для простоты возвращаем заглушки
            return {
                'new_products': 0,
                'new_suppliers': 0,
                'price_updates': 0,
                'most_active_supplier': 'Unknown'
            }
        except:
            return {
                'new_products': 0,
                'new_suppliers': 0,
                'price_updates': 0,
                'most_active_supplier': 'Unknown'
            }

    def _trim_history(self, history_list: List):
        """Обрезка истории до максимального размера"""
        while len(history_list) > self.max_history_items:
            history_list.pop(0)

    def save_metrics(self):
        """Сохранение метрик в файл"""
        try:
            metrics_data = {
                'last_updated': datetime.now().isoformat(),
                'system_metrics': [asdict(m) for m in self.system_metrics_history[-10:]],
                'processing_metrics': [asdict(m) for m in self.processing_metrics_history[-10:]],
                'business_metrics': [asdict(m) for m in self.business_metrics_history[-10:]]
            }
            
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Ошибка сохранения метрик: {e}")

    def get_latest_metrics(self) -> Dict[str, Any]:
        """Получение последних метрик"""
        try:
            system_metrics = self.collect_system_metrics()
            processing_metrics = self.collect_processing_metrics()
            business_metrics = self.collect_business_metrics()
            
            return {
                'system': asdict(system_metrics),
                'processing': asdict(processing_metrics),
                'business': asdict(business_metrics),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения метрик: {e}")
            return {}

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Получение сводки метрик"""
        try:
            latest = self.get_latest_metrics()
            
            # Анализ трендов
            system_trend = self._analyze_system_trend()
            processing_trend = self._analyze_processing_trend()
            
            return {
                'health_status': self._calculate_health_status(latest),
                'system_trend': system_trend,
                'processing_trend': processing_trend,
                'alerts': self._generate_alerts(latest),
                'recommendations': self._generate_recommendations(latest)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения сводки метрик: {e}")
            return {}

    def _calculate_health_status(self, metrics: Dict[str, Any]) -> str:
        """Расчет общего статуса здоровья системы"""
        try:
            system = metrics.get('system', {})
            processing = metrics.get('processing', {})
            
            # Критерии здоровья
            cpu_ok = system.get('cpu_percent', 0) < 80
            memory_ok = system.get('memory_percent', 0) < 85
            disk_ok = system.get('disk_usage_percent', 0) < 90
            success_rate_ok = processing.get('success_rate', 0) > 70
            
            issues = []
            if not cpu_ok:
                issues.append('high_cpu')
            if not memory_ok:
                issues.append('high_memory')
            if not disk_ok:
                issues.append('low_disk')
            if not success_rate_ok:
                issues.append('low_success_rate')
            
            if not issues:
                return 'healthy'
            elif len(issues) == 1:
                return 'warning'
            else:
                return 'critical'
                
        except:
            return 'unknown'

    def _analyze_system_trend(self) -> str:
        """Анализ тренда системных метрик"""
        try:
            if len(self.system_metrics_history) < 2:
                return 'stable'
            
            recent = self.system_metrics_history[-5:]  # Последние 5 точек
            
            # Анализ тренда CPU
            cpu_values = [m.cpu_percent for m in recent]
            cpu_trend = 'increasing' if cpu_values[-1] > cpu_values[0] else 'stable'
            
            # Анализ тренда памяти
            memory_values = [m.memory_percent for m in recent]
            memory_trend = 'increasing' if memory_values[-1] > memory_values[0] else 'stable'
            
            if cpu_trend == 'increasing' and memory_trend == 'increasing':
                return 'degrading'
            elif cpu_trend == 'increasing' or memory_trend == 'increasing':
                return 'warning'
            else:
                return 'stable'
                
        except:
            return 'stable'

    def _analyze_processing_trend(self) -> str:
        """Анализ тренда обработки"""
        try:
            if len(self.processing_metrics_history) < 2:
                return 'stable'
            
            recent = self.processing_metrics_history[-5:]
            
            # Анализ тренда успешности
            success_rates = [m.success_rate for m in recent]
            
            if len(success_rates) >= 2:
                if success_rates[-1] < success_rates[0] - 10:
                    return 'degrading'
                elif success_rates[-1] > success_rates[0] + 10:
                    return 'improving'
            
            return 'stable'
            
        except:
            return 'stable'

    def _generate_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Генерация алертов на основе метрик"""
        alerts = []
        
        try:
            system = metrics.get('system', {})
            processing = metrics.get('processing', {})
            
            # Системные алерты
            if system.get('cpu_percent', 0) > 90:
                alerts.append({
                    'type': 'critical',
                    'category': 'system',
                    'message': f"Высокая загрузка CPU: {system.get('cpu_percent', 0):.1f}%",
                    'timestamp': datetime.now().isoformat()
                })
            
            if system.get('memory_percent', 0) > 90:
                alerts.append({
                    'type': 'critical',
                    'category': 'system',
                    'message': f"Высокое использование памяти: {system.get('memory_percent', 0):.1f}%",
                    'timestamp': datetime.now().isoformat()
                })
            
            if system.get('disk_free_gb', 0) < 1:
                alerts.append({
                    'type': 'critical',
                    'category': 'system',
                    'message': f"Мало свободного места: {system.get('disk_free_gb', 0):.1f} GB",
                    'timestamp': datetime.now().isoformat()
                })
            
            # Алерты обработки
            if processing.get('success_rate', 0) < 50:
                alerts.append({
                    'type': 'warning',
                    'category': 'processing',
                    'message': f"Низкий процент успешной обработки: {processing.get('success_rate', 0):.1f}%",
                    'timestamp': datetime.now().isoformat()
                })
            
            if processing.get('errors_last_hour', 0) > 10:
                alerts.append({
                    'type': 'warning',
                    'category': 'processing',
                    'message': f"Много ошибок за последний час: {processing.get('errors_last_hour', 0)}",
                    'timestamp': datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Ошибка генерации алертов: {e}")
        
        return alerts

    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Генерация рекомендаций по оптимизации"""
        recommendations = []
        
        try:
            system = metrics.get('system', {})
            processing = metrics.get('processing', {})
            
            # Системные рекомендации
            if system.get('memory_percent', 0) > 80:
                recommendations.append("Рассмотрите увеличение объема RAM или оптимизацию использования памяти")
            
            if system.get('cpu_percent', 0) > 80:
                recommendations.append("Высокая загрузка CPU - рассмотрите масштабирование или оптимизацию кода")
            
            # Рекомендации по обработке
            if processing.get('pdf_success_rate', 0) < processing.get('excel_success_rate', 0) - 20:
                recommendations.append("PDF обработка менее эффективна - проверьте настройки OCR")
            
            if processing.get('avg_processing_time', 0) > 60:
                recommendations.append("Среднее время обработки велико - рассмотрите оптимизацию алгоритмов")
            
            if not recommendations:
                recommendations.append("Система работает в нормальном режиме")
            
        except Exception as e:
            logger.error(f"Ошибка генерации рекомендаций: {e}")
        
        return recommendations