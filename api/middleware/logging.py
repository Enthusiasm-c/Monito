"""
=============================================================================
MONITO API REQUEST LOGGING MIDDLEWARE
=============================================================================
Версия: 3.0
Цель: Middleware для логирования HTTP запросов и ответов
=============================================================================
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logger import get_logger

logger = get_logger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования всех HTTP запросов и ответов
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Обработка HTTP запроса с логированием
        
        Args:
            request: HTTP запрос
            call_next: Следующий middleware/handler
            
        Returns:
            HTTP ответ
        """
        # Генерируем уникальный ID запроса
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Логируем входящий запрос
        start_time = time.time()
        
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        logger.info(
            f"🔵 [{request_id}] {request.method} {request.url.path} - "
            f"IP: {client_ip}, Agent: {user_agent[:50]}..."
        )
        
        # Логируем параметры запроса (только для GET)
        if request.method == "GET" and request.query_params:
            logger.debug(f"📋 [{request_id}] Query params: {dict(request.query_params)}")
        
        try:
            # Выполняем запрос
            response = await call_next(request)
            
            # Рассчитываем время обработки
            process_time = time.time() - start_time
            
            # Логируем ответ
            status_emoji = self._get_status_emoji(response.status_code)
            logger.info(
                f"{status_emoji} [{request_id}] {response.status_code} - "
                f"{process_time:.3f}s"
            )
            
            # Добавляем заголовки ответа
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Логируем ошибки
            process_time = time.time() - start_time
            logger.error(
                f"❌ [{request_id}] Error processing request: {e} - "
                f"{process_time:.3f}s"
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Получение IP адреса клиента"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _get_status_emoji(self, status_code: int) -> str:
        """Получение эмодзи для статус кода"""
        if 200 <= status_code < 300:
            return "✅"  # Успех
        elif 300 <= status_code < 400:
            return "🔄"  # Перенаправление
        elif 400 <= status_code < 500:
            return "⚠️"   # Клиентская ошибка
        elif 500 <= status_code < 600:
            return "❌"  # Серверная ошибка
        else:
            return "❓"  # Неизвестный статус 