from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import get_settings
from app.database import init_db, close_db
from app.core.events import event_bus
from app.utils.logger import setup_logging
from app.api.v1 import router as v1_router
from app.core.exceptions import AppException
from app.ws import ws_manager

logger = structlog.get_logger()


async def _forward_event_to_ws(topic: str, data: dict):
    user_id = data.get("user_id")
    if user_id:
        from datetime import datetime, timezone
        await ws_manager.send_to_user(user_id, {
            "type": topic,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("app.starting")
    await init_db()
    try:
        await event_bus.connect()
    except Exception as e:
        logger.warning("event_bus.connect_failed", error=str(e))

    for topic in [
        event_bus.TOPIC_ORDER_UPDATE,
        event_bus.TOPIC_TRADE_FILL,
        event_bus.TOPIC_RISK_ALERT,
        event_bus.TOPIC_STRATEGY_LOG,
        event_bus.TOPIC_BACKTEST_PROGRESS,
    ]:
        try:
            await event_bus.subscribe(
                topic,
                lambda data, _t=topic: _forward_event_to_ws(_t, data),
            )
        except Exception as e:
            logger.warning("event_bus.subscribe_failed", topic=topic, error=str(e))

    from app.services.strategy_engine import strategy_engine
    strategy_engine.start()
    yield
    strategy_engine.stop()
    await event_bus.disconnect()
    await close_db()
    logger.info("app.stopped")


app = FastAPI(
    title="QuantPlatform API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix=settings.API_PREFIX)

from app.ws.routes import router as ws_router
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
    return {"status": "ok"}
