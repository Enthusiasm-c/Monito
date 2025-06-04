"""
=============================================================================
MONITO REST API MAIN APPLICATION
=============================================================================
Версия: 3.0
Цель: FastAPI приложение для unified системы управления ценами
=============================================================================
"""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from modules.adapters.legacy_integration_adapter import LegacyIntegrationAdapter
from modules.compatibility.compatibility_manager import CompatibilityManager
from utils.logger import get_logger

from .routers import (
    catalog_router,
    products_router,
    suppliers_router,
    prices_router,
    analytics_router,
    migration_router,
    health_router,
    telegram,
    unified_catalog,
    websocket,
    reports
)
from .middleware import (
    RequestLoggingMiddleware,
    AuthenticationMiddleware,
    RateLimitingMiddleware
)
from .config import get_api_config

logger = get_logger(__name__)

# Глобальные переменные для unified системы
integration_adapter: LegacyIntegrationAdapter = None
compatibility_manager: CompatibilityManager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager для FastAPI приложения"""
    # Startup
    logger.info("🚀 Starting Monito API...")
    
    global integration_adapter, compatibility_manager
    
    try:
        # Инициализируем unified систему
        config = get_api_config()
        database_url = config.database_url
        
        integration_adapter = LegacyIntegrationAdapter(database_url)
        compatibility_manager = CompatibilityManager(integration_adapter)
        
        # Сохраняем в app state для доступа из роутеров
        app.state.integration_adapter = integration_adapter
        app.state.compatibility_manager = compatibility_manager
        
        logger.info("✅ Unified system initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize unified system: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Monito API...")
    
    # Cleanup if needed
    # integration_adapter cleanup would go here
    
    logger.info("✅ Shutdown complete")

def create_app() -> FastAPI:
    """
    Создание и настройка FastAPI приложения
    
    Returns:
        Настроенное FastAPI приложение
    """
    
    # Получаем конфигурацию
    config = get_api_config()
    
    # Создаем приложение
    app = FastAPI(
        title="Monito Unified Price Management API",
        description="""
        🏝️ **Monito** - Unified система управления ценами поставщиков острова Бали
        
        ## Возможности
        
        * 🔍 **Unified Catalog** - Единый каталог товаров со сравнением цен
        * 💰 **Price Analysis** - Анализ цен и рекомендации по закупкам
        * 🏪 **Supplier Management** - Управление поставщиками и их производительностью
        * 📊 **Analytics** - Аналитика рынка и трендов цен
        * 🔄 **Migration Tools** - Инструменты миграции из legacy системы
        
        ## Технологии
        
        - **FastAPI** для высокопроизводительного API
        - **SQLAlchemy** для работы с unified базой данных
        - **AI-powered** сопоставление и анализ товаров
        - **Real-time** обновление цен и статистики
        """,
        version="3.0.0",
        lifespan=lifespan,
        docs_url="/docs" if config.enable_docs else None,
        redoc_url="/redoc" if config.enable_docs else None,
        openapi_url="/openapi.json" if config.enable_docs else None
    )
    
    # Настраиваем CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Добавляем Gzip сжатие
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Добавляем кастомные middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    if config.enable_auth:
        app.add_middleware(AuthenticationMiddleware, api_key=config.api_key)
    
    if config.enable_rate_limiting:
        app.add_middleware(RateLimitingMiddleware, 
                          requests_per_minute=config.rate_limit_per_minute)
    
    # Подключаем роутеры
    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(catalog_router, prefix="/api/v1/catalog", tags=["Unified Catalog"])
    app.include_router(products_router, prefix="/api/v1/products", tags=["Products"])
    app.include_router(suppliers_router, prefix="/api/v1/suppliers", tags=["Suppliers"])
    app.include_router(prices_router, prefix="/api/v1/prices", tags=["Prices"])
    app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
    app.include_router(migration_router, prefix="/api/v1/migration", tags=["Migration"])
    app.include_router(telegram.router, prefix="/api/v1/telegram", tags=["Telegram"])
    app.include_router(websocket.router, tags=["WebSocket"])
    app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
    
    # Unified роутеры (уже с префиксами)
    app.include_router(unified_catalog.router)
    
    # Обработчики ошибок
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, 'request_id', 'unknown')
            }
        )
    
    # Кастомная OpenAPI схема
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="Monito Unified API",
            version="3.0.0",
            description=app.description,
            routes=app.routes,
        )
        
        # Добавляем кастомные теги и схемы
        openapi_schema["info"]["x-logo"] = {
            "url": "https://via.placeholder.com/200x50/4A90E2/FFFFFF?text=MONITO"
        }
        
        # Группируем эндпоинты по функциональности
        openapi_schema["tags"] = [
            {
                "name": "Health",
                "description": "Проверка состояния API и системы"
            },
            {
                "name": "Unified Catalog",
                "description": "🏪 Единый каталог товаров с лучшими ценами"
            },
            {
                "name": "Products",
                "description": "📦 Управление товарами и их сопоставление"
            },
            {
                "name": "Suppliers",
                "description": "🏬 Управление поставщиками и их производительностью"
            },
            {
                "name": "Prices",
                "description": "💰 Управление ценами и их анализ"
            },
            {
                "name": "Analytics", 
                "description": "📊 Аналитика и статистика системы"
            },
            {
                "name": "Migration",
                "description": "🔄 Инструменты миграции из legacy системы"
            },
            {
                "name": "Telegram",
                "description": "🤖 Управление ботом в Telegram"
            },
            {
                "name": "WebSocket",
                "description": "🔄 WebSocket для реального времени"
            },
            {
                "name": "Reports",
                "description": "📊 Отчеты и анализ данных"
            }
        ]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    # Кастомная документация
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Interactive API Documentation",
            swagger_favicon_url="https://via.placeholder.com/32x32/4A90E2/FFFFFF?text=M",
            swagger_ui_parameters={
                "defaultModelsExpandDepth": -1,
                "docExpansion": "list",
                "filter": True,
                "showRequestHeaders": True
            }
        )
    
    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "message": "🏝️ Monito Unified Price Management API",
            "version": "3.0.0",
            "status": "operational",
            "docs": "/docs",
            "health": "/health"
        }
    
    logger.info(f"FastAPI application created with config: {config.dict()}")
    
    return app

# Создаем экземпляр приложения
app = create_app() 