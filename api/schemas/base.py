"""
=============================================================================
MONITO API BASE SCHEMAS
=============================================================================
Версия: 3.0
Цель: Базовые Pydantic схемы для валидации данных API
=============================================================================
"""

from typing import Any, Dict, List, Optional, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field, validator

# Generic type для пагинированных ответов
T = TypeVar('T')

class BaseResponse(BaseModel):
    """Базовая схема ответа API"""
    
    success: bool = Field(True, description="Статус успешности операции")
    message: Optional[str] = Field(None, description="Сообщение о результате")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Время ответа")
    request_id: Optional[str] = Field(None, description="ID запроса для трассировки")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789"
            }
        }

class ErrorResponse(BaseResponse):
    """Схема ответа с ошибкой"""
    
    success: bool = Field(False, description="Статус ошибки")
    error_code: Optional[str] = Field(None, description="Код ошибки")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Детали ошибки")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "Validation error occurred",
                "error_code": "VALIDATION_ERROR",
                "error_details": {
                    "field": "product_name",
                    "reason": "Field is required"
                },
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789"
            }
        }

class PaginationParams(BaseModel):
    """Параметры пагинации"""
    
    page: int = Field(1, ge=1, description="Номер страницы (начиная с 1)")
    limit: int = Field(50, ge=1, le=1000, description="Количество элементов на странице")
    
    @property
    def offset(self) -> int:
        """Рассчитать offset для SQL запроса"""
        return (self.page - 1) * self.limit
    
    class Config:
        schema_extra = {
            "example": {
                "page": 1,
                "limit": 50
            }
        }

class PaginatedResponse(BaseResponse, Generic[T]):
    """Пагинированный ответ API"""
    
    data: List[T] = Field(description="Данные страницы")
    pagination: Dict[str, Any] = Field(description="Информация о пагинации")
    
    @classmethod
    def create(cls, data: List[T], page: int, limit: int, total: int, **kwargs):
        """
        Создание пагинированного ответа
        
        Args:
            data: Данные для страницы
            page: Номер текущей страницы
            limit: Размер страницы
            total: Общее количество элементов
            **kwargs: Дополнительные параметры для BaseResponse
        """
        total_pages = (total + limit - 1) // limit  # Ceiling division
        
        return cls(
            data=data,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "next_page": page + 1 if page < total_pages else None,
                "prev_page": page - 1 if page > 1 else None
            },
            **kwargs
        )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {"id": 1, "name": "Example Item 1"},
                    {"id": 2, "name": "Example Item 2"}
                ],
                "pagination": {
                    "page": 1,
                    "limit": 50,
                    "total": 150,
                    "total_pages": 3,
                    "has_next": True,
                    "has_prev": False,
                    "next_page": 2,
                    "prev_page": None
                },
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }

class HealthCheckResponse(BaseResponse):
    """Схема ответа health check"""
    
    status: str = Field("healthy", description="Статус здоровья системы")
    version: str = Field("3.0.0", description="Версия API")
    uptime_seconds: float = Field(description="Время работы в секундах")
    database_status: str = Field(description="Статус подключения к БД")
    unified_system_status: str = Field(description="Статус unified системы")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "status": "healthy",
                "version": "3.0.0",
                "uptime_seconds": 3600.5,
                "database_status": "connected",
                "unified_system_status": "operational",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }

class SearchFilters(BaseModel):
    """Базовые фильтры для поиска"""
    
    category: Optional[str] = Field(None, description="Фильтр по категории")
    brand: Optional[str] = Field(None, description="Фильтр по бренду")
    supplier: Optional[str] = Field(None, description="Фильтр по поставщику")
    price_min: Optional[float] = Field(None, ge=0, description="Минимальная цена")
    price_max: Optional[float] = Field(None, ge=0, description="Максимальная цена")
    
    @validator('price_max')
    def validate_price_range(cls, v, values):
        """Валидация диапазона цен"""
        if v is not None and 'price_min' in values and values['price_min'] is not None:
            if v < values['price_min']:
                raise ValueError('price_max must be greater than or equal to price_min')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "category": "beverages",
                "brand": "Coca-Cola",
                "supplier": "PT Global Supply",
                "price_min": 5000,
                "price_max": 50000
            }
        }

class SortParams(BaseModel):
    """Параметры сортировки"""
    
    sort_by: str = Field("created_at", description="Поле для сортировки")
    sort_order: str = Field("desc", regex="^(asc|desc)$", description="Порядок сортировки")
    
    class Config:
        schema_extra = {
            "example": {
                "sort_by": "price",
                "sort_order": "asc"
            }
        }

class BulkOperationResponse(BaseResponse):
    """Ответ для массовых операций"""
    
    total_processed: int = Field(description="Общее количество обработанных элементов")
    successful: int = Field(description="Количество успешно обработанных")
    failed: int = Field(description="Количество неудачных операций")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Список ошибок")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "total_processed": 100,
                "successful": 98,
                "failed": 2,
                "errors": [
                    {
                        "index": 15,
                        "error": "Invalid price format",
                        "item_id": "prod_123"
                    }
                ],
                "timestamp": "2024-01-01T12:00:00Z"
            }
        } 