"""
Redis client for pub/sub and caching.
"""
import redis
import redis.asyncio as aioredis
from app.core.config import settings
from typing import Optional

_redis_client: Optional[redis.Redis] = None
_async_redis_client: Optional[aioredis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get synchronous Redis client singleton (for Celery)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            encoding="utf-8"
        )
    return _redis_client


async def get_async_redis_client() -> aioredis.Redis:
    """Get async Redis client singleton (for WebSocket pubsub)."""
    global _async_redis_client
    if _async_redis_client is None:
        _async_redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            encoding="utf-8"
        )
    return _async_redis_client


def close_redis_client():
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None


async def close_async_redis_client():
    """Close async Redis connection."""
    global _async_redis_client
    if _async_redis_client is not None:
        await _async_redis_client.aclose()
        _async_redis_client = None
