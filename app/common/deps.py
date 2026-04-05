from __future__ import annotations

import time
from collections.abc import AsyncGenerator

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.settings import get_settings
from app.common.database import AsyncSessionLocal

settings = get_settings()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def require_api_key(x_api_key: str = Header(default="")) -> str:
    if not settings.API_KEYS:
        return x_api_key  # dev mode — no auth
    if x_api_key not in settings.API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    # Rate limiting — sliding window via Redis
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"rate_limit:{x_api_key}"
        now = time.time()
        window_start = now - 60

        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, 60)
        results = await pipe.execute()
        await r.aclose()

        count = results[2]
        if count > settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS)
    except HTTPException:
        raise
    except Exception:
        pass  # Redis unavailable — fail open rather than denying all requests

    return x_api_key
