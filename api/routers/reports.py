"""
=============================================================================
REPORTS API ROUTER
=============================================================================
API endpoints для системы отчетности Monito
Версия: 4.2  
=============================================================================
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import io
import logging

from ..services.report_generator import ReportGenerator
from ..services.report_scheduler import (
    ReportScheduler, ReportSubscription, ReportType, 
    ReportFrequency, EmailSettings
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])

# === Pydantic Models ===

class ReportFormatEnum(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"

class ReportTypeEnum(str, Enum):
    PRICE_ANALYSIS = "price_analysis"
    SUPPLIER_PERFORMANCE = "supplier_performance"
    COST_SAVINGS = "cost_savings"
    INVENTORY_SUMMARY = "inventory_summary"

class ReportFrequencyEnum(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

class GenerateReportRequest(BaseModel):
    report_type: ReportTypeEnum
    format: ReportFormatEnum = ReportFormatEnum.PDF
    filters: Optional[Dict[str, Any]] = None
    include_charts: bool = True

class CreateSubscriptionRequest(BaseModel):
    report_type: ReportTypeEnum
    frequency: ReportFrequencyEnum
    recipients: List[EmailStr]
    format: ReportFormatEnum = ReportFormatEnum.PDF
    enabled: bool = True
    custom_schedule: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

class UpdateSubscriptionRequest(BaseModel):
    frequency: Optional[ReportFrequencyEnum] = None
    recipients: Optional[List[EmailStr]] = None
    format: Optional[ReportFormatEnum] = None
    enabled: Optional[bool] = None
    custom_schedule: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

class EmailSettingsRequest(BaseModel):
    smtp_server: str
    smtp_port: int = 587
    username: str
    password: str
    use_tls: bool = True
    sender_name: str = "Monito System"

class ReportResponse(BaseModel):
    id: str
    filename: str
    format: str
    size_bytes: int
    generated_at: datetime
    download_url: str

class SubscriptionResponse(BaseModel):
    id: str
    report_type: str
    frequency: str
    recipients: List[str]
    format: str
    enabled: bool
    last_sent: Optional[datetime]
    created_at: datetime

class SchedulerStatusResponse(BaseModel):
    is_running: bool
    active_subscriptions: int
    total_subscriptions: int
    next_check: Optional[datetime]
    last_activity: datetime

# === Global Services ===
report_generator = ReportGenerator("reports")
report_scheduler: Optional[ReportScheduler] = None

# === Helper Functions ===

def get_report_scheduler() -> ReportScheduler:
    """Dependency для получения планировщика отчетов"""
    global report_scheduler
    if report_scheduler is None:
        raise HTTPException(status_code=503, detail="Report scheduler not configured")
    return report_scheduler

async def get_mock_data(report_type: ReportTypeEnum) -> Dict[str, Any]:
    """Получает mock данные для генерации отчетов"""
    base_data = {
        'total_products': 1247,
        'total_suppliers': 23,
        'total_prices': 5420,
        'avg_savings': 15.3,
        'updates_today': 342,
        'api_response_time': 120,
        'system_health': 'excellent'
    }
    
    if report_type == ReportTypeEnum.PRICE_ANALYSIS:
        base_data.update({
            'top_categories': [
                {'name': 'Напитки', 'savings': 15.2, 'products': 45},
                {'name': 'Продукты', 'savings': 12.8, 'products': 32},
                {'name': 'Хоз. товары', 'savings': 18.5, 'products': 28}
            ]
        })
    
    return base_data

async def get_mock_supplier_data() -> List[Dict[str, Any]]:
    """Получает mock данные поставщиков"""
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

# === API Endpoints ===

@router.post("/generate", response_model=Dict[str, Any])
async def generate_report(request: GenerateReportRequest):
    """
    Генерирует отчет в реальном времени
    
    Поддерживаемые типы отчетов:
    - price_analysis: Анализ цен и экономии
    - supplier_performance: Производительность поставщиков
    """
    
    try:
        logger.info(f"Generating {request.report_type} report in {request.format} format")
        
        # Получаем данные для отчета
        if request.report_type == ReportTypeEnum.PRICE_ANALYSIS:
            data = await get_mock_data(request.report_type)
            report_bytes = report_generator.generate_price_analysis_report(
                data, request.format.value
            )
        elif request.report_type == ReportTypeEnum.SUPPLIER_PERFORMANCE:
            supplier_data = await get_mock_supplier_data()
            report_bytes = report_generator.generate_supplier_performance_report(
                supplier_data, request.format.value
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported report type: {request.report_type}")
        
        # Формируем ответ
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"monito_{request.report_type.value}_{timestamp}.{request.format.value}"
        
        return {
            "message": "Report generated successfully",
            "filename": filename,
            "format": request.format.value,
            "size_bytes": len(report_bytes),
            "generated_at": datetime.now().isoformat(),
            "download_ready": True
        }
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@router.post("/download")
async def download_report(request: GenerateReportRequest):
    """
    Генерирует и сразу отдает отчет для скачивания
    """
    
    try:
        # Получаем данные и генерируем отчет
        if request.report_type == ReportTypeEnum.PRICE_ANALYSIS:
            data = await get_mock_data(request.report_type)
            report_bytes = report_generator.generate_price_analysis_report(
                data, request.format.value
            )
        elif request.report_type == ReportTypeEnum.SUPPLIER_PERFORMANCE:
            supplier_data = await get_mock_supplier_data()
            report_bytes = report_generator.generate_supplier_performance_report(
                supplier_data, request.format.value
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported report type: {request.report_type}")
        
        # Формируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"monito_{request.report_type.value}_{timestamp}.{request.format.value}"
        
        # Определяем MIME type
        if request.format == ReportFormatEnum.PDF:
            media_type = "application/pdf"
        else:
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        # Возвращаем файл
        return StreamingResponse(
            io.BytesIO(report_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        raise HTTPException(status_code=500, detail=f"Error downloading report: {str(e)}")

@router.post("/email/settings")
async def configure_email_settings(settings: EmailSettingsRequest):
    """Настраивает параметры SMTP для отправки отчетов"""
    
    global report_scheduler
    
    try:
        email_settings = EmailSettings(
            smtp_server=settings.smtp_server,
            smtp_port=settings.smtp_port,
            username=settings.username,
            password=settings.password,
            use_tls=settings.use_tls,
            sender_name=settings.sender_name
        )
        
        # Создаем новый планировщик с обновленными настройками
        report_scheduler = ReportScheduler(email_settings, "reports")
        
        logger.info("Email settings configured successfully")
        
        return {
            "message": "Email settings configured successfully",
            "smtp_server": settings.smtp_server,
            "smtp_port": settings.smtp_port,
            "sender_name": settings.sender_name
        }
        
    except Exception as e:
        logger.error(f"Error configuring email settings: {e}")
        raise HTTPException(status_code=500, detail=f"Error configuring email: {str(e)}")

@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    scheduler: ReportScheduler = Depends(get_report_scheduler)
):
    """Создает подписку на автоматические отчеты"""
    
    try:
        subscription_id = str(uuid.uuid4())
        
        subscription = ReportSubscription(
            id=subscription_id,
            report_type=ReportType(request.report_type.value),
            frequency=ReportFrequency(request.frequency.value),
            recipients=request.recipients,
            format=request.format.value,
            enabled=request.enabled,
            custom_schedule=request.custom_schedule,
            filters=request.filters
        )
        
        scheduler.add_subscription(subscription)
        
        logger.info(f"Created subscription: {subscription_id}")
        
        return SubscriptionResponse(
            id=subscription.id,
            report_type=subscription.report_type.value,
            frequency=subscription.frequency.value,
            recipients=subscription.recipients,
            format=subscription.format,
            enabled=subscription.enabled,
            last_sent=subscription.last_sent,
            created_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating subscription: {str(e)}")

@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_subscriptions(scheduler: ReportScheduler = Depends(get_report_scheduler)):
    """Получает список всех подписок"""
    
    try:
        subscriptions = scheduler.get_subscriptions()
        
        return [
            SubscriptionResponse(
                id=sub.id,
                report_type=sub.report_type.value,
                frequency=sub.frequency.value,
                recipients=sub.recipients,
                format=sub.format,
                enabled=sub.enabled,
                last_sent=sub.last_sent,
                created_at=datetime.now()  # В реальном приложении это будет храниться в БД
            )
            for sub in subscriptions
        ]
        
    except Exception as e:
        logger.error(f"Error getting subscriptions: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting subscriptions: {str(e)}")

@router.put("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    request: UpdateSubscriptionRequest,
    scheduler: ReportScheduler = Depends(get_report_scheduler)
):
    """Обновляет параметры подписки"""
    
    try:
        # Проверяем существование подписки
        subscription = scheduler.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Подготавливаем обновления
        updates = {}
        if request.frequency is not None:
            updates['frequency'] = request.frequency.value
        if request.recipients is not None:
            updates['recipients'] = request.recipients
        if request.format is not None:
            updates['format'] = request.format.value
        if request.enabled is not None:
            updates['enabled'] = request.enabled
        if request.custom_schedule is not None:
            updates['custom_schedule'] = request.custom_schedule
        if request.filters is not None:
            updates['filters'] = request.filters
        
        # Обновляем подписку
        success = scheduler.update_subscription(subscription_id, updates)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update subscription")
        
        # Получаем обновленную подписку
        updated_subscription = scheduler.get_subscription(subscription_id)
        
        return SubscriptionResponse(
            id=updated_subscription.id,
            report_type=updated_subscription.report_type.value,
            frequency=updated_subscription.frequency.value,
            recipients=updated_subscription.recipients,
            format=updated_subscription.format,
            enabled=updated_subscription.enabled,
            last_sent=updated_subscription.last_sent,
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating subscription: {str(e)}")

@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    scheduler: ReportScheduler = Depends(get_report_scheduler)
):
    """Удаляет подписку"""
    
    try:
        success = scheduler.remove_subscription(subscription_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        return {"message": f"Subscription {subscription_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting subscription: {str(e)}")

@router.post("/subscriptions/{subscription_id}/send")
async def send_report_now(
    subscription_id: str,
    background_tasks: BackgroundTasks,
    scheduler: ReportScheduler = Depends(get_report_scheduler)
):
    """Отправляет отчет немедленно (не дожидаясь расписания)"""
    
    try:
        subscription = scheduler.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        if not subscription.enabled:
            raise HTTPException(status_code=400, detail="Subscription is disabled")
        
        # Запускаем отправку в фоне
        background_tasks.add_task(scheduler.generate_and_send_report, subscription)
        
        return {
            "message": f"Report generation and sending started for subscription {subscription_id}",
            "subscription_id": subscription_id,
            "recipients": subscription.recipients
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending report: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending report: {str(e)}")

@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status(scheduler: ReportScheduler = Depends(get_report_scheduler)):
    """Получает статус планировщика отчетов"""
    
    try:
        status = scheduler.get_scheduler_status()
        
        return SchedulerStatusResponse(
            is_running=status['is_running'],
            active_subscriptions=status['active_subscriptions'],
            total_subscriptions=status['total_subscriptions'],
            next_check=status.get('next_check'),
            last_activity=datetime.fromisoformat(status['last_activity'])
        )
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting scheduler status: {str(e)}")

@router.post("/scheduler/start")
async def start_scheduler(scheduler: ReportScheduler = Depends(get_report_scheduler)):
    """Запускает планировщик автоматических отчетов"""
    
    try:
        scheduler.start_scheduler()
        
        return {
            "message": "Report scheduler started successfully",
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting scheduler: {str(e)}")

@router.post("/scheduler/stop")
async def stop_scheduler(scheduler: ReportScheduler = Depends(get_report_scheduler)):
    """Останавливает планировщик отчетов"""
    
    try:
        scheduler.stop_scheduler()
        
        return {
            "message": "Report scheduler stopped successfully",
            "status": "stopped"
        }
        
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise HTTPException(status_code=500, detail=f"Error stopping scheduler: {str(e)}")

@router.get("/templates")
async def get_report_templates():
    """Получает список доступных шаблонов отчетов"""
    
    return {
        "templates": [
            {
                "id": "price_analysis",
                "name": "Анализ Цен",
                "description": "Подробный анализ цен, трендов и экономии по категориям",
                "formats": ["pdf", "excel"],
                "sections": ["Основные показатели", "Топ категории", "Тренды цен", "Рекомендации"]
            },
            {
                "id": "supplier_performance",
                "name": "Производительность Поставщиков",
                "description": "Оценка эффективности поставщиков и их рейтинги",
                "formats": ["pdf", "excel"],
                "sections": ["Рейтинги поставщиков", "Статистика товаров", "Надежность доставки"]
            }
        ]
    }

@router.get("/test/pdf")
async def test_pdf_generation():
    """Тестовый endpoint для проверки генерации PDF"""
    
    try:
        test_data = await get_mock_data(ReportTypeEnum.PRICE_ANALYSIS)
        report_bytes = report_generator.generate_price_analysis_report(test_data, "pdf")
        
        filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return StreamingResponse(
            io.BytesIO(report_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating test PDF: {str(e)}")

@router.get("/test/excel")  
async def test_excel_generation():
    """Тестовый endpoint для проверки генерации Excel"""
    
    try:
        test_data = await get_mock_data(ReportTypeEnum.PRICE_ANALYSIS)
        report_bytes = report_generator.generate_price_analysis_report(test_data, "excel")
        
        filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(report_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating test Excel: {str(e)}") 