import pytest
import asyncio
import time
from backend.core.cache import CacheManager


@pytest.mark.asyncio
async def test_cache_bounded_memory():
    """Test that cache respects 10,000 item limit and does not grow unbounded."""
    # Insert 10,001 distinct keys to exceed the limit
    for i in range(10_001):
        key = f"test_key_{i}"
        value = f"test_value_{i}"
        await CacheManager.set(key, value, ttl=3600)

    # Access the internal cache to check size
    from backend.core.cache import _IN_MEMORY_CACHE

    # TTLCache should not exceed maxsize
    cache_size = len(_IN_MEMORY_CACHE)
    assert cache_size <= 10_000, f"Cache size {cache_size} exceeds limit of 10,000"


@pytest.mark.asyncio
async def test_cache_get_set_basic():
    """Test basic get/set functionality."""
    key = "test_key_basic"
    value = {"name": "test", "data": [1, 2, 3]}

    await CacheManager.set(key, value, ttl=3600)
    retrieved = await CacheManager.get(key)

    assert retrieved == value


@pytest.mark.asyncio
async def test_cache_ttl_expiry():
    """Test that cached items expire after TTL."""
    key = "test_key_ttl"
    value = "test_value"

    # Set with short TTL
    await CacheManager.set(key, value, ttl=1)

    # Should exist immediately
    retrieved = await CacheManager.get(key)
    assert retrieved == value

    # Wait for expiry
    await asyncio.sleep(1.5)

    # Should be expired now
    retrieved = await CacheManager.get(key)
    assert retrieved is None


@pytest.mark.asyncio
async def test_cache_delete():
    """Test delete functionality."""
    key = "test_key_delete"
    value = "test_value"

    await CacheManager.set(key, value, ttl=3600)
    retrieved = await CacheManager.get(key)
    assert retrieved == value

    await CacheManager.delete(key)
    retrieved = await CacheManager.get(key)
    assert retrieved is None


@pytest.mark.asyncio
async def test_cache_missing_key():
    """Test that missing keys return None."""
    retrieved = await CacheManager.get("nonexistent_key_12345")
    assert retrieved is None
