#!/usr/bin/env python3
"""
=============================================================================
MONITO API SERVER
=============================================================================
Версия: 3.0
Цель: Запуск FastAPI сервера для unified системы управления ценами Бали
=============================================================================
"""

import os
import sys
import uvicorn
from pathlib import Path

# Добавляем текущую директорию в PYTHONPATH
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from api.main import app
from api.config import get_api_config

def main():
    """Запуск API сервера"""
    
    config = get_api_config()
    
    print("🏝️ " + "="*60)
    print("🏝️  MONITO UNIFIED PRICE MANAGEMENT API")
    print("🏝️ " + "="*60)
    print(f"🏝️  Version: {config.app_version}")
    print(f"🏝️  Environment: {'Development' if config.debug else 'Production'}")
    print(f"🏝️  Host: {config.api_host}:{config.api_port}")
    print(f"🏝️  Database: {config.database_url}")
    print(f"🏝️  Docs: http://{config.api_host}:{config.api_port}/docs")
    print("🏝️ " + "="*60)
    
    # Настройки uvicorn
    uvicorn_config = {
        "app": "api.main:app",
        "host": config.api_host,
        "port": config.api_port,
        "reload": config.debug,
        "log_level": config.log_level.lower(),
        "access_log": config.log_requests
    }
    
    # Запускаем сервер
    uvicorn.run(**uvicorn_config)

if __name__ == "__main__":
    main() 