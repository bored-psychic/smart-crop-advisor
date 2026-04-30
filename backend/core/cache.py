import json
import functools
import time
import logging
from typing import Any, Optional, Callable
from core.config import settings

# ── Redis Fallback Logic ───────────────────────────────────────────────────
_IN_MEMORY_CACHE = {}

try:
    import redis.asyncio as redis
    _pool = redis.ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )
    REDIS_AVAILABLE = True
except (ImportError, Exception):
    REDIS_AVAILABLE = False
    logging.warning("Redis not found or connection failed. Falling back to In-Memory LRU.")

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
        
        # In-memory fallback
        item = _IN_MEMORY_CACHE.get(key)
        if item and item['expiry'] > time.time():
            return item['value']
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
        
        # In-memory fallback
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
