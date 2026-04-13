"""Async Redis helpers (FastAPI). Broker for Celery uses same Redis; cache uses REDIS_URL (often DB /1)."""

from typing import Optional

import redis.asyncio as redis

from async_database import settings

_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


async def cache_get(key: str) -> Optional[str]:
    r = await get_redis()
    return await r.get(key)


async def cache_set(key: str, value: str, ttl_seconds: int = 60) -> None:
    r = await get_redis()
    await r.set(key, value, ex=ttl_seconds)


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
