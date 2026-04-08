from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.common.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

def _configure_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                }
            },
            "root": {"level": "INFO", "handlers": ["console"]},
        }
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    _configure_logging()

    from app.providers.router import build_router
    import app.providers.router as provider_router_module

    try:
        provider_router_module.router = build_router(settings.DEFAULT_PROVIDER)
        logger.info("provider initialised: %s", settings.DEFAULT_PROVIDER)
    except Exception as exc:
        logger.error("Failed to initialise providers: %s", exc)

    yield

    from app.common.database import engine

    await engine.dispose()
    logger.info("database engine disposed")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Backend Engine",
        docs="/docs",
        description="Model-agnostic AI job queue",
        version="1.0.0",
        lifespan=lifespan,
    )

    from app.api.jobs import router as jobs_router
    from app.api.health import router as health_router

    app.include_router(jobs_router)
    app.include_router(health_router)

    return app


app = create_app()
