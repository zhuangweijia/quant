from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "StockAnalysis"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://quant:quant@localhost:5432/quant"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    JWT_PRIVATE_KEY_PATH: str = "keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "keys/public.pem"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "RS256"

    ENCRYPTION_KEY: str = ""

    AKSHARE_RATE_LIMIT: int = 500
    SKIP_CONFIG_VALIDATION: str = ""

    # Analysis pipeline config
    STOCK_UNIVERSE: str = "csi300"
    ANALYSIS_TIME: str = "17:00"
    ANALYSIS_TIMEZONE: str = "Asia/Shanghai"
    MODEL_TRAIN_WINDOW_DAYS: int = 756  # ~3 years
    MODEL_VAL_WINDOW_DAYS: int = 126   # ~6 months
    FORWARD_RETURN_DAYS: int = 5
    FORWARD_RETURN_THRESHOLD: float = 0.02
    MODEL_IC_THRESHOLD: float = 0.02
    MODEL_DIR: str = "models"

    RATE_LIMIT_PER_MINUTE: int = 60

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
