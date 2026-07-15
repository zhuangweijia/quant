from contextlib import asynccontextmanager
from datetime import UTC

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import router as v1_router
from app.config import get_settings
from app.core.events import event_bus
from app.core.exceptions import AppException
from app.core.validation import validate_config
from app.database import AsyncSessionLocal, close_db, init_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.utils.logger import setup_logging
from app.ws import ws_manager
from app.ws.routes import router as ws_router

logger = structlog.get_logger()


async def _forward_event_to_ws(topic: str, data: dict):
    user_id = data.get("user_id")
    if user_id:
        from datetime import datetime

        await ws_manager.send_to_user(
            user_id,
            {
                "type": topic,
                "data": data,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("app.starting")
    await init_db()
    await validate_config()
    from app.services.setup_pipeline import setup_pipeline

    await setup_pipeline.interrupt_stale_runs()
    try:
        await event_bus.connect()
    except Exception as e:
        logger.warning("event_bus.connect_failed", error=str(e))

    for topic in [
        event_bus.TOPIC_ANALYSIS_PROGRESS,
        event_bus.TOPIC_RANKING_READY,
        event_bus.TOPIC_DATA_SYNC_ALERT,
    ]:
        try:
            await event_bus.subscribe(
                topic,
                lambda data, _t=topic: _forward_event_to_ws(_t, data),
            )
        except Exception as e:
            logger.warning("event_bus.subscribe_failed", topic=topic, error=str(e))

    from app.services.analysis_pipeline import analysis_pipeline

    analysis_pipeline.start()
    yield
    analysis_pipeline.stop()
    await event_bus.disconnect()
    await close_db()
    logger.info("app.stopped")


app = FastAPI(
    title="StockAnalysis API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    RateLimitMiddleware,
    default_limit=settings.RATE_LIMIT_PER_MINUTE,
)

app.include_router(v1_router, prefix=settings.API_PREFIX)
app.include_router(ws_router)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.code if exc.code < 500 else 400,
        content={
            "code": exc.code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "Internal Server Error"},
    )


@app.get("/health")
async def health():
    result = {"status": "ok"}
    status_code = 200

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception as e:
        result["db"] = f"error: {e}"
        status_code = 503

    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        result["redis"] = "ok"
    except Exception as e:
        result["redis"] = f"error: {e}"
        status_code = 503

    if status_code != 200:
        result["status"] = "degraded"

    return JSONResponse(content=result, status_code=status_code)
