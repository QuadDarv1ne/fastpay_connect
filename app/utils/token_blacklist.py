"""Token blacklist management using Redis."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import redis

from app.settings import settings

logger = logging.getLogger(__name__)

# TTL по умолчанию — макс. время жизни access токена + буфер
DEFAULT_TTL_SECONDS = 3600  # 1 hour

# Singleton Redis connection for token blacklist
_redis_client: Optional[redis.Redis] = None


def _get_redis_client() -> Optional[redis.Redis]:
    """Получить Redis клиент для blacklist (singleton with lazy init)."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            _redis_client.ping()
            logger.info("Token blacklist: Redis connection established")
        except redis.RedisError as e:
            logger.warning(f"Redis connection failed, token blacklist disabled: {e}")
            return None
    return _redis_client


def _hash_token(token: str) -> str:
    """Hash token for secure storage in Redis."""
    return hashlib.sha256(token.encode()).hexdigest()


def blacklist_token(token: str, ttl: Optional[int] = None) -> bool:
    """Добавить токен в blacklist."""
    client = _get_redis_client()
    if not client:
        logger.error("Cannot blacklist token: Redis unavailable")
        return False

    key = f"token:blacklist:{_hash_token(token)}"
    try:
        client.setex(key, ttl or DEFAULT_TTL_SECONDS, "1")
        logger.info(f"Token blacklisted (ttl={ttl or DEFAULT_TTL_SECONDS}s)")
        return True
    except redis.RedisError as e:
        logger.error(f"Failed to blacklist token: {e}")
        return False


def is_token_blacklisted(token: str) -> bool:
    """Проверить, находится ли токен в blacklist.

    Fails open: when Redis is unavailable, the token is allowed through.
    This avoids locking out all users during Redis outages. The blacklist
    is a best-effort safety net; real security comes from short access-token
    TTLs.
    """
    client = _get_redis_client()
    if not client:
        logger.warning(
            "Redis unavailable for token blacklist check; "
            "allowing token through (fail-open)"
        )
        return False

    key = f"token:blacklist:{_hash_token(token)}"
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
