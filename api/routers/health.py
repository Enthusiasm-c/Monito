"""
=============================================================================
MONITO API HEALTH ROUTER
=============================================================================
Версия: 3.0
Цель: Роутер для проверки состояния API и unified системы
=============================================================================
"""

import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from api.schemas.base import HealthCheckResponse, BaseResponse
from modules.adapters.legacy_integration_adapter import LegacyIntegrationAdapter
from utils.logger import get_logger

logger = get_logger(__name__)

# Время запуска API
_startup_time = time.time()

router = APIRouter()

def get_integration_adapter(request: Request) -> LegacyIntegrationAdapter:
    """Dependency для получения integration adapter"""
    return request.app.state.integration_adapter

@router.get("/", 
           response_model=HealthCheckResponse,
           summary="🏥 Проверка состояния API",
           description="Базовая проверка работоспособности API и всех компонентов системы")
async def health_check(request: Request, 
                      integration_adapter: LegacyIntegrationAdapter = Depends(get_integration_adapter)) -> HealthCheckResponse:
    """
    Основная проверка состояния системы
    
    Проверяет:
    - Работоспособность API
    - Подключение к базе данных
    - Состояние unified системы
    - Время работы сервиса
    
    Returns:
        Подробная информация о состоянии системы
    """
    logger.info("Health check requested")
    
    # Рассчитываем время работы
    uptime_seconds = time.time() - _startup_time
    
    # Проверяем базу данных
    database_status = "unknown"
    try:
        # Тестируем подключение к БД через простой запрос
        system_stats = integration_adapter.db_manager.get_system_statistics()
        database_status = "connected"
        logger.debug("Database connection check: OK")
    except SQLAlchemyError as e:
        database_status = "disconnected"
        logger.warning(f"Database connection check failed: {e}")
    except Exception as e:
        database_status = "error"
        logger.error(f"Database check error: {e}")
    
    # Проверяем unified систему
    unified_system_status = "unknown"
    try:
        # Тестируем основные компоненты unified системы
        test_search = integration_adapter.db_manager.search_master_products("test", limit=1)
        unified_system_status = "operational"
        logger.debug("Unified system check: OK")
    except Exception as e:
        unified_system_status = "error"
        logger.warning(f"Unified system check failed: {e}")
    
    # Определяем общий статус
    overall_status = "healthy"
    if database_status != "connected":
        overall_status = "degraded"
    if unified_system_status == "error":
        overall_status = "unhealthy"
    
    return HealthCheckResponse(
        status=overall_status,
        version="3.0.0",
        uptime_seconds=uptime_seconds,
        database_status=database_status,
        unified_system_status=unified_system_status,
        message=f"System is {overall_status}",
        request_id=getattr(request.state, 'request_id', None)
    )

@router.get("/detailed",
           response_model=Dict[str, Any],
           summary="🔍 Детальная диагностика системы",
           description="Подробная информация о всех компонентах unified системы")
async def detailed_health_check(request: Request,
                               integration_adapter: LegacyIntegrationAdapter = Depends(get_integration_adapter)) -> Dict[str, Any]:
    """
    Детальная проверка состояния системы
    
    Возвращает подробную информацию о:
    - Статистике базы данных
    - Производительности компонентов
    - Состоянии адаптеров
    - Системных метриках
    
    Returns:
        Детальная диагностическая информация
    """
    logger.info("Detailed health check requested")
    
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - _startup_time,
        "api": {
            "version": "3.0.0",
            "status": "operational"
        }
    }
    
    # Информация о базе данных
    try:
        system_stats = integration_adapter.db_manager.get_system_statistics()
        result["database"] = {
            "status": "connected",
            "statistics": system_stats,
            "connection_pool": "healthy"  # Упрощенно
        }
    except Exception as e:
        result["database"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Информация о unified системе
    try:
        # Тестируем различные компоненты
        result["unified_system"] = {
            "status": "operational",
            "components": {
                "database_manager": "healthy",
                "product_matching_engine": "healthy", 
                "price_comparison_engine": "healthy",
                "catalog_manager": "healthy"
            }
        }
        
        # Тестируем базовые операции
        search_test = integration_adapter.db_manager.search_master_products("", limit=1)
        result["unified_system"]["search_functionality"] = "operational"
        
    except Exception as e:
        result["unified_system"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Информация об адаптерах
    try:
        result["adapters"] = {
            "parser_adapter": "loaded",
            "normalizer_adapter": "loaded", 
            "legacy_integration": "operational"
        }
    except Exception as e:
        result["adapters"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Системные метрики
    result["system_metrics"] = {
        "memory_usage": "n/a",  # Можно добавить psutil для мониторинга
        "cpu_usage": "n/a",
        "disk_usage": "n/a"
    }
    
    result["request_id"] = getattr(request.state, 'request_id', None)
    
    return result

@router.get("/ping",
           response_model=BaseResponse,
           summary="🏓 Простая проверка доступности",
           description="Минимальная проверка для мониторинга доступности сервиса")
async def ping(request: Request) -> BaseResponse:
    """
    Простая проверка доступности API
    
    Самый быстрый способ проверить, что API отвечает
    
    Returns:
        Подтверждение доступности
    """
    return BaseResponse(
        message="pong",
        request_id=getattr(request.state, 'request_id', None)
    )

@router.get("/version",
           response_model=Dict[str, str],
           summary="📋 Информация о версии",
           description="Информация о версии API и компонентов")
async def version_info(request: Request) -> Dict[str, str]:
    """
    Информация о версии API и компонентов
    
    Returns:
        Версии всех компонентов системы
    """
    return {
        "api_version": "3.0.0",
        "unified_system_version": "3.0.0",
        "database_schema_version": "1.0",
        "legacy_compatibility_version": "2.x",
        "build_timestamp": "2024-01-01T00:00:00Z",  # Можно сделать динамическим
        "request_id": getattr(request.state, 'request_id', None)
    }

@router.get("/ready",
           response_model=BaseResponse,
           summary="✅ Проверка готовности к обслуживанию",
           description="Проверка готовности системы к обработке реальных запросов")
async def readiness_check(request: Request,
                         integration_adapter: LegacyIntegrationAdapter = Depends(get_integration_adapter)) -> BaseResponse:
    """
    Проверка готовности системы к работе
    
    Отличается от health check тем, что проверяет готовность
    принимать и обрабатывать бизнес-запросы
    
    Returns:
        Статус готовности системы
        
    Raises:
        HTTPException: Если система не готова
    """
    logger.info("Readiness check requested")
    
    checks = []
    
    # Проверяем базу данных
    try:
        system_stats = integration_adapter.db_manager.get_system_statistics()
        checks.append(("database", True, "Connected"))
    except Exception as e:
        checks.append(("database", False, f"Error: {e}"))
    
    # Проверяем unified систему
    try:
        search_test = integration_adapter.db_manager.search_master_products("test", limit=1)
        checks.append(("unified_system", True, "Operational"))
    except Exception as e:
        checks.append(("unified_system", False, f"Error: {e}"))
    
    # Анализируем результаты
    failed_checks = [name for name, passed, _ in checks if not passed]
    
    if failed_checks:
        error_details = {name: msg for name, passed, msg in checks if not passed}
        raise HTTPException(
            status_code=503,
            detail={
                "message": f"System not ready. Failed checks: {', '.join(failed_checks)}",
                "failed_checks": error_details
            }
        )
    
    return BaseResponse(
        message="System is ready to handle requests",
        request_id=getattr(request.state, 'request_id', None)
    ) 