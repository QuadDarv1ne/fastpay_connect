"""Token blacklist management using Redis."""

import logging
from typing import Optional
from datetime import datetime, timezone, timedelta

import redis

from app.settings import settings

logger = logging.getLogger(__name__)

# TTL по умолчанию — макс. время жизни access токена + буфер
DEFAULT_TTL_SECONDS = 3600  # 1 hour


def _get_redis_client() -> Optional[redis.Redis]:
    """Получить Redis клиент для blacklist."""
    try:
        client = redis.from_url(settings.redis_url)
        client.ping()
        return client
    except redis.RedisError as e:
        logger.warning(f"Redis connection failed, token blacklist disabled: {e}")
        return None


def blacklist_token(token: str, ttl: Optional[int] = None) -> bool:
    """Добавить токен в blacklist."""
    client = _get_redis_client()
    if not client:
        logger.error("Cannot blacklist token: Redis unavailable")
        return False

    key = f"token:blacklist:{token}"
    try:
        client.setex(key, ttl or DEFAULT_TTL_SECONDS, "1")
        logger.info(f"Token blacklisted (ttl={ttl or DEFAULT_TTL_SECONDS}s)")
        return True
    except redis.RedisError as e:
        logger.error(f"Failed to blacklist token: {e}")
        return False


def is_token_blacklisted(token: str) -> bool:
    """Проверить, находится ли токен в blacklist."""
    client = _get_redis_client()
    if not client:
        return False

    key = f"token:blacklist:{token}"
    try:
        return client.exists(key) > 0
    except redis.RedisError as e:
        logger.error(f"Failed to check token blacklist: {e}")
        return False


async def check_token_not_blacklisted(token: str) -> bool:
    """FastAPI dependency: raises if token is blacklisted."""
    if is_token_blacklisted(token):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True
