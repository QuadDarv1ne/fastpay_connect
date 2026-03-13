"""Кэширование для часто используемых данных."""

import asyncio
from typing import Any, Dict, Optional, Callable, TypeVar
from functools import wraps
import time
from collections import OrderedDict

T = TypeVar('T')


class LRUCache:
    """LRU кэш для хранения данных."""

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша."""
        if key in self._cache:
            entry = self._cache[key]
            if entry['expires'] and time.time() > entry['expires']:
                del self._cache[key]
                self._misses += 1
                return None
            self._cache.move_to_end(key)
            self._hits += 1
            return entry['value']
        self._misses += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Установить значение в кэш."""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = {
            'value': value,
            'expires': time.time() + ttl if ttl else None
        }
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """Удалить значение из кэша."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Очистить кэш."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> Dict[str, int]:
        """Получить статистику кэша."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(hit_rate, 2)
        }

    def _cleanup_expired(self) -> None:
        """Очистить просроченные записи."""
        now = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if v['expires'] and now > v['expires']
        ]
        for key in expired_keys:
            del self._cache[key]


class AsyncCache:
    """Асинхронный кэш с TTL поддержкой."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry['expires'] and time.time() > entry['expires']:
                    del self._cache[key]
                    self._misses += 1
                    return None
                self._hits += 1
                return entry['value']
            self._misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Установить значение в кэш."""
        async with self._lock:
            if key in self._cache:
                self._cache[key] = {
                    'value': value,
                    'expires': time.time() + (ttl or self._default_ttl)
                }
            else:
                if len(self._cache) >= self._max_size:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                self._cache[key] = {
                    'value': value,
                    'expires': time.time() + (ttl or self._default_ttl)
                }

    async def delete(self, key: str) -> bool:
        """Удалить значение из кэша."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Очистить кэш."""
        async with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша."""
        async with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 2)
            }


def cached(cache: AsyncCache, key_prefix: str = "", ttl: Optional[int] = None):
    """Декоратор для кэширования результатов асинхронных функций."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


payment_cache = AsyncCache(max_size=500, default_ttl=300)
statistics_cache = AsyncCache(max_size=100, default_ttl=60)
