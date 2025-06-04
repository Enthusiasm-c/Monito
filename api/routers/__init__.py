"""
=============================================================================
MONITO API ROUTERS PACKAGE
=============================================================================
FastAPI роутеры для различных эндпоинтов unified системы
=============================================================================
"""

from .health import router as health_router
from .catalog import router as catalog_router
from .products import router as products_router
from .suppliers import router as suppliers_router
from .prices import router as prices_router
from .analytics import router as analytics_router
from .migration import router as migration_router
from .telegram import router as telegram_router

__all__ = [
    "health_router",
    "catalog_router", 
    "products_router",
    "suppliers_router",
    "prices_router",
    "analytics_router",
    "migration_router",
    "telegram_router"
] 