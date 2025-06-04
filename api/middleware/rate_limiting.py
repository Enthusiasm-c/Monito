"""
=============================================================================
MONITO API RATE LIMITING MIDDLEWARE
=============================================================================
Версия: 3.0
Цель: Middleware для ограничения скорости запросов к API
=============================================================================
"""

import time
from collections import defaultdict, deque
from typing import Callable, Dict, Deque

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logger import get_logger

logger = get_logger(__name__)

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для ограничения скорости запросов (Rate Limiting)
    """
    
    def __init__(self, app, requests_per_minute: int = 100):
        """
        Инициализация middleware ограничения скорости
        
        Args:
            app: FastAPI приложение
            requests_per_minute: Максимальное количество запросов в минуту
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # Окно в секундах (1 минута)
        
        # Хранилище для отслеживания запросов по IP
        self.request_history: Dict[str, Deque[float]] = defaultdict(deque)
        
        # Пути, которые не ограничиваются
        self.excluded_paths = {
            "/health",
            "/health/",
            "/",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
        
        logger.info(f"Rate limiting middleware initialized: {requests_per_minute} req/min")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Обработка ограничения скорости для HTTP запроса
        
        Args:
            request: HTTP запрос
            call_next: Следующий middleware/handler
            
        Returns:
            HTTP ответ
            
        Raises:
            HTTPException: При превышении лимита запросов
        """
        # Проверяем, исключен ли путь из ограничений
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Получаем идентификатор клиента
        client_id = self._get_client_identifier(request)
        current_time = time.time()
        
        # Очищаем старые запросы из истории
        self._cleanup_old_requests(client_id, current_time)
        
        # Проверяем лимит
        request_count = len(self.request_history[client_id])
        
        if request_count >= self.requests_per_minute:
            # Лимит превышен
            oldest_request = self.request_history[client_id][0]
            retry_after = int(oldest_request + self.window_size - current_time) + 1
            
            logger.warning(
                f"Rate limit exceeded for {client_id}: {request_count}/{self.requests_per_minute} req/min"
            )
            
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(oldest_request + self.window_size))
                }
            )
        
        # Добавляем текущий запрос в историю
        self.request_history[client_id].append(current_time)
        
        # Выполняем запрос
        response = await call_next(request)
        
        # Добавляем заголовки с информацией о лимитах
        remaining_requests = max(0, self.requests_per_minute - len(self.request_history[client_id]))
        reset_time = int(current_time + self.window_size)
        
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining_requests)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        # Логируем использование лимита
        if remaining_requests <= 10:
            logger.warning(
                f"Rate limit warning for {client_id}: {remaining_requests} requests remaining"
            )
        
        return response
    
    def _get_client_identifier(self, request: Request) -> str:
        """
        Получение идентификатора клиента для rate limiting
        
        Args:
            request: HTTP запрос
            
        Returns:
            Идентификатор клиента
        """
        # Сначала пытаемся получить IP из заголовков прокси
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Используем IP клиента
        if request.client:
            return request.client.host
        
        # Fallback на User-Agent (менее надежно)
        user_agent = request.headers.get("user-agent", "unknown")
        return f"ua_{hash(user_agent) % 10000}"
    
    def _cleanup_old_requests(self, client_id: str, current_time: float):
        """
        Очистка старых запросов из истории
        
        Args:
            client_id: Идентификатор клиента
            current_time: Текущее время
        """
        cutoff_time = current_time - self.window_size
        
        # Удаляем запросы старше окна времени
        while (self.request_history[client_id] and 
               self.request_history[client_id][0] < cutoff_time):
            self.request_history[client_id].popleft()
        
        # Очищаем пустые записи
        if not self.request_history[client_id]:
            del self.request_history[client_id]
    
    def _is_excluded_path(self, path: str) -> bool:
        """
        Проверка, исключен ли путь из rate limiting
        
        Args:
            path: Путь запроса
            
        Returns:
            True если путь исключен
        """
        # Точное совпадение
        if path in self.excluded_paths:
            return True
        
        # Проверяем пути документации
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True
        
        return False
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Получение статистики rate limiting
        
        Returns:
            Статистика использования
        """
        current_time = time.time()
        active_clients = 0
        total_requests = 0
        
        for client_id in list(self.request_history.keys()):
            self._cleanup_old_requests(client_id, current_time)
            if self.request_history.get(client_id):
                active_clients += 1
                total_requests += len(self.request_history[client_id])
        
        return {
            "active_clients": active_clients,
            "total_requests_in_window": total_requests,
            "requests_per_minute_limit": self.requests_per_minute,
            "window_size_seconds": self.window_size,
            "excluded_paths": list(self.excluded_paths)
        } 