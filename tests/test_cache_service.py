"""Tests for cache service."""

import pytest
import asyncio
import time
from app.services.cache_service import LRUCache, AsyncCache, cached


class TestLRUCache:
    def test_set_and_get(self):
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent_key(self):
        cache = LRUCache(max_size=10)
        assert cache.get("nonexistent") is None

    def test_delete(self):
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("key1") is False

    def test_clear(self):
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_lru_eviction(self):
        cache = LRUCache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_lru_order_update(self):
        cache = LRUCache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.get("key1")
        cache.set("key4", "value4")
        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None

    def test_stats(self):
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key1")
        cache.get("key2")
        stats = cache.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 66.67

    def test_ttl_expiration(self):
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1", ttl=1)
        time.sleep(1.1)
        assert cache.get("key1") is None


class TestAsyncCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = AsyncCache(max_size=10)
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        cache = AsyncCache(max_size=10)
        assert await cache.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_delete(self):
        cache = AsyncCache(max_size=10)
        await cache.set("key1", "value1")
        assert await cache.delete("key1") is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_clear(self):
        cache = AsyncCache(max_size=10)
        await cache.set("key1", "value1")
        await cache.clear()
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_max_size_eviction(self):
        cache = AsyncCache(max_size=3)
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        await cache.set("key4", "value4")
        assert await cache.get("key1") is None
        assert await cache.get("key2") == "value2"

    @pytest.mark.asyncio
    async def test_stats(self):
        cache = AsyncCache(max_size=10)
        await cache.set("key1", "value1")
        await cache.get("key1")
        await cache.get("key2")
        stats = await cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        cache = AsyncCache(max_size=10, default_ttl=1)
        await cache.set("key1", "value1", ttl=1)
        await asyncio.sleep(1.1)
        result = await cache.get("key1")
        assert result is None


class TestCachedDecorator:
    @pytest.mark.asyncio
    async def test_cached_function(self):
        cache = AsyncCache(max_size=10)
        call_count = 0

        @cached(cache, key_prefix="test", ttl=60)
        async def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await expensive_function(5)
        result2 = await expensive_function(5)
        result3 = await expensive_function(10)

        assert result1 == 10
        assert result2 == 10
        assert result3 == 20
        assert call_count == 2
