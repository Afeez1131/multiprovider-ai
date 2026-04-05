from __future__ import annotations

import hashlib
import json
import logging

import redis.asyncio as aioredis

from app.common.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def make_cache_key(prompt: str, options: dict[str, object] | None) -> str:
    """Deterministic SHA-256 key from prompt + sorted options."""
    opts = json.dumps(sorted((options or {}).items()), sort_keys=True)
    raw = f"{prompt}:{opts}".encode()
    return f"job_result:{hashlib.sha256(raw).hexdigest()}"


async def get_cached_result(key: str) -> str | None:
    try:
        return await _get_redis().get(key)
    except Exception as exc:
        logger.warning("cache get failed key=%s: %s", key, exc)
        return None


async def set_cached_result(key: str, value: str, ttl: int) -> None:
    try:
        await _get_redis().setex(key, ttl, value)
    except Exception as exc:
        logger.warning("cache set failed key=%s: %s", key, exc)
