#!/usr/bin/env python3
"""
=============================================================================
MONITO API QUICK TEST
=============================================================================
Версия: 3.0  
Цель: Быстрый тест работоспособности FastAPI сервера
=============================================================================
"""

import sys
import os
from pathlib import Path

# Добавляем путь к проекту
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_api_import():
    """Тест импорта основных компонентов API"""
    
    print("🧪 Testing API imports...")
    
    try:
        # Тестируем импорт основного приложения
        from api.main import app
        print("✅ FastAPI app imported successfully")
        
        # Тестируем импорт конфигурации
        from api.config import get_api_config
        config = get_api_config()
        print(f"✅ API config loaded: version {config.app_version}")
        
        # Тестируем импорт роутеров
        from api.routers.health import router as health_router
        from api.routers.catalog import router as catalog_router
        print("✅ API routers imported successfully")
        
        # Тестируем импорт схем
        from api.schemas.base import BaseResponse, HealthCheckResponse
        print("✅ API schemas imported successfully")
        
        # Тестируем middleware
        from api.middleware.logging import RequestLoggingMiddleware
        from api.middleware.auth import AuthenticationMiddleware  
        from api.middleware.rate_limiting import RateLimitingMiddleware
        print("✅ API middleware imported successfully")
        
        print(f"\n🎉 All API components imported successfully!")
        print(f"📄 API Title: {app.title}")
        print(f"📋 API Version: {app.version}")
        print(f"📝 API Description length: {len(app.description)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_unified_system_integration():
    """Тест интеграции с unified системой"""
    
    print("\n🧪 Testing unified system integration...")
    
    try:
        # Тестируем импорт unified компонентов
        from modules.adapters.legacy_integration_adapter import LegacyIntegrationAdapter
        print("✅ LegacyIntegrationAdapter imported")
        
        from modules.compatibility.compatibility_manager import CompatibilityManager
        print("✅ CompatibilityManager imported")
        
        from models.unified_database import MasterProduct, SupplierPrice
        print("✅ Unified database models imported")
        
        print("🎉 Unified system integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Unified system integration failed: {e}")
        return False

def test_api_creation():
    """Тест создания FastAPI приложения"""
    
    print("\n🧪 Testing API application creation...")
    
    try:
        from api.main import create_app
        
        # Создаем приложение
        app = create_app()
        
        print(f"✅ FastAPI app created: {app.title}")
        
        # Проверяем основные атрибуты
        assert app.version == "3.0.0"
        assert "Monito" in app.title
        assert app.openapi_url == "/openapi.json"
        
        # Проверяем количество роутеров
        route_count = len(app.routes)
        print(f"✅ API has {route_count} routes configured")
        
        print("🎉 API application creation test passed!")
        return True
        
    except Exception as e:
        print(f"❌ API creation failed: {e}")
        return False

def main():
    """Запуск всех тестов"""
    
    print("🏝️ " + "="*60)
    print("🏝️  MONITO API QUICK TEST SUITE")
    print("🏝️ " + "="*60)
    
    tests = [
        test_api_import,
        test_unified_system_integration,
        test_api_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "="*60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API is ready to start.")
        print("🚀 Run: python api_server.py")
        return 0
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main()) 