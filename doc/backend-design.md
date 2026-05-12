# QuantPlatform 后端技术设计文档

> 版本: v1.0  
> 日期: 2026-05-13

---

## 目录

- [1. 技术选型与依赖](#1-技术选型与依赖)
- [2. 项目结构](#2-项目结构)
- [3. 应用启动与生命周期](#3-应用启动与生命周期)
- [4. 配置管理](#4-配置管理)
- [5. 数据库层设计](#5-数据库层设计)
- [6. API 层设计](#6-api-层设计)
- [7. WebSocket 层设计](#7-websocket-层设计)
- [8. 服务层设计](#8-服务层设计)
- [9. 行情数据服务](#9-行情数据服务)
- [10. 策略引擎设计](#10-策略引擎设计)
- [11. 回测引擎设计](#11-回测引擎设计)
- [12. 交易执行服务](#12-交易执行服务)
- [13. 风控引擎设计](#13-风控引擎设计)
- [14. 事件总线设计](#14-事件总线设计)
- [15. 认证与鉴权](#15-认证与鉴权)
- [16. 后台任务调度](#16-后台任务调度)
- [17. 日志系统](#17-日志系统)
- [18. 错误处理](#18-错误处理)
- [19. 测试策略](#19-测试策略)

---

## 1. 技术选型与依赖

### 1.1 核心框架

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | ≥ 3.11 | 运行时 |
| FastAPI | ≥ 0.110 | Web 框架 |
| Uvicorn | ≥ 0.29 | ASGI 服务器 |
| Pydantic | ≥ 2.0 | 数据校验与序列化 |

### 1.2 数据层

| 依赖 | 版本 | 用途 |
|------|------|------|
| SQLAlchemy | ≥ 2.0 | ORM（async engine） |
| asyncpg | ≥ 0.29 | PostgreSQL 异步驱动 |
| Alembic | ≥ 1.13 | 数据库迁移 |
| redis | ≥ 5.0 | Redis 异步客户端（hiredis 解析器） |

### 1.3 认证与安全

| 依赖 | 版本 | 用途 |
|------|------|------|
| python-jose | ≥ 3.3 | JWT 编解码（RS256） |
| passlib[bcrypt] | ≥ 1.7 | 密码哈希 |
| cryptography | ≥ 42.0 | API Key 加密存储 |

### 1.4 数据源

| 依赖 | 版本 | 用途 |
|------|------|------|
| akshare | ≥ 1.12 | A股数据源 |
| alpaca-py | ≥ 0.20 | 美股数据 + 交易 |
| python-binance | ≥ 1.0 | 加密货币数据 + 交易 |
| websockets | ≥ 12.0 | WebSocket 客户端 |

### 1.5 策略与计算

| 依赖 | 版本 | 用途 |
|------|------|------|
| pandas | ≥ 2.2 | 数据分析 |
| numpy | ≥ 1.26 | 数值计算 |
| TA-Lib | ≥ 0.4.28 | 技术指标计算 |

### 1.6 基础设施

| 依赖 | 版本 | 用途 |
|------|------|------|
| APScheduler | ≥ 3.10 | 定时任务调度 |
| structlog | ≥ 24.1 | 结构化日志 |
| httpx | ≥ 0.27 | 异步 HTTP 客户端 |
| pyyaml | ≥ 6.0 | YAML 配置解析 |

### 1.7 开发与测试

| 依赖 | 版本 | 用途 |
|------|------|------|
| pytest | ≥ 8.0 | 测试框架 |
| pytest-asyncio | ≥ 0.23 | 异步测试 |
| pytest-cov | ≥ 5.0 | 覆盖率 |
| httpx | ≥ 0.27 | TestClient |
| ruff | ≥ 0.3 | Linter + Formatter |

---

## 2. 项目结构

```
backend/
├── pyproject.toml                    # 项目配置与依赖
├── Dockerfile
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│       ├── 001_init_users.py
│       ├── 002_init_strategies.py
│       ├── 003_init_orders_positions.py
│       ├── 004_init_market_data.py
│       ├── 005_init_backtest_results.py
│       └── 006_init_risk_alerts.py
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI 应用入口
│   ├── config.py                     # 配置管理
│   ├── database.py                   # 数据库连接与会话
│   │
│   ├── models/                       # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── base.py                   # 声明基类 + 公共 Mixin
│   │   ├── user.py
│   │   ├── strategy.py
│   │   ├── order.py
│   │   ├── position.py
│   │   ├── market_data.py
│   │   ├── backtest_result.py
│   │   ├── risk_rule.py
│   │   └── alert.py
│   │
│   ├── schemas/                      # Pydantic 请求/响应模型
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── market.py
│   │   ├── strategy.py
│   │   ├── backtest.py
│   │   ├── trade.py
│   │   ├── risk.py
│   │   ├── dashboard.py
│   │   └── common.py                 # 分页、排序等通用 Schema
│   │
│   ├── api/                          # API 路由层
│   │   ├── __init__.py
│   │   ├── deps.py                   # 依赖注入（db session、current_user 等）
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py             # 汇总路由
│   │       ├── auth.py
│   │       ├── market.py
│   │       ├── strategy.py
│   │       ├── backtest.py
│   │       ├── trade.py
│   │       ├── risk.py
│   │       ├── dashboard.py
│   │       └── settings.py
│   │
│   ├── ws/                           # WebSocket 端点
│   │   ├── __init__.py
│   │   ├── manager.py                # 连接管理器
│   │   ├── market_ws.py              # 行情推送
│   │   └── trade_ws.py               # 交易状态推送
│   │
│   ├── services/                     # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── market/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # MarketDataProvider 抽象基类
│   │   │   ├── collector.py          # 数据采集调度
│   │   │   ├── provider_factory.py   # 数据源工厂
│   │   │   └── providers/
│   │   │       ├── __init__.py
│   │   │       ├── akshare_provider.py
│   │   │       ├── alpaca_provider.py
│   │   │       └── binance_provider.py
│   │   ├── strategy/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py             # 策略运行引擎
│   │   │   ├── backtest_engine.py    # 回测引擎
│   │   │   ├── loader.py             # 策略动态加载器
│   │   │   ├── sandbox.py            # 策略沙箱执行环境
│   │   │   └── registry.py           # 运行时策略注册表
│   │   ├── trade/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # BrokerAdapter 抽象基类
│   │   │   ├── executor.py           # 交易执行器
│   │   │   ├── order_manager.py      # 订单生命周期管理
│   │   │   ├── simulator.py          # 模拟盘撮合引擎
│   │   │   ├── broker_factory.py     # 券商工厂
│   │   │   └── brokers/
│   │   │       ├── __init__.py
│   │   │       ├── paper_broker.py   # 模拟盘 Broker
│   │   │       ├── alpaca_broker.py
│   │   │       └── binance_broker.py
│   │   ├── risk/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py            # 风控引擎
│   │   │   ├── rules.py              # 风控规则实现
│   │   │   ├── position_sizer.py     # 仓位计算
│   │   │   └── monitor.py            # 实时风控监控
│   │   └── dashboard/
│   │       ├── __init__.py
│   │       └── aggregator.py         # 数据聚合计算
│   │
│   ├── core/                         # 核心基础设施
│   │   ├── __init__.py
│   │   ├── events.py                 # 事件总线（Redis Pub/Sub）
│   │   ├── types.py                  # 共享类型定义
│   │   ├── exceptions.py             # 自定义异常
│   │   ├── security.py               # 加密/解密工具
│   │   └── rate_limiter.py           # 限流器
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                 # 日志配置
│       ├── decorators.py             # 通用装饰器
│       └── time_utils.py             # 时区与交易时段工具
│
└── tests/
    ├── __init__.py
    ├── conftest.py                   # pytest fixtures
    ├── test_auth.py
    ├── test_market.py
    ├── test_strategy.py
    ├── test_backtest.py
    ├── test_trade.py
    ├── test_risk.py
    └── services/
        ├── test_akshare_provider.py
        ├── test_alpaca_provider.py
        ├── test_binance_provider.py
        ├── test_backtest_engine.py
        ├── test_simulator.py
        └── test_risk_manager.py
```

---

## 3. 应用启动与生命周期

### 3.1 main.py 启动流程

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.database import init_db, close_db
from app.core.events import event_bus
from app.services.market.collector import MarketCollector
from app.services.strategy.registry import StrategyRegistry
from app.utils.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- Startup ----
    setup_logging()
    await init_db()
    await event_bus.connect()

    collector = MarketCollector()
    await collector.start()

    registry = StrategyRegistry()
    await registry.restore_running_strategies()

    app.state.collector = collector
    app.state.registry = registry

    yield

    # ---- Shutdown ----
    await registry.stop_all()
    await collector.stop()
    await event_bus.disconnect()
    await close_db()


app = FastAPI(
    title="QuantPlatform API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
```

### 3.2 启动序列图

```
Uvicorn 启动
    │
    ├─ 1. setup_logging()            初始化结构化日志
    ├─ 2. init_db()                  创建连接池 + 运行待执行的 Alembic 迁移
    ├─ 3. event_bus.connect()        建立 Redis 连接
    ├─ 4. collector.start()          启动行情数据采集定时任务
    ├─ 5. registry.restore()         恢复上次未停止的策略
    └─ 6. 挂载路由 & 中间件

    ... 应用运行中 ...

Shutdown 信号
    │
    ├─ 1. registry.stop_all()        停止所有运行策略
    ├─ 2. collector.stop()           停止数据采集
    ├─ 3. event_bus.disconnect()     关闭 Redis 连接
    └─ 4. close_db()                 关闭数据库连接池
```

---

## 4. 配置管理

### 4.1 config.py

使用 Pydantic Settings 从环境变量和 `.env` 文件加载配置：

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "QuantPlatform"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://quant:quant@localhost:5432/quant"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # JWT
    JWT_PRIVATE_KEY_PATH: str = "keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "keys/public.pem"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "RS256"

    # 加密
    ENCRYPTION_KEY: str = ""  # AES-256 key (hex)

    # 数据源
    AKSHARE_RATE_LIMIT: int = 500        # 每小时请求限制
    ALPACA_API_KEY: str = ""
    ALPACA_API_SECRET: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"
    ALPACA_DATA_URL: str = "https://data.alpaca.markets"
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    BINANCE_BASE_URL: str = "https://api.binance.com"

    # 交易
    TRADING_MODE: str = "paper"  # paper / live
    ORDER_TIMEOUT_SECONDS: int = 30

    # 回测
    BACKTEST_TIMEOUT_SECONDS: int = 600
    MAX_CONCURRENT_BACKTESTS: int = 3

    # 限流
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_TRADE_PER_MINUTE: int = 10

    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json / console

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### 4.2 .env 文件模板

```env
# .env.example
DEBUG=false
DATABASE_URL=postgresql+asyncpg://quant:quant@localhost:5432/quant
REDIS_URL=redis://localhost:6379/0
JWT_PRIVATE_KEY_PATH=keys/private.pem
JWT_PUBLIC_KEY_PATH=keys/public.pem
ENCRYPTION_KEY=
TRADING_MODE=paper
LOG_LEVEL=INFO
```

---

## 5. 数据库层设计

### 5.1 连接与会话管理

```python
# app/database.py
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    # 测试连接
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))


async def close_db():
    await engine.dispose()
```

### 5.2 ORM 基类

```python
# app/models/base.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
```

### 5.3 完整 ORM 模型

#### User 模型

```python
# app/models/user.py
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(256), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(16), default="trader", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    login_failed_count: Mapped[int] = mapped_column(
        default=0, nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    strategies = relationship("Strategy", back_populates="user", lazy="selectin")
    positions = relationship("Position", back_populates="user", lazy="selectin")
```

#### Strategy 模型

```python
# app/models/strategy.py
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class Strategy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "strategies"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="draft", nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User", back_populates="strategies")
    orders = relationship("Order", back_populates="strategy", lazy="selectin")
    backtest_results = relationship(
        "BacktestResult", back_populates="strategy", lazy="selectin"
    )
```

#### Order 模型

```python
# app/models/order.py
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_strategy_created", "strategy_id", "created_at"),
        Index("ix_orders_symbol", "symbol"),
    )

    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    broker_order_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    filled_qty: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("0"), nullable=False
    )
    filled_price: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    commission: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("0"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    strategy = relationship("Strategy", back_populates="orders")
    user = relationship("User")
```

#### Position 模型

```python
# app/models/position.py
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class Position(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "strategy_id", "symbol",
            name="uq_position_user_strategy_symbol"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    avg_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    frozen_qty: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("0"), nullable=False
    )

    user = relationship("User", back_populates="positions")
    strategy = relationship("Strategy")
```

#### MarketData 模型

```python
# app/models/market_data.py
from decimal import Decimal
from sqlalchemy import String, Numeric, BigInteger, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class MarketData(TimestampMixin, Base):
    __tablename__ = "market_data"
    __table_args__ = (
        UniqueConstraint(
            "symbol", "market", "timeframe", "timestamp",
            name="uq_market_data_symbol_tf_ts"
        ),
        Index(
            "ix_market_data_lookup",
            "symbol", "market", "timeframe", "timestamp",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
```

#### BacktestResult 模型

```python
# app/models/backtest_result.py
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Numeric, Date, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class BacktestResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "backtest_results"

    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    total_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    annual_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    sortino_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    max_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    calmar_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    win_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    profit_factor: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    trade_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_holding_period: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    equity_curve: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    drawdown_curve: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    trades: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    monthly_returns: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    strategy = relationship("Strategy", back_populates="backtest_results")
    user = relationship("User")
```

#### RiskRule 模型

```python
# app/models/risk_rule.py
from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TimestampMixin


class RiskRule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "risk_rules"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=True
    )
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(default=0, nullable=False)
```

#### Alert 模型

```python
# app/models/alert.py
from sqlalchemy import String, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TimestampMixin


class Alert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    level: Mapped[str] = mapped_column(String(8), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

### 5.4 Alembic 迁移工作流

```bash
# 生成迁移文件
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看当前版本
alembic current
```

---

## 6. API 层设计

### 6.1 依赖注入

```python
# app/api/deps.py
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User


security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    payload = AuthService.decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = await db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
```

### 6.2 路由注册

```python
# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1 import auth, market, strategy, backtest, trade, risk, dashboard, settings

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(market.router, prefix="/market", tags=["行情"])
router.include_router(strategy.router, prefix="/strategies", tags=["策略"])
router.include_router(backtest.router, prefix="/backtest", tags=["回测"])
router.include_router(trade.router, prefix="/trade", tags=["交易"])
router.include_router(risk.router, prefix="/risk", tags=["风控"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["看板"])
router.include_router(settings.router, prefix="/settings", tags=["设置"])
```

### 6.3 通用响应格式

```python
# app/schemas/common.py
from typing import Generic, TypeVar, Any
from pydantic import BaseModel


T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None


class PageRequest(BaseModel):
    page: int = 1
    page_size: int = 20


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

### 6.4 API 路由示例（Strategy）

```python
# app/api/v1/strategy.py
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import CurrentUser, DBSession
from app.schemas.strategy import (
    StrategyCreate, StrategyUpdate, StrategyDetail, StrategyListItem
)
from app.schemas.common import ResponseBase, PageResponse
from app.services.strategy.engine import StrategyEngine

router = APIRouter()


@router.get("", response_model=ResponseBase[PageResponse[StrategyListItem]])
async def list_strategies(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    market: str | None = Query(None),
    keyword: str | None = Query(None),
):
    return await StrategyEngine.list_strategies(
        db, user.id, page, page_size, status, market, keyword
    )


@router.post("", response_model=ResponseBase[StrategyDetail], status_code=201)
async def create_strategy(
    user: CurrentUser,
    db: DBSession,
    payload: StrategyCreate,
):
    return await StrategyEngine.create_strategy(db, user.id, payload)


@router.get("/{strategy_id}", response_model=ResponseBase[StrategyDetail])
async def get_strategy(
    user: CurrentUser,
    db: DBSession,
    strategy_id: UUID,
):
    return await StrategyEngine.get_strategy(db, user.id, strategy_id)


@router.put("/{strategy_id}", response_model=ResponseBase[StrategyDetail])
async def update_strategy(
    user: CurrentUser,
    db: DBSession,
    strategy_id: UUID,
    payload: StrategyUpdate,
):
    return await StrategyEngine.update_strategy(db, user.id, strategy_id, payload)


@router.delete("/{strategy_id}", response_model=ResponseBase[None])
async def delete_strategy(
    user: CurrentUser,
    db: DBSession,
    strategy_id: UUID,
):
    return await StrategyEngine.delete_strategy(db, user.id, strategy_id)


@router.post("/{strategy_id}/start", response_model=ResponseBase[None])
async def start_strategy(
    user: CurrentUser,
    db: DBSession,
    strategy_id: UUID,
):
    return await StrategyEngine.start_strategy(db, user.id, strategy_id)


@router.post("/{strategy_id}/stop", response_model=ResponseBase[None])
async def stop_strategy(
    user: CurrentUser,
    db: DBSession,
    strategy_id: UUID,
):
    return await StrategyEngine.stop_strategy(db, user.id, strategy_id)


@router.get("/{strategy_id}/logs", response_model=ResponseBase[PageResponse[dict]])
async def get_strategy_logs(
    user: CurrentUser,
    db: DBSession,
    strategy_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    level: str | None = Query(None),
):
    return await StrategyEngine.get_logs(db, user.id, strategy_id, page, page_size, level)
```

### 6.5 Pydantic Schema 示例

```python
# app/schemas/strategy.py
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    description: str | None = Field(None, max_length=1000)
    code: str = Field(..., min_length=1)
    params: dict | None = None
    market: str = Field(..., pattern="^(a_stock|us_stock|crypto)$")


class StrategyUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=128)
    description: str | None = None
    code: str | None = Field(None, min_length=1)
    params: dict | None = None


class StrategyListItem(BaseModel):
    id: UUID
    name: str
    market: str
    status: str
    created_at: datetime
    updated_at: datetime


class StrategyDetail(StrategyListItem):
    description: str | None
    code: str
    params: dict | None


class StrategyLogItem(BaseModel):
    timestamp: datetime
    level: str
    message: str
```

---

## 7. WebSocket 层设计

### 7.1 连接管理器

```python
# app/ws/manager.py
from fastapi import WebSocket
from typing import defaultdict
import json
import asyncio


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def connect(self, topic: str, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections[topic].append(ws)

    async def disconnect(self, topic: str, ws: WebSocket):
        async with self._lock:
            if ws in self._connections[topic]:
                self._connections[topic].remove(ws)

    async def broadcast(self, topic: str, data: dict):
        message = json.dumps(data)
        async with self._lock:
            dead = []
            for ws in self._connections[topic]:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections[topic].remove(ws)

    async def send_to_user(self, user_id: str, topic: str, data: dict):
        message = json.dumps(data)
        user_topic = f"{topic}:{user_id}"
        async with self._lock:
            dead = []
            for ws in self._connections[user_topic]:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections[user_topic].remove(ws)


ws_manager = ConnectionManager()
```

### 7.2 行情 WebSocket

```python
# app/ws/market_ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.ws.manager import ws_manager

router = APIRouter()


@router.websocket("/ws/market")
async def market_websocket(
    ws: WebSocket,
    token: str = Query(...),
):
    user = await authenticate_ws(token)
    if not user:
        await ws.close(code=4001, reason="Unauthorized")
        return

    topic = f"market:tick:{user.id}"
    await ws_manager.connect(topic, ws)
    try:
        while True:
            data = await ws.receive_json()
            # 客户端发送订阅/取消订阅指令
            action = data.get("action")
            symbols = data.get("symbols", [])
            if action == "subscribe":
                # 注册行情订阅
                await subscribe_market_data(user.id, symbols)
            elif action == "unsubscribe":
                await unsubscribe_market_data(user.id, symbols)
    except WebSocketDisconnect:
        await ws_manager.disconnect(topic, ws)
```

### 7.3 交易 WebSocket

```python
# app/ws/trade_ws.py
@router.websocket("/ws/trade")
async def trade_websocket(ws: WebSocket, token: str = Query(...)):
    user = await authenticate_ws(token)
    if not user:
        await ws.close(code=4001, reason="Unauthorized")
        return

    topic = f"trade:updates:{user.id}"
    await ws_manager.connect(topic, ws)
    try:
        while True:
            await ws.receive_text()  # 保持连接，等待客户端心跳
    except WebSocketDisconnect:
        await ws_manager.disconnect(topic, ws)
```

### 7.4 WebSocket 消息格式

```json
// 行情推送
{
    "type": "tick",
    "data": {
        "symbol": "BTCUSDT",
        "market": "crypto",
        "price": 62345.67,
        "volume": 123.45,
        "change_pct": 2.35,
        "timestamp": "2026-05-13T10:30:00Z"
    }
}

// 订单状态更新
{
    "type": "order_update",
    "data": {
        "order_id": "uuid-xxx",
        "status": "filled",
        "filled_qty": 1.5,
        "filled_price": 62345.67,
        "timestamp": "2026-05-13T10:30:01Z"
    }
}

// 风控告警
{
    "type": "risk_alert",
    "data": {
        "level": "warning",
        "title": "接近止损线",
        "message": "BTCUSDT 浮亏已达 -8.5%，止损线为 -10%",
        "timestamp": "2026-05-13T10:30:02Z"
    }
}

// 回测进度
{
    "type": "backtest_progress",
    "data": {
        "task_id": "uuid-xxx",
        "progress": 0.65,
        "current_bar": 650,
        "total_bars": 1000,
        "status": "running"
    }
}
```

---

## 8. 服务层设计

### 8.1 分层架构

```
┌─────────────────────────────────────────────┐
│  API Layer (app/api/v1/)                     │
│  - 参数校验 (Pydantic Schema)                │
│  - 权限检查 (deps.py)                        │
│  - 响应序列化                                │
├─────────────────────────────────────────────┤
│  Service Layer (app/services/)               │
│  - 业务逻辑编排                              │
│  - 跨模型事务                                │
│  - 调用外部接口                              │
├─────────────────────────────────────────────┤
│  Model Layer (app/models/)                   │
│  - ORM 映射                                  │
│  - 数据库访问                                │
├─────────────────────────────────────────────┤
│  Infrastructure (app/core/)                  │
│  - 事件总线                                  │
│  - 安全工具                                  │
│  - 缓存                                      │
└─────────────────────────────────────────────┘
```

**核心原则**:
- API 层不包含业务逻辑，只做参数转发和响应包装
- Service 层之间可以互相调用，但避免循环依赖
- Model 层只做数据访问，不包含业务逻辑
- 外部接口调用全部封装在 Service 层

---

## 9. 行情数据服务

### 9.1 Provider 抽象基类

```python
# app/services/market/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator


class MarketDataProvider(ABC):
    @property
    @abstractmethod
    def market(self) -> str:
        ...

    @abstractmethod
    async def get_klines(
        self,
        symbol: str,
        timeframe: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = 500,
    ) -> list[dict]:
        ...

    @abstractmethod
    async def subscribe_ticks(
        self, symbols: list[str]
    ) -> AsyncIterator[dict]:
        ...

    @abstractmethod
    async def search_symbols(self, keyword: str) -> list[dict]:
        ...

    @abstractmethod
    async def get_latest_price(self, symbol: str) -> dict:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
```

### 9.2 Provider 工厂

```python
# app/services/market/provider_factory.py
from app.services.market.providers.akshare_provider import AKShareProvider
from app.services.market.providers.alpaca_provider import AlpacaProvider
from app.services.market.providers.binance_provider import BinanceProvider
from app.services.market.base import MarketDataProvider


_providers: dict[str, type[MarketDataProvider]] = {
    "a_stock": AKShareProvider,
    "us_stock": AlpacaProvider,
    "crypto": BinanceProvider,
}

_instances: dict[str, MarketDataProvider] = {}


def get_provider(market: str) -> MarketDataProvider:
    if market not in _providers:
        raise ValueError(f"Unsupported market: {market}")
    if market not in _instances:
        _instances[market] = _providers[market]()
    return _instances[market]
```

### 9.3 数据采集器

```python
# app/services/market/collector.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.market.provider_factory import get_provider
from app.core.events import event_bus


class MarketCollector:
    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._running = False

    async def start(self):
        self._running = True
        # A股 - 交易日每5分钟采集
        self._scheduler.add_job(
            self._collect_a_stock_klines,
            "cron",
            minute="*/5",
            day_of_week="mon-fri",
            hour="9-15",
        )
        # A股 - 日终采集日K线
        self._scheduler.add_job(
            self._collect_a_stock_daily,
            "cron",
            hour=15, minute=30,
            day_of_week="mon-fri",
        )
        # 美股 - 交易时段每分钟采集
        self._scheduler.add_job(
            self._collect_us_stock_klines,
            "cron",
            minute="*",
            hour="21-23",  # UTC -> 美东时间
        )
        # 加密货币 - 每分钟采集
        self._scheduler.add_job(
            self._collect_crypto_klines,
            "interval",
            minutes=1,
        )
        # 实时行情 WebSocket 订阅
        self._scheduler.add_job(
            self._subscribe_crypto_ticks,
            "date",
        )  # 启动时立即执行
        self._scheduler.start()

    async def stop(self):
        self._running = False
        self._scheduler.shutdown(wait=False)

    async def _collect_a_stock_klines(self):
        provider = get_provider("a_stock")
        symbols = await self._get_watched_symbols("a_stock")
        for symbol in symbols:
            try:
                klines = await provider.get_klines(
                    symbol, "5m", limit=1
                )
                await self._save_klines("a_stock", "5m", klines)
                await event_bus.publish(
                    "market:bar",
                    {"market": "a_stock", "symbol": symbol, "bars": klines}
                )
            except Exception as e:
                logger.error(f"Collect A-stock klines failed: {symbol} - {e}")

    async def _subscribe_crypto_ticks(self):
        provider = get_provider("crypto")
        symbols = await self._get_watched_symbols("crypto")
        async for tick in provider.subscribe_ticks(symbols):
            await event_bus.publish("market:tick", tick)
            await self._cache_tick(tick)

    async def _save_klines(self, market: str, timeframe: str, klines: list[dict]):
        # 批量 INSERT ... ON CONFLICT DO NOTHING
        ...

    async def _cache_tick(self, tick: dict):
        # 写入 Redis
        ...

    async def _get_watched_symbols(self, market: str) -> list[str]:
        # 从 DB 查询运行中策略订阅的标的 + 用户关注的标的
        ...
```

---

## 10. 策略引擎设计

### 10.1 策略加载器

```python
# app/services/strategy/loader.py
import ast
import importlib.util
import sys
from pathlib import Path
from app.core.types import BaseStrategy

ALLOWED_IMPORTS = {
    "pandas", "numpy", "talib", "math", "datetime",
    "collections", "itertools", "functools", "typing",
    "dataclasses", "enum", "decimal",
}


class StrategyLoader:
    @staticmethod
    def validate_code(code: str) -> tuple[bool, str]:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                        return False, f"Forbidden import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] not in ALLOWED_IMPORTS:
                    return False, f"Forbidden import: {node.module}"

        has_strategy_class = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseStrategy":
                        has_strategy_class = True
        if not has_strategy_class:
            return False, "No class inheriting BaseStrategy found"

        return True, "OK"

    @staticmethod
    def load_strategy(code: str, class_name: str | None = None) -> type[BaseStrategy]:
        module_name = f"strategy_dynamic_{id(code)}"
        spec = importlib.util.spec_from_loader(module_name, loader=None)
        module = importlib.util.module_from_spec(spec)
        exec(compile(code, "<strategy>", "exec"), module.__dict__)

        strategy_class = None
        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseStrategy)
                and obj is not BaseStrategy
            ):
                if class_name is None or name == class_name:
                    strategy_class = obj
                    break

        if strategy_class is None:
            raise ValueError("No valid strategy class found in code")
        return strategy_class
```

### 10.2 策略运行注册表

```python
# app/services/strategy/registry.py
import asyncio
from dict import Dict
from app.services.strategy.loader import StrategyLoader
from app.services.strategy.engine import StrategyRuntime


class StrategyRegistry:
    def __init__(self):
        self._runtimes: Dict[str, StrategyRuntime] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    async def register(self, strategy_id: str, runtime: StrategyRuntime):
        self._runtimes[strategy_id] = runtime
        self._tasks[strategy_id] = asyncio.create_task(
            runtime.run(), name=f"strategy-{strategy_id}"
        )

    async def unregister(self, strategy_id: str):
        runtime = self._runtimes.pop(strategy_id, None)
        task = self._tasks.pop(strategy_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if runtime:
            await runtime.stop()

    async def restore_running_strategies(self):
        # 从数据库查询 status=running 的策略，重新加载并启动
        ...

    async def stop_all(self):
        for sid in list(self._runtimes.keys()):
            await self.unregister(sid)

    def get_runtime(self, strategy_id: str) -> StrategyRuntime | None:
        return self._runtimes.get(strategy_id)
```

### 10.3 策略运行时

```python
# app/services/strategy/engine.py
import asyncio
from app.services.strategy.loader import StrategyLoader
from app.services.strategy.sandbox import StrategySandbox
from app.core.events import event_bus
from app.core.types import BarData, TickData


class StrategyRuntime:
    def __init__(self, strategy_id: str, strategy_class, params: dict, context):
        self._strategy_id = strategy_id
        self._instance = strategy_class(params)
        self._context = context
        self._running = False

    async def run(self):
        self._running = True
        try:
            self._instance.on_init(self._context)
            async for event in event_bus.subscribe(f"strategy:{self._strategy_id}"):
                if not self._running:
                    break
                if event["type"] == "bar":
                    bar = BarData(**event["data"])
                    await self._execute_on_bar(bar)
                elif event["type"] == "tick":
                    tick = TickData(**event["data"])
                    await self._execute_on_tick(tick)
        except asyncio.CancelledError:
            pass
        finally:
            self._instance.on_stop(self._context)

    async def _execute_on_bar(self, bar: BarData):
        sandbox = StrategySandbox(self._context)
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._instance.on_bar, bar),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            await self._log("error", f"on_bar timeout for {bar.symbol}")
        except Exception as e:
            await self._log("error", f"on_bar error: {e}")

    async def stop(self):
        self._running = False

    async def _log(self, level: str, message: str):
        await event_bus.publish("strategy:log", {
            "strategy_id": self._strategy_id,
            "level": level,
            "message": message,
        })
```

---

## 11. 回测引擎设计

### 11.1 回测流程

```
用户发起回测请求
       │
       ▼
┌─ 参数校验 ──────────────────────────────────────┐
│ · 策略ID有效性                                    │
│ · 时间范围合法性                                   │
│ · 并发回测数检查                                   │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─ 数据加载 ──────────────────────────────────────┐
│ · 从 PostgreSQL 加载历史K线                       │
│ · 检查数据完整性（缺失率 < 10%）                   │
│ · 数据缺失则从数据源补拉                           │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─ 回测执行（异步任务） ───────────────────────────┐
│                                                   │
│  for each bar in historical_data:                 │
│    ├── 更新模拟账户的当前价格                       │
│    ├── 更新持仓的浮动盈亏                           │
│    ├── 调用 strategy.on_bar(bar)                  │
│    ├── 收集策略产生的交易信号                       │
│    ├── 进入模拟撮合引擎                             │
│    │   ├── 计算成交价（含滑点）                     │
│    │   ├── 计算手续费                              │
│    │   ├── 更新模拟持仓                            │
│    │   └── 更新模拟余额                            │
│    ├── 检查止损/止盈                               │
│    ├── 更新权益曲线                                │
│    └── 推送进度（每10%）                           │
│                                                   │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─ 统计计算 ──────────────────────────────────────┐
│ · 总收益率 / 年化收益率                            │
│ · 夏普比率 / 索提诺比率                            │
│ · 最大回撤 / Calmar 比率                           │
│ · 胜率 / 盈亏比                                    │
│ · 月度收益矩阵                                     │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─ 结果存储 ──────────────────────────────────────┐
│ · 保存到 backtest_results 表                      │
│ · WebSocket 通知完成                               │
└─────────────────────────────────────────────────┘
```

### 11.2 回测引擎核心代码结构

```python
# app/services/strategy/backtest_engine.py
import asyncio
from decimal import Decimal
from dataclasses import dataclass, field
from app.services.strategy.loader import StrategyLoader
from app.services.trade.simulator import Simulator
from app.core.types import BarData


@dataclass
class BacktestConfig:
    strategy_id: str
    strategy_class: type
    params: dict
    symbol: str
    market: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: Decimal
    commission_rate: Decimal
    slippage: Decimal


@dataclass
class BacktestState:
    cash: Decimal
    equity: Decimal
    positions: dict = field(default_factory=dict)
    equity_curve: list = field(default_factory=list)
    drawdown_curve: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    peak_equity: Decimal = Decimal("0")


class BacktestEngine:
    def __init__(self, config: BacktestConfig):
        self._config = config
        self._strategy = config.strategy_class(config.params)
        self._simulator = Simulator(
            commission_rate=config.commission_rate,
            slippage=config.slippage,
        )
        self._state = BacktestState(cash=config.initial_capital, equity=config.initial_capital)
        self._progress_callback = None

    def set_progress_callback(self, callback):
        self._progress_callback = callback

    async def run(self, bars: list[BarData]) -> dict:
        total = len(bars)
        self._strategy.on_init(self._build_context())

        for i, bar in enumerate(bars):
            # 更新当前价格
            self._current_prices[bar.symbol] = bar.close

            # 执行策略
            self._strategy.on_bar(bar)

            # 处理待成交订单
            self._simulator.process_orders(bar, self._state)

            # 检查止损止盈
            self._simulator.check_stop_loss_take_profit(bar, self._state)

            # 更新权益
            self._update_equity()

            # 进度回调
            if self._progress_callback and i % max(1, total // 10) == 0:
                await self._progress_callback(i / total)

        return self._calculate_statistics()

    def _build_context(self):
        # 构建策略上下文（模拟版）
        ...

    def _update_equity(self):
        position_value = sum(
            pos["qty"] * self._current_prices.get(pos["symbol"], 0)
            for pos in self._state.positions.values()
        )
        self._state.equity = self._state.cash + position_value
        if self._state.equity > self._state.peak_equity:
            self._state.peak_equity = self._state.equity
        drawdown = (
            (self._state.peak_equity - self._state.equity)
            / self._state.peak_equity
            if self._state.peak_equity > 0
            else Decimal("0")
        )
        self._state.equity_curve.append(float(self._state.equity))
        self._state.drawdown_curve.append(float(drawdown))

    def _calculate_statistics(self) -> dict:
        import numpy as np
        curve = np.array(self._state.equity_curve)
        returns = np.diff(curve) / curve[:-1]

        total_return = (curve[-1] - curve[0]) / curve[0]
        trading_days = len(curve) - 1
        annual_return = (1 + total_return) ** (252 / max(trading_days, 1)) - 1

        daily_returns = returns
        sharpe = (
            np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
            if np.std(daily_returns) > 0
            else 0
        )

        downside = daily_returns[daily_returns < 0]
        sortino = (
            np.mean(daily_returns) / np.std(downside) * np.sqrt(252)
            if len(downside) > 0 and np.std(downside) > 0
            else 0
        )

        max_dd = max(self._state.drawdown_curve) if self._state.drawdown_curve else 0
        calmar = annual_return / max_dd if max_dd > 0 else 0

        trades = self._state.trades
        winning = [t for t in trades if t["pnl"] > 0]
        losing = [t for t in trades if t["pnl"] <= 0]
        win_rate = len(winning) / len(trades) if trades else 0
        profit_factor = (
            sum(t["pnl"] for t in winning) / abs(sum(t["pnl"] for t in losing))
            if losing and sum(t["pnl"] for t in losing) != 0
            else float("inf")
        )

        return {
            "total_return": round(float(total_return), 4),
            "annual_return": round(float(annual_return), 4),
            "sharpe_ratio": round(float(sharpe), 4),
            "sortino_ratio": round(float(sortino), 4),
            "max_drawdown": round(float(max_dd), 4),
            "calmar_ratio": round(float(calmar), 4),
            "win_rate": round(float(win_rate), 4),
            "profit_factor": round(float(profit_factor), 4),
            "trade_count": len(trades),
            "equity_curve": self._state.equity_curve,
            "drawdown_curve": self._state.drawdown_curve,
            "trades": trades,
            "monthly_returns": self._calc_monthly_returns(),
        }
```

---

## 12. 交易执行服务

### 12.1 Broker 抽象基类

```python
# app/services/trade/base.py
from abc import ABC, abstractmethod


class BrokerAdapter(ABC):
    @property
    @abstractmethod
    def market(self) -> str:
        ...

    @abstractmethod
    async def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: float,
        price: float | None = None,
    ) -> dict:
        """返回 {"broker_order_id": str, "status": str}"""
        ...

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> dict:
        ...

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> dict:
        """返回 {"status": str, "filled_qty": float, "filled_price": float}"""
        ...

    @abstractmethod
    async def get_positions(self) -> list[dict]:
        ...

    @abstractmethod
    async def get_account(self) -> dict:
        """返回 {"cash": float, "equity": float, "buying_power": float}"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
```

### 12.2 订单管理器

```python
# app/services/trade/order_manager.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.order import Order
from app.core.events import event_bus
import asyncio


class OrderManager:
    def __init__(self, broker: BrokerAdapter):
        self._broker = broker
        self._polling_tasks: dict[str, asyncio.Task] = {}

    async def submit(self, db: AsyncSession, order: Order) -> Order:
        try:
            result = await self._broker.submit_order(
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                qty=float(order.qty),
                price=float(order.price) if order.price else None,
            )
            order.broker_order_id = result["broker_order_id"]
            order.status = "submitted"
            await db.flush()

            # 启动状态轮询
            self._polling_tasks[str(order.id)] = asyncio.create_task(
                self._poll_order_status(db, order)
            )
            return order
        except Exception as e:
            order.status = "rejected"
            order.error_message = str(e)
            await db.flush()
            raise

    async def cancel(self, db: AsyncSession, order: Order) -> Order:
        if order.broker_order_id:
            await self._broker.cancel_order(order.broker_order_id)
        order.status = "cancelled"
        await db.flush()

        # 停止轮询
        task = self._polling_tasks.pop(str(order.id), None)
        if task:
            task.cancel()

        await event_bus.publish("trade:order", {
            "user_id": str(order.user_id),
            "order_id": str(order.id),
            "status": "cancelled",
        })
        return order

    async def _poll_order_status(self, db: AsyncSession, order: Order):
        max_attempts = 600  # 最多轮询10分钟（每秒一次）
        for _ in range(max_attempts):
            await asyncio.sleep(1)
            try:
                status = await self._broker.get_order_status(order.broker_order_id)
                if status["status"] in ("filled", "cancelled", "rejected", "expired"):
                    order.status = status["status"]
                    order.filled_qty = status.get("filled_qty", order.filled_qty)
                    order.filled_price = status.get("filled_price", order.filled_price)
                    await db.flush()
                    await event_bus.publish("trade:order", {
                        "user_id": str(order.user_id),
                        "order_id": str(order.id),
                        "status": order.status,
                        "filled_qty": float(order.filled_qty),
                        "filled_price": float(order.filled_price) if order.filled_price else None,
                    })
                    break
                elif status["status"] == "partial_filled":
                    order.filled_qty = status.get("filled_qty", order.filled_qty)
                    order.filled_price = status.get("filled_price", order.filled_price)
                    await db.flush()
            except Exception:
                continue
```

### 12.3 模拟撮合引擎

```python
# app/services/trade/simulator.py
from decimal import Decimal


class Simulator:
    def __init__(self, commission_rate: Decimal, slippage: Decimal):
        self._commission_rate = commission_rate
        self._slippage = slippage
        self._pending_orders: list[dict] = []

    def add_order(self, order: dict):
        self._pending_orders.append(order)

    def process_orders(self, bar, state):
        filled_orders = []
        remaining = []

        for order in self._pending_orders:
            fill_price = self._try_fill(order, bar)
            if fill_price is not None:
                commission = self._calc_commission(order["qty"], fill_price)
                actual_cost = fill_price * order["qty"] + commission

                if order["side"] == "buy":
                    if actual_cost <= state.cash:
                        state.cash -= actual_cost
                        self._update_position(state, order["symbol"], order["qty"], fill_price)
                        filled_orders.append({
                            "symbol": order["symbol"],
                            "side": "buy",
                            "qty": order["qty"],
                            "price": fill_price,
                            "commission": commission,
                        })
                    else:
                        remaining.append(order)  # 资金不足
                else:
                    proceeds = fill_price * order["qty"] - commission
                    state.cash += proceeds
                    self._reduce_position(state, order["symbol"], order["qty"], fill_price)
                    filled_orders.append({
                        "symbol": order["symbol"],
                        "side": "sell",
                        "qty": order["qty"],
                        "price": fill_price,
                        "commission": commission,
                    })
            else:
                remaining.append(order)

        self._pending_orders = remaining
        state.trades.extend(filled_orders)

    def _try_fill(self, order: dict, bar) -> Decimal | None:
        if order["order_type"] == "market":
            if order["side"] == "buy":
                return bar.open * (1 + self._slippage)
            else:
                return bar.open * (1 - self._slippage)
        elif order["order_type"] == "limit":
            if order["side"] == "buy" and bar.low <= order["price"]:
                return order["price"]
            elif order["side"] == "sell" and bar.high >= order["price"]:
                return order["price"]
        elif order["order_type"] == "stop":
            if order["side"] == "sell" and bar.low <= order["price"]:
                return order["price"] * (1 - self._slippage)
            elif order["side"] == "buy" and bar.high >= order["price"]:
                return order["price"] * (1 + self._slippage)
        return None

    def _calc_commission(self, qty: Decimal, price: Decimal) -> Decimal:
        return qty * price * self._commission_rate

    def _update_position(self, state, symbol, qty, price):
        if symbol in state.positions:
            pos = state.positions[symbol]
            total_cost = pos["avg_price"] * pos["qty"] + price * qty
            pos["qty"] += qty
            pos["avg_price"] = total_cost / pos["qty"]
        else:
            state.positions[symbol] = {"qty": qty, "avg_price": price}

    def _reduce_position(self, state, symbol, qty, price):
        if symbol in state.positions:
            pos = state.positions[symbol]
            pos["qty"] -= qty
            if pos["qty"] <= 0:
                del state.positions[symbol]
```

---

## 13. 风控引擎设计

### 13.1 风控管理器

```python
# app/services/risk/manager.py
from app.services.risk.rules import RuleEngine
from app.core.events import event_bus


class RiskManager:
    def __init__(self):
        self._rule_engine = RuleEngine()

    async def check_order(self, user_id: str, order: dict, context: dict) -> tuple[bool, str]:
        rules = await self._load_rules(user_id, order.get("strategy_id"))
        for rule in rules:
            if not rule.enabled:
                continue
            passed, reason = await self._rule_engine.evaluate(rule, order, context)
            if not passed:
                await self._create_alert(user_id, "error", "风控拦截", reason)
                return False, reason
        return True, ""

    async def check_positions(self, user_id: str, positions: dict, prices: dict):
        """实时检查持仓是否触发止损止盈"""
        rules = await self._load_rules(user_id, None)
        stop_loss_rules = [r for r in rules if r.rule_type == "stop_loss"]
        take_profit_rules = [r for r in rules if r.rule_type == "take_profit"]

        for symbol, pos in positions.items():
            current_price = prices.get(symbol, 0)
            pnl_pct = (current_price - pos["avg_price"]) / pos["avg_price"]

            for rule in stop_loss_rules:
                if rule.params.get("symbol") in (symbol, None):
                    if pnl_pct <= -rule.params["stop_loss_pct"]:
                        await self._trigger_stop(user_id, symbol, pos, "stop_loss")
                        return

            for rule in take_profit_rules:
                if rule.params.get("symbol") in (symbol, None):
                    if pnl_pct >= rule.params["take_profit_pct"]:
                        await self._trigger_stop(user_id, symbol, pos, "take_profit")
                        return

    async def _trigger_stop(self, user_id, symbol, position, trigger_type):
        await event_bus.publish("risk:alert", {
            "user_id": user_id,
            "level": "warning",
            "title": f"触发{trigger_type}",
            "message": f"{symbol} 触发 {trigger_type}，自动平仓 {position['qty']}",
        })
        # 生成市价平仓订单
        ...

    async def _load_rules(self, user_id: str, strategy_id: str | None):
        # 从 DB 加载全局规则 + 策略规则，按 priority 排序
        ...

    async def _create_alert(self, user_id, level, title, message):
        # 写入 alerts 表 + WebSocket 通知
        ...
```

### 13.2 风控规则实现

```python
# app/services/risk/rules.py
from abc import ABC, abstractmethod


class RiskRule(ABC):
    @abstractmethod
    async def evaluate(self, order: dict, context: dict) -> tuple[bool, str]:
        ...


class MaxPositionValueRule(RiskRule):
    async def evaluate(self, order, context):
        if order["side"] != "buy":
            return True, ""
        current_value = context.get("position_values", {}).get(order["symbol"], 0)
        order_value = order["qty"] * (order.get("price") or context["current_price"])
        max_value = self.params["max_value"]
        if current_value + order_value > max_value:
            return False, f"单标的持仓金额超限: {current_value + order_value:.2f} > {max_value}"
        return True, ""


class MaxPositionRatioRule(RiskRule):
    async def evaluate(self, order, context):
        if order["side"] != "buy":
            return True, ""
        total_equity = context.get("total_equity", 0)
        order_value = order["qty"] * (order.get("price") or context["current_price"])
        current_ratio = context.get("total_position_value", 0) / total_equity if total_equity > 0 else 0
        new_ratio = current_ratio + order_value / total_equity if total_equity > 0 else 1
        if new_ratio > self.params["max_ratio"]:
            return False, f"总仓位占比超限: {new_ratio:.2%} > {self.params['max_ratio']:.2%}"
        return True, ""


class DailyLossLimitRule(RiskRule):
    async def evaluate(self, order, context):
        daily_loss = context.get("daily_loss", 0)
        if daily_loss >= self.params["max_daily_loss"]:
            return False, f"日亏损已达限额: {daily_loss:.2f} >= {self.params['max_daily_loss']}"
        return True, ""


class DailyTradeLimitRule(RiskRule):
    async def evaluate(self, order, context):
        daily_trades = context.get("daily_trades", 0)
        if daily_trades >= self.params["max_trades"]:
            return False, f"日交易次数已达上限: {daily_trades} >= {self.params['max_trades']}"
        return True, ""


class BlacklistRule(RiskRule):
    async def evaluate(self, order, context):
        if order["symbol"] in self.params.get("symbols", []):
            return False, f"标的 {order['symbol']} 在交易黑名单中"
        return True, ""


class MaxOrderAmountRule(RiskRule):
    async def evaluate(self, order, context):
        order_value = order["qty"] * (order.get("price") or context["current_price"])
        if order_value > self.params["max_amount"]:
            return False, f"单笔下单金额超限: {order_value:.2f} > {self.params['max_amount']}"
        return True, ""


RULE_MAP = {
    "max_position_value": MaxPositionValueRule,
    "max_position_ratio": MaxPositionRatioRule,
    "daily_loss_limit": DailyLossLimitRule,
    "daily_trade_limit": DailyTradeLimitRule,
    "blacklist": BlacklistRule,
    "max_order_amount": MaxOrderAmountRule,
}


class RuleEngine:
    def create_rule(self, rule_type: str, params: dict) -> RiskRule:
        cls = RULE_MAP.get(rule_type)
        if not cls:
            raise ValueError(f"Unknown rule type: {rule_type}")
        rule = cls()
        rule.params = params
        return rule

    async def evaluate(self, rule_model, order: dict, context: dict) -> tuple[bool, str]:
        rule = self.create_rule(rule_model.rule_type, rule_model.params)
        return await rule.evaluate(order, context)
```

---

## 14. 事件总线设计

```python
# app/core/events.py
import json
import redis.asyncio as aioredis
from app.config import get_settings
from typing import Callable, Any


class EventBus:
    def __init__(self):
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._handlers: dict[str, list[Callable]] = {}
        self._listener_task = None

    async def connect(self):
        settings = get_settings()
        self._redis = aioredis.from_url(settings.REDIS_URL)
        self._pubsub = self._redis.pubsub()
        self._listener_task = asyncio.create_task(self._listen())

    async def disconnect(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()

    async def publish(self, topic: str, data: dict):
        await self._redis.publish(topic, json.dumps(data, default=str))

    async def subscribe(self, topic: str, handler: Callable[[dict], Any]):
        if topic not in self._handlers:
            self._handlers[topic] = []
            await self._pubsub.subscribe(topic)
        self._handlers[topic].append(handler)

    async def unsubscribe(self, topic: str, handler: Callable | None = None):
        if handler and topic in self._handlers:
            self._handlers[topic] = [h for h in self._handlers[topic] if h != handler]
        else:
            self._handlers.pop(topic, None)
            await self._pubsub.unsubscribe(topic)

    async def _listen(self):
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                topic = message["channel"]
                if isinstance(topic, bytes):
                    topic = topic.decode()
                data = json.loads(message["data"])
                for handler in self._handlers.get(topic, []):
                    try:
                        result = handler(data)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.error(f"Event handler error: {topic} - {e}")


event_bus = EventBus()
```

---

## 15. 认证与鉴权

### 15.1 Auth Service

```python
# app/services/auth_service.py
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import get_settings


class AuthService:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @classmethod
    def hash_password(cls, password: str) -> str:
        return cls.pwd_context.hash(password)

    @classmethod
    def verify_password(cls, plain: str, hashed: str) -> bool:
        return cls.pwd_context.verify(plain, hashed)

    @classmethod
    def create_access_token(cls, user_id: str, role: str) -> str:
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {"sub": user_id, "role": role, "exp": expire, "type": "access"}
        with open(settings.JWT_PRIVATE_KEY_PATH) as f:
            private_key = f.read()
        return jwt.encode(payload, private_key, algorithm=settings.JWT_ALGORITHM)

    @classmethod
    def create_refresh_token(cls, user_id: str) -> str:
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        payload = {"sub": user_id, "exp": expire, "type": "refresh"}
        with open(settings.JWT_PRIVATE_KEY_PATH) as f:
            private_key = f.read()
        return jwt.encode(payload, private_key, algorithm=settings.JWT_ALGORITHM)

    @classmethod
    def decode_token(cls, token: str) -> dict | None:
        settings = get_settings()
        try:
            with open(settings.JWT_PUBLIC_KEY_PATH) as f:
                public_key = f.read()
            payload = jwt.decode(
                token, public_key, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            return None
```

### 15.2 API Key 加密

```python
# app/core/security.py
from cryptography.fernet import Fernet
from app.config import get_settings


class Encryption:
    _fernet: Fernet | None = None

    @classmethod
    def _get_fernet(cls) -> Fernet:
        if cls._fernet is None:
            settings = get_settings()
            cls._fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        return cls._get_fernet().encrypt(plaintext.encode()).decode()

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        return cls._get_fernet().decrypt(ciphertext.encode()).decode()

    @classmethod
    def mask(cls, value: str) -> str:
        if len(value) <= 8:
            return "****"
        return value[:4] + "****" + value[-4:]
```

---

## 16. 后台任务调度

### 16.1 调度器配置

```python
# 使用 APScheduler AsyncIOScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


scheduler = AsyncIOScheduler(
    job_defaults={
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 60,
    }
)

# 注册任务
scheduler.add_job(
    collect_a_stock_realtime,
    CronTrigger(minute="*/5", hour="9-15", day_of_week="mon-fri"),
    id="collect_a_stock_realtime",
    replace_existing=True,
)

scheduler.add_job(
    collect_crypto_klines,
    IntervalTrigger(minutes=1),
    id="collect_crypto_klines",
    replace_existing=True,
)

scheduler.add_job(
    sync_positions_from_broker,
    IntervalTrigger(minutes=5),
    id="sync_positions",
    replace_existing=True,
)

scheduler.add_job(
    reset_daily_risk_counters,
    CronTrigger(hour=0, minute=0),
    id="reset_daily_risk",
    replace_existing=True,
)

scheduler.add_job(
    cleanup_old_logs,
    CronTrigger(hour=2, minute=0),
    id="cleanup_logs",
    replace_existing=True,
)
```

---

## 17. 日志系统

```python
# app/utils/logger.py
import structlog
import logging
from app.config import get_settings


def setup_logging():
    settings = get_settings()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if settings.LOG_FORMAT == "json"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(message)s",
    )
```

**日志规范**:

| 模块 | logger name | 说明 |
|------|-------------|------|
| API 请求 | `api` | 请求路径、状态码、耗时 |
| 数据采集 | `market.collector` | 采集任务状态、数据量 |
| 策略引擎 | `strategy.engine` | 策略加载、运行、异常 |
| 交易执行 | `trade.executor` | 下单、撤单、成交 |
| 风控引擎 | `risk.manager` | 规则检查、拦截、告警 |
| 回测引擎 | `backtest` | 回测进度、统计结果 |

---

## 18. 错误处理

### 18.1 自定义异常

```python
# app/core/exceptions.py
from fastapi import HTTPException, status


class AppException(Exception):
    def __init__(self, code: int, message: str, detail: str = ""):
        self.code = code
        self.message = message
        self.detail = detail


class StrategyLoadError(AppException):
    def __init__(self, detail: str):
        super().__init__(400, "策略加载失败", detail)


class InsufficientFundsError(AppException):
    def __init__(self):
        super().__init__(400, "资金不足")


class RiskCheckFailedError(AppException):
    def __init__(self, reason: str):
        super().__init__(403, "风控拦截", reason)


class MarketClosedError(AppException):
    def __init__(self, market: str):
        super().__init__(400, "市场未开盘", f"{market} 市场当前不在交易时段")


class OrderNotFoundError(AppException):
    def __init__(self, order_id: str):
        super().__init__(404, "订单不存在", order_id)
```

### 18.2 全局异常处理器

```python
# app/main.py 中注册
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.exceptions import AppException


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
    logger.exception("Unhandled exception", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "Internal Server Error"},
    )
```

---

## 19. 测试策略

### 19.1 测试分层

```
tests/
├── conftest.py           # 全局 fixtures（测试DB、测试客户端、mock用户）
├── unit/                 # 单元测试
│   ├── test_loader.py    # 策略加载器
│   ├── test_simulator.py # 模拟撮合引擎
│   ├── test_risk_rules.py # 风控规则
│   └── test_statistics.py # 统计计算
├── integration/          # 集成测试
│   ├── test_auth_api.py  # 认证API
│   ├── test_strategy_api.py # 策略CRUD
│   ├── test_trade_api.py # 交易API
│   └── test_backtest.py  # 回测全流程
└── e2e/                  # 端到端测试
    └── test_full_flow.py # 完整交易流程
```

### 19.2 测试 Fixtures

```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.database import get_db
from app.models.base import Base


TEST_DB_URL = "postgresql+asyncpg://quant:quant@localhost:5432/quant_test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    async with async_sessionmaker(test_engine)() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_token(client):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "password": "Test1234",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "Test1234",
    })
    return resp.json()["data"]["access_token"]
```

### 19.3 覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| 策略加载器 | ≥ 90% |
| 模拟撮合引擎 | ≥ 95% |
| 风控规则 | ≥ 90% |
| 回测统计 | ≥ 90% |
| API 端点 | ≥ 80% |
| 认证鉴权 | ≥ 85% |
| **整体** | **≥ 70%** |
