import logging
import os
from typing import Optional

import redis
from fastapi import Header, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.settings import settings

logger = logging.getLogger(__name__)

# Отключаем rate limiting для тестов
DISABLE_RATE_LIMITING = os.getenv("DISABLE_RATE_LIMITING", "false").lower() == "true"

# Лимиты
DEFAULT_RATE_LIMIT = "10/minute"
API_KEY_RATE_LIMIT = "100/minute"  # Повышенный лимит для API ключей


def get_api_key_from_header(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """Получить API ключ из заголовка."""
    return x_api_key


def get_rate_limit_key(request: Request) -> str:
    """Получить ключ для rate limiting."""
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"api_key:{api_key}"
    return f"ip:{get_remote_address(request)}"


def get_redis_client():
    """Получить Redis клиент для rate limiting (singleton with lazy init)."""
    if not hasattr(get_redis_client, '_client'):
        get_redis_client._client = None
        try:
            get_redis_client._client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            get_redis_client._client.ping()
            logger.info("Rate limiter: Redis connection established")
        except redis.RedisError as e:
            logger.warning(f"Redis connection failed, falling back to memory: {e}")
            get_redis_client._client = None
    return get_redis_client._client


if DISABLE_RATE_LIMITING:
    # Пустой limiter для тестов
    class DummyLimiter:
        def __call__(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

        def limit(self, limit):
            def decorator(func):
                return func
            return decorator
    limiter = DummyLimiter()
    rate_limiter_middleware = None
else:
    # Пробуем использовать Redis для персистентности rate limiting
    redis_client = get_redis_client()
    
    if redis_client:
        logger.info("Rate limiting: Using Redis backend")
        limiter = Limiter(
            key_func=get_rate_limit_key,
            storage_uri=settings.redis_url,
            default_limits=[DEFAULT_RATE_LIMIT],
        )
    else:
        # Fallback на in-memory
        logger.warning("Rate limiting: Using in-memory backend (Redis unavailable)")
        limiter = Limiter(
            key_func=get_rate_limit_key,
            default_limits=[DEFAULT_RATE_LIMIT],
        )
    
    # Создаём middleware для автоматического применения лимитов
    rate_limiter_middleware = SlowAPIMiddleware(limiter)


async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded
) -> JSONResponse:
    """Обработчик превышения лимита запросов."""
    retry_after: Optional[str] = None
    if hasattr(exc, 'detail') and hasattr(exc.detail, 'headers'):
        retry_after = exc.detail.headers.get("Retry-After")

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "error": "Too Many Requests",
            "message": "Превышен лимит запросов. Пожалуйста, подождите.",
            "retry_after": retry_after or "60",
        },
    )
