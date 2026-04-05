from __future__ import annotations

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, Retries, TimeLimit

from app.common.settings import get_settings

settings = get_settings()

broker = RedisBroker(url=settings.REDIS_URL)
broker.add_middleware(AgeLimit())
broker.add_middleware(TimeLimit())
broker.add_middleware(Retries())

dramatiq.set_broker(broker)
