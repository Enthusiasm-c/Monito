"""
=============================================================================
MONITO API CONFIGURATION
=============================================================================
Версия: 3.0
Цель: Конфигурация для FastAPI приложения
=============================================================================
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator

class APIConfig(BaseSettings):
    """Конфигурация API"""
    
    # Основные настройки
    app_name: str = "Monito Unified API"
    app_version: str = "3.0.0"
    debug: bool = False
    
    # База данных
    database_url: str = "sqlite:///./monito_unified.db"
    
    # API настройки
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: Optional[str] = None
    
    # Аутентификация и безопасность
    enable_auth: bool = False
    enable_rate_limiting: bool = True
    rate_limit_per_minute: int = 100
    
    # CORS
    cors_origins: List[str] = ["*"]
    
    # Документация
    enable_docs: bool = True
    docs_username: Optional[str] = None
    docs_password: Optional[str] = None
    
    # Логирование
    log_level: str = "INFO"
    log_requests: bool = True
    
    # Кеширование
    enable_cache: bool = True
    cache_ttl_seconds: int = 300
    
    # Внешние сервисы
    telegram_bot_token: Optional[str] = None
    webhook_url: Optional[str] = None
    
    # Unified система
    unified_batch_size: int = 100
    matching_confidence_threshold: float = 0.8
    price_comparison_enabled: bool = True
    
    @validator('cors_origins', pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and v:
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_prefix = "MONITO_"
        case_sensitive = False

# Кеш для конфигурации
_config_cache: Optional[APIConfig] = None

def get_api_config() -> APIConfig:
    """
    Получение конфигурации API с кешированием
    
    Returns:
        Конфигурация API
    """
    global _config_cache
    
    if _config_cache is None:
        _config_cache = APIConfig()
    
    return _config_cache

def reload_config() -> APIConfig:
    """
    Принудительная перезагрузка конфигурации
    
    Returns:
        Обновленная конфигурация
    """
    global _config_cache
    _config_cache = None
    return get_api_config() 