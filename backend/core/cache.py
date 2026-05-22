import json
import functools
import time
import logging
from typing import Any, Optional, Callable
from backend.config import get_settings
import cachetools

# ── Redis Fallback Logic ───────────────────────────────────────────────────
# Bounded LRU cache with 10,000 item limit to prevent unbounded memory growth.
# Entries are stored with explicit expiry timestamps to support variable TTLs.
_IN_MEMORY_CACHE = cachetools.LRUCache(maxsize=10_000)

_pool = None
REDIS_AVAILABLE = False

try:
    import redis.asyncio as redis
    settings = get_settings()
    _pool = redis.ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )
    REDIS_AVAILABLE = True
except (ImportError, Exception) as e:
    REDIS_AVAILABLE = False
    logging.warning(f"Redis not available, falling back to In-Memory LRU: {e}")

def get_redis_client():
    if not REDIS_AVAILABLE:
        return None
    return redis.Redis(connection_pool=_pool)

class CacheManager:
    @staticmethod
    async def get(key: str) -> Optional[Any]:
        if REDIS_AVAILABLE:
            try:
                async with get_redis_client() as r:
                    data = await r.get(key)
                    return json.loads(data) if data else None
            except Exception:
                pass

        # In-memory fallback: check expiry timestamp
        item = _IN_MEMORY_CACHE.get(key)
        if item and item['expiry'] > time.time():
            return item['value']
        # Expired entry; clean it up
        if item:
            _IN_MEMORY_CACHE.pop(key, None)
        return None

    @staticmethod
    async def set(key: str, value: Any, ttl: int = 3600):
        if REDIS_AVAILABLE:
            try:
                async with get_redis_client() as r:
                    await r.set(key, json.dumps(value), ex=ttl)
                    return
            except Exception:
                pass

        # In-memory fallback: store with explicit expiry timestamp
        # LRUCache bounded at 10,000 items
        _IN_MEMORY_CACHE[key] = {
            'value': value,
            'expiry': time.time() + ttl
        }

    @staticmethod
    async def delete(key: str):
        if REDIS_AVAILABLE:
            try:
                async with get_redis_client() as r:
                    await r.delete(key)
                    return
            except Exception:
                pass
        _IN_MEMORY_CACHE.pop(key, None)

# ── Cache Decorator for FastAPI Routes ──────────────────────────────────────
def cache_response(ttl: int = 3600, key_prefix: str = "cache"):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
            cached_val = await CacheManager.get(cache_key)
            if cached_val is not None:
                return cached_val
            
            result = await func(*args, **kwargs)
            await CacheManager.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator
