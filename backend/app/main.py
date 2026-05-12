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

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("app.starting")
    await init_db()
    try:
        await event_bus.connect()
    except Exception as e:
        logger.warning("event_bus.connect_failed", error=str(e))
    yield
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
