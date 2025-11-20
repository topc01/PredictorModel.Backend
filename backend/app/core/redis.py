"""
Redis client for pub/sub and caching.
"""
import redis
from app.core.config import settings
from typing import Optional

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            encoding="utf-8"
        )
    return _redis_client


def close_redis_client():
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None
