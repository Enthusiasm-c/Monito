"""
=============================================================================
MONITO API AUTHENTICATION MIDDLEWARE
=============================================================================
Версия: 3.0
Цель: Middleware для аутентификации API через токены
=============================================================================
"""

from typing import Callable, Optional

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logger import get_logger

logger = get_logger(__name__)

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware для аутентификации через API ключи
    """
    
    def __init__(self, app, api_key: Optional[str] = None):
        """
        Инициализация middleware аутентификации
        
        Args:
            app: FastAPI приложение
            api_key: API ключ для аутентификации
        """
        super().__init__(app)
        self.api_key = api_key
        
        # Пути, которые не требуют аутентификации
        self.public_paths = {
            "/",
            "/health",
            "/health/",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
        
        logger.info(f"Authentication middleware initialized with API key: {'***' if api_key else 'None'}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Обработка аутентификации для HTTP запроса
        
        Args:
            request: HTTP запрос
            call_next: Следующий middleware/handler
            
        Returns:
            HTTP ответ
            
        Raises:
            HTTPException: При неудачной аутентификации
        """
        # Проверяем, требует ли путь аутентификации
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Если API ключ не настроен, пропускаем аутентификацию
        if not self.api_key:
            return await call_next(request)
        
        # Извлекаем токен из заголовка
        auth_header = request.headers.get("Authorization")
        api_key = request.headers.get("X-API-Key")
        
        provided_key = None
        
        # Проверяем Authorization заголовок (Bearer токен)
        if auth_header and auth_header.startswith("Bearer "):
            provided_key = auth_header[7:]  # Убираем "Bearer "
        
        # Проверяем X-API-Key заголовок
        elif api_key:
            provided_key = api_key
        
        # Проверяем API ключ в query параметрах (менее безопасно)
        elif "api_key" in request.query_params:
            provided_key = request.query_params["api_key"]
            logger.warning(f"API key provided in query params from {self._get_client_ip(request)}")
        
        # Валидируем предоставленный ключ
        if not provided_key:
            logger.warning(f"Missing API key from {self._get_client_ip(request)}")
            raise HTTPException(
                status_code=401,
                detail="API key required. Provide it via 'Authorization: Bearer <key>' or 'X-API-Key' header",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if provided_key != self.api_key:
            logger.warning(f"Invalid API key from {self._get_client_ip(request)}")
            raise HTTPException(
                status_code=401,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Аутентификация успешна
        request.state.authenticated = True
        logger.debug(f"Successful authentication from {self._get_client_ip(request)}")
        
        return await call_next(request)
    
    def _is_public_path(self, path: str) -> bool:
        """Проверка, является ли путь публичным"""
        # Точное совпадение
        if path in self.public_paths:
            return True
        
        # Проверяем пути документации с параметрами
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True
        
        return False
    
    def _get_client_ip(self, request: Request) -> str:
        """Получение IP адреса клиента"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown" 