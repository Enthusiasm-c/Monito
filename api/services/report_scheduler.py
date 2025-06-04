"""
=============================================================================
MONITO REPORT SCHEDULER & EMAIL SYSTEM
=============================================================================
Модуль для планирования автоматических отчетов и email рассылки
Версия: 4.2
=============================================================================
"""

import asyncio
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Any, Optional
import schedule
import time
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
import json

from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)

class ReportFrequency(Enum):
    """Частота генерации отчетов"""
    DAILY = "daily"
    WEEKLY = "weekly" 
    MONTHLY = "monthly"
    CUSTOM = "custom"

class ReportType(Enum):
    """Типы отчетов"""
    PRICE_ANALYSIS = "price_analysis"
    SUPPLIER_PERFORMANCE = "supplier_performance"
    COST_SAVINGS = "cost_savings"
    INVENTORY_SUMMARY = "inventory_summary"

@dataclass
class EmailSettings:
    """Настройки SMTP для отправки email"""
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    use_tls: bool = True
    sender_name: str = "Monito System"
    
@dataclass
class ReportSubscription:
    """Подписка на отчет"""
    id: str
    report_type: ReportType
    frequency: ReportFrequency
    recipients: List[str]
    format: str = "pdf"  # pdf или excel
    enabled: bool = True
    last_sent: Optional[datetime] = None
    custom_schedule: Optional[str] = None  # Для custom frequency (cron expression)
    filters: Optional[Dict[str, Any]] = None
    
class ReportScheduler:
    """Планировщик автоматических отчетов"""
    
    def __init__(self, email_settings: EmailSettings, output_dir: str = "reports"):
        self.email_settings = email_settings
        self.report_generator = ReportGenerator(output_dir)
        self.subscriptions: Dict[str, ReportSubscription] = {}
        self.is_running = False
        
        # Загружаем подписки из файла
        self.subscriptions_file = Path(output_dir) / "subscriptions.json"
        self._load_subscriptions()
        
    def _load_subscriptions(self):
        """Загружает подписки из файла"""
        try:
            if self.subscriptions_file.exists():
                with open(self.subscriptions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for sub_data in data:
                    subscription = ReportSubscription(
                        id=sub_data['id'],
                        report_type=ReportType(sub_data['report_type']),
                        frequency=ReportFrequency(sub_data['frequency']),
                        recipients=sub_data['recipients'],
                        format=sub_data.get('format', 'pdf'),
                        enabled=sub_data.get('enabled', True),
                        last_sent=datetime.fromisoformat(sub_data['last_sent']) if sub_data.get('last_sent') else None,
                        custom_schedule=sub_data.get('custom_schedule'),
                        filters=sub_data.get('filters')
                    )
                    self.subscriptions[subscription.id] = subscription
                    
        except Exception as e:
            logger.error(f"Error loading subscriptions: {e}")
    
    def _save_subscriptions(self):
        """Сохраняет подписки в файл"""
        try:
            data = []
            for subscription in self.subscriptions.values():
                data.append({
                    'id': subscription.id,
                    'report_type': subscription.report_type.value,
                    'frequency': subscription.frequency.value,
                    'recipients': subscription.recipients,
                    'format': subscription.format,
                    'enabled': subscription.enabled,
                    'last_sent': subscription.last_sent.isoformat() if subscription.last_sent else None,
                    'custom_schedule': subscription.custom_schedule,
                    'filters': subscription.filters
                })
            
            with open(self.subscriptions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error saving subscriptions: {e}")
    
    def add_subscription(self, subscription: ReportSubscription) -> str:
        """Добавляет новую подписку на отчет"""
        self.subscriptions[subscription.id] = subscription
        self._save_subscriptions()
        logger.info(f"Added subscription: {subscription.id}")
        return subscription.id
    
    def remove_subscription(self, subscription_id: str) -> bool:
        """Удаляет подписку"""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            self._save_subscriptions()
            logger.info(f"Removed subscription: {subscription_id}")
            return True
        return False
    
    def update_subscription(self, subscription_id: str, updates: Dict[str, Any]) -> bool:
        """Обновляет параметры подписки"""
        if subscription_id not in self.subscriptions:
            return False
        
        subscription = self.subscriptions[subscription_id]
        
        for key, value in updates.items():
            if hasattr(subscription, key):
                if key == 'report_type' and isinstance(value, str):
                    value = ReportType(value)
                elif key == 'frequency' and isinstance(value, str):
                    value = ReportFrequency(value)
                elif key == 'last_sent' and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                
                setattr(subscription, key, value)
        
        self._save_subscriptions()
        logger.info(f"Updated subscription: {subscription_id}")
        return True
    
    def get_subscriptions(self) -> List[ReportSubscription]:
        """Возвращает список всех подписок"""
        return list(self.subscriptions.values())
    
    def get_subscription(self, subscription_id: str) -> Optional[ReportSubscription]:
        """Возвращает подписку по ID"""
        return self.subscriptions.get(subscription_id)
    
    async def generate_and_send_report(self, subscription: ReportSubscription) -> bool:
        """Генерирует и отправляет отчет"""
        try:
            logger.info(f"Generating report for subscription: {subscription.id}")
            
            # Получаем данные для отчета
            report_data = await self._get_report_data(subscription.report_type, subscription.filters)
            
            # Генерируем отчет
            if subscription.report_type == ReportType.PRICE_ANALYSIS:
                report_bytes = self.report_generator.generate_price_analysis_report(
                    report_data, subscription.format
                )
            elif subscription.report_type == ReportType.SUPPLIER_PERFORMANCE:
                supplier_data = await self._get_supplier_data(subscription.filters)
                report_bytes = self.report_generator.generate_supplier_performance_report(
                    supplier_data, subscription.format
                )
            else:
                logger.error(f"Unsupported report type: {subscription.report_type}")
                return False
            
            # Формируем имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"monito_{subscription.report_type.value}_{timestamp}.{subscription.format}"
            
            # Отправляем по email
            success = await self._send_email_report(
                subscription, report_bytes, filename
            )
            
            if success:
                subscription.last_sent = datetime.now()
                self._save_subscriptions()
                logger.info(f"Report sent successfully: {subscription.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error generating/sending report for {subscription.id}: {e}")
            return False
    
    async def _get_report_data(self, report_type: ReportType, 
                             filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Получает данные для генерации отчета"""
        
        # В реальном приложении здесь будут запросы к базе данных
        # Пока возвращаем mock данные
        
        base_data = {
            'total_products': 1247,
            'total_suppliers': 23,
            'total_prices': 5420,
            'avg_savings': 15.3,
            'updates_today': 342,
            'api_response_time': 120,
            'system_health': 'excellent',
            'generated_at': datetime.now().isoformat()
        }
        
        if report_type == ReportType.PRICE_ANALYSIS:
            base_data.update({
                'top_categories': [
                    {'name': 'Напитки', 'savings': 15.2, 'products': 45},
                    {'name': 'Продукты', 'savings': 12.8, 'products': 32},
                    {'name': 'Хоз. товары', 'savings': 18.5, 'products': 28}
                ],
                'price_trends': {
                    'trend_direction': 'down',
                    'trend_percent': -2.5
                }
            })
        
        return base_data
    
    async def _get_supplier_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Получает данные о поставщиках"""
        
        # Mock данные поставщиков
        return [
            {
                'name': 'Bali Fresh Market',
                'product_count': 145,
                'avg_price': 15500,
                'rating': 4.8,
                'reliability': 95
            },
            {
                'name': 'Island Supplies Co',
                'product_count': 98,
                'avg_price': 16200,
                'rating': 4.6,
                'reliability': 92
            },
            {
                'name': 'Tropical Goods Ltd',
                'product_count': 76,
                'avg_price': 14800,
                'rating': 4.9,
                'reliability': 98
            }
        ]
    
    async def _send_email_report(self, subscription: ReportSubscription, 
                               report_bytes: bytes, filename: str) -> bool:
        """Отправляет отчет по email"""
        
        try:
            # Создаем email сообщение
            msg = MIMEMultipart()
            msg['From'] = f"{self.email_settings.sender_name} <{self.email_settings.username}>"
            msg['To'] = ", ".join(subscription.recipients)
            msg['Subject'] = f"🏝️ Monito Report - {subscription.report_type.value.replace('_', ' ').title()}"
            
            # Тело письма
            body = self._create_email_body(subscription)
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # Прикрепляем отчет
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(report_bytes)
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(attachment)
            
            # Отправляем
            server = smtplib.SMTP(self.email_settings.smtp_server, self.email_settings.smtp_port)
            
            if self.email_settings.use_tls:
                server.starttls()
            
            server.login(self.email_settings.username, self.email_settings.password)
            server.sendmail(self.email_settings.username, subscription.recipients, msg.as_string())
            server.quit()
            
            logger.info(f"Email sent to: {subscription.recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _create_email_body(self, subscription: ReportSubscription) -> str:
        """Создает HTML тело письма"""
        
        report_title = subscription.report_type.value.replace('_', ' ').title()
        frequency_text = subscription.frequency.value.capitalize()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #4A90E2 0%, #7B68EE 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; }}
                .btn {{ display: inline-block; background-color: #4A90E2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
                .metrics {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .metric {{ text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #4A90E2; }}
                .metric-label {{ font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏝️ Monito Report</h1>
                    <p>{report_title}</p>
                </div>
                
                <div class="content">
                    <p>Здравствуйте!</p>
                    
                    <p>Ваш {frequency_text.lower()} отчет по системе Monito готов. Отчет содержит актуальную информацию о ценах поставщиков острова Бали.</p>
                    
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value">1,247</div>
                            <div class="metric-label">Товаров</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">23</div>
                            <div class="metric-label">Поставщиков</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">15.3%</div>
                            <div class="metric-label">Экономия</div>
                        </div>
                    </div>
                    
                    <p><strong>В прикрепленном файле вы найдете:</strong></p>
                    <ul>
                        <li>📊 Подробную аналитику цен</li>
                        <li>💰 Анализ экономии по категориям</li>
                        <li>📈 Тренды изменения цен</li>
                        <li>🎯 Рекомендации по оптимизации закупок</li>
                    </ul>
                    
                    <p>Отчет сгенерирован автоматически {datetime.now().strftime('%d.%m.%Y в %H:%M')}.</p>
                    
                    <p style="text-align: center;">
                        <a href="http://localhost:5173" class="btn">Открыть Dashboard</a>
                    </p>
                </div>
                
                <div class="footer">
                    <p>© 2025 Monito Unified Price Management System</p>
                    <p>🏝️ Управление ценами поставщиков острова Бали</p>
                    <p>Для отмены подписки обратитесь к администратору системы</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def start_scheduler(self):
        """Запускает планировщик отчетов"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        logger.info("Starting report scheduler")
        
        # Настраиваем расписание
        schedule.every().hour.do(self._check_and_send_reports)
        
        # Запускаем в отдельном потоке
        asyncio.create_task(self._scheduler_loop())
    
    def stop_scheduler(self):
        """Останавливает планировщик"""
        self.is_running = False
        schedule.clear()
        logger.info("Report scheduler stopped")
    
    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self.is_running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Проверяем каждую минуту
    
    def _check_and_send_reports(self):
        """Проверяет и отправляет отчеты по расписанию"""
        current_time = datetime.now()
        
        for subscription in self.subscriptions.values():
            if not subscription.enabled:
                continue
            
            should_send = False
            
            # Проверяем нужно ли отправлять отчет
            if subscription.frequency == ReportFrequency.DAILY:
                if not subscription.last_sent or \
                   current_time - subscription.last_sent >= timedelta(days=1):
                    should_send = True
                    
            elif subscription.frequency == ReportFrequency.WEEKLY:
                if not subscription.last_sent or \
                   current_time - subscription.last_sent >= timedelta(weeks=1):
                    should_send = True
                    
            elif subscription.frequency == ReportFrequency.MONTHLY:
                if not subscription.last_sent or \
                   current_time - subscription.last_sent >= timedelta(days=30):
                    should_send = True
            
            if should_send:
                # Запускаем отправку отчета
                asyncio.create_task(self.generate_and_send_report(subscription))
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Возвращает статус планировщика"""
        return {
            'is_running': self.is_running,
            'active_subscriptions': len([s for s in self.subscriptions.values() if s.enabled]),
            'total_subscriptions': len(self.subscriptions),
            'next_check': schedule.next_run() if schedule.jobs else None,
            'last_activity': datetime.now().isoformat()
        } 