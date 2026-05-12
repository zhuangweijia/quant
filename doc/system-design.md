# QuantPlatform 量化交易系统设计文档

## 一、系统概览

- **名称**: QuantPlatform
- **定位**: 多市场（A股 / 美股 / 加密货币）全功能量化交易平台
- **技术栈**: FastAPI + Vue3 + PostgreSQL + Redis + Docker
- **部署策略**: 本地开发 → Docker Compose → 云服务器部署

---

## 二、系统架构

```
┌─────────────────────────────────────────────────┐
│                  Vue3 Frontend                   │
│  (Dashboard / Strategy / Backtest / Trade / ...) │
└──────────────────────┬──────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────┴──────────────────────────┐
│                FastAPI Gateway                    │
├──────────┬──────────┬──────────┬────────────────┤
│ Market   │ Strategy │ Trade    │ Risk           │
│ Data     │ Engine   │ Engine   │ Manager        │
│ Service  │ Service  │ Service  │ Service        │
├──────────┴──────────┴──────────┴────────────────┤
│   PostgreSQL        │        Redis               │
│  (业务数据)          │  (缓存/消息/实时行情)       │
└─────────────────────┴───────────────────────────┘
```

---

## 三、项目目录结构

```
quant/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic/
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── strategy.py
│   │   │   ├── order.py
│   │   │   ├── position.py
│   │   │   └── market_data.py
│   │   ├── schemas/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── market.py
│   │   │   │   ├── strategy.py
│   │   │   │   ├── backtest.py
│   │   │   │   ├── trade.py
│   │   │   │   ├── risk.py
│   │   │   │   └── dashboard.py
│   │   │   └── ws/
│   │   │       ├── market_ws.py
│   │   │       └── trade_ws.py
│   │   ├── services/
│   │   │   ├── market/
│   │   │   │   ├── collector.py
│   │   │   │   ├── providers/
│   │   │   │   │   ├── akshare_provider.py
│   │   │   │   │   ├── alpaca_provider.py
│   │   │   │   │   └── binance_provider.py
│   │   │   │   └── base.py
│   │   │   ├── strategy/
│   │   │   │   ├── engine.py
│   │   │   │   ├── backtest_engine.py
│   │   │   │   ├── loader.py
│   │   │   │   └── scheduler.py
│   │   │   ├── trade/
│   │   │   │   ├── executor.py
│   │   │   │   ├── brokers/
│   │   │   │   │   ├── xtquant_broker.py
│   │   │   │   │   ├── alpaca_broker.py
│   │   │   │   │   └── binance_broker.py
│   │   │   │   └── order_manager.py
│   │   │   └── risk/
│   │   │       ├── manager.py
│   │   │       ├── position_sizer.py
│   │   │       └── monitor.py
│   │   ├── core/
│   │   │   ├── events.py
│   │   │   ├── types.py
│   │   │   └── exceptions.py
│   │   └── utils/
│   │       ├── logger.py
│   │       └── decorators.py
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/
│   │   ├── stores/
│   │   │   ├── auth.ts
│   │   │   ├── market.ts
│   │   │   ├── strategy.ts
│   │   │   ├── trade.ts
│   │   │   └── dashboard.ts
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── market.ts
│   │   │   ├── strategy.ts
│   │   │   ├── backtest.ts
│   │   │   └── trade.ts
│   │   ├── composables/
│   │   │   ├── useWebSocket.ts
│   │   │   └── useChart.ts
│   │   ├── views/
│   │   │   ├── Dashboard.vue
│   │   │   ├── Market.vue
│   │   │   ├── StrategyList.vue
│   │   │   ├── StrategyEdit.vue
│   │   │   ├── Backtest.vue
│   │   │   ├── Trade.vue
│   │   │   ├── Risk.vue
│   │   │   └── Settings.vue
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   ├── KlineChart.vue
│   │   │   │   ├── PnlChart.vue
│   │   │   │   └── PositionPie.vue
│   │   │   ├── trade/
│   │   │   │   ├── OrderBook.vue
│   │   │   │   ├── OrderForm.vue
│   │   │   │   └── PositionTable.vue
│   │   │   └── common/
│   │   │       ├── Layout.vue
│   │   │       └── NavBar.vue
│   │   └── styles/
│   └── public/
└── strategies/
    ├── examples/
    │   ├── ma_cross.py
    │   ├── rsi_reversal.py
    │   └── grid_trading.py
    └── base_strategy.py
```

---

## 四、开发阶段规划

### Phase 1: 基础框架搭建（1-2周）

| 任务 | 说明 |
|------|------|
| 项目初始化 | FastAPI + Vue3 脚手架、Docker Compose |
| 数据库设计 | 建表（users, strategies, orders, positions, market_data, backtest_results） |
| 用户认证 | JWT 注册/登录，API 鉴权中间件 |
| 前端布局 | Layout、路由、导航栏、登录页 |

### Phase 2: 行情数据模块（1-2周）

| 任务 | 说明 |
|------|------|
| 数据源适配器 | AKShare（A股）、Alpaca（美股）、Binance（加密货币） |
| 数据采集服务 | 定时任务拉取 K线 / Tick，存入 PostgreSQL |
| WebSocket 推送 | 实时行情推送到前端 |
| 前端行情页 | K线图、实时报价表格 |

### Phase 3: 策略引擎与回测（2-3周）

| 任务 | 说明 |
|------|------|
| 策略基类 | 定义 `on_bar`、`on_tick`、`on_order` 等标准接口 |
| 策略加载器 | 动态加载用户编写的策略文件 |
| 回测引擎 | 事件驱动回测：历史数据回放 → 信号生成 → 模拟撮合 |
| 回测报告 | 收益曲线、夏普比率、最大回撤、交易明细 |
| 前端回测页 | 参数配置表单、回测结果图表展示 |

### Phase 4: 交易执行模块（2周）

| 任务 | 说明 |
|------|------|
| 券商适配器 | Binance（加密货币实盘）、Alpaca（美股）、XtQuant（A股模拟） |
| 订单管理 | 下单、撤单、订单状态跟踪 |
| 模拟盘交易 | Paper Trading 模式 |
| 前端交易页 | 下单面板、持仓表、订单历史、实时 WebSocket 更新 |

### Phase 5: 风控与策略调度（1-2周）

| 任务 | 说明 |
|------|------|
| 风控引擎 | 仓位上限、单笔止损、日亏损限额、黑名单检查 |
| 策略调度 | APScheduler 定时启停策略，多策略并行运行 |
| 告警通知 | 风控触发时 WebSocket 通知 + 可选邮件 / Webhook |
| 前端风控页 | 风控参数配置、实时告警展示 |

### Phase 6: Dashboard 与优化（1-2周）

| 任务 | 说明 |
|------|------|
| Dashboard 看板 | 总资产曲线、各策略 PnL 对比、持仓分布饼图 |
| 数据聚合 | 按日/周/月统计收益，策略排名 |
| 性能优化 | Redis 缓存热点数据、API 分页 |
| 前端细节 | 响应式布局、暗色主题 |

### Phase 7: 部署与文档（1周）

| 任务 | 说明 |
|------|------|
| Docker 化 | 各服务 Dockerfile、docker-compose.yml |
| CI/CD | GitHub Actions 自动测试 + 构建镜像 |
| 云部署 | 迁移到云服务器，Nginx 反向代理 |
| 使用文档 | 策略编写指南、API 文档、部署说明 |

**总开发周期: 10-14 周**

---

## 五、关键技术决策

| 领域 | 选型 | 理由 |
|------|------|------|
| 后端框架 | FastAPI | 异步高性能，自动生成 OpenAPI 文档 |
| 前端框架 | Vue3 + TypeScript | 响应式、组合式 API、类型安全 |
| UI 组件库 | Element Plus | 成熟的 Vue3 企业级组件库 |
| 图表 | ECharts | K线图、金融图表支持好 |
| 状态管理 | Pinia | Vue3 官方推荐，轻量 |
| ORM | SQLAlchemy 2.0 + Alembic | 异步支持，成熟的迁移工具 |
| 任务队列 | Celery + Redis / APScheduler | 定时任务和异步任务处理 |
| WebSocket | FastAPI 原生 WebSocket | 实时行情和交易推送 |
| 数据源-A股 | AKShare | 免费开源，覆盖全 |
| 数据源-美股 | Alpaca API | 免费行情 + 交易 |
| 数据源-加密货币 | Binance API | 流动性好，API 文档完善 |
| 认证 | JWT | 无状态，适合前后端分离 |

---

## 六、数据库核心表设计

### users

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| username | VARCHAR(64) | 用户名，唯一 |
| hashed_password | VARCHAR(256) | 密码哈希 |
| role | VARCHAR(16) | 角色（admin / user） |
| created_at | TIMESTAMP | 创建时间 |

### strategies

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键 → users |
| name | VARCHAR(128) | 策略名称 |
| code | TEXT | 策略源代码 |
| params | JSONB | 策略参数 |
| market | VARCHAR(16) | 市场（a_stock / us_stock / crypto） |
| status | VARCHAR(16) | 状态（draft / running / stopped） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### orders

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| strategy_id | UUID | 外键 → strategies |
| symbol | VARCHAR(32) | 标的代码 |
| side | VARCHAR(8) | 方向（buy / sell） |
| type | VARCHAR(16) | 订单类型（market / limit / stop） |
| qty | DECIMAL | 数量 |
| price | DECIMAL | 价格 |
| status | VARCHAR(16) | 状态（pending / filled / cancelled / rejected） |
| broker_order_id | VARCHAR(128) | 券商/交易所订单ID |
| filled_qty | DECIMAL | 已成交数量 |
| filled_price | DECIMAL | 成交均价 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### positions

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键 → users |
| strategy_id | UUID | 外键 → strategies |
| symbol | VARCHAR(32) | 标的代码 |
| qty | DECIMAL | 持仓数量 |
| avg_price | DECIMAL | 持仓均价 |
| market | VARCHAR(16) | 市场 |
| updated_at | TIMESTAMP | 更新时间 |

### market_data

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| symbol | VARCHAR(32) | 标的代码 |
| market | VARCHAR(16) | 市场 |
| timeframe | VARCHAR(8) | 周期（1m / 5m / 1h / 1d） |
| open | DECIMAL | 开盘价 |
| high | DECIMAL | 最高价 |
| low | DECIMAL | 最低价 |
| close | DECIMAL | 收盘价 |
| volume | DECIMAL | 成交量 |
| timestamp | TIMESTAMP | 数据时间 |

**索引**: `(symbol, market, timeframe, timestamp)` 联合索引

### backtest_results

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| strategy_id | UUID | 外键 → strategies |
| params | JSONB | 回测使用的参数 |
| start_date | DATE | 回测起始日 |
| end_date | DATE | 回测结束日 |
| total_return | DECIMAL | 总收益率 |
| annual_return | DECIMAL | 年化收益率 |
| sharpe_ratio | DECIMAL | 夏普比率 |
| max_drawdown | DECIMAL | 最大回撤 |
| win_rate | DECIMAL | 胜率 |
| trade_count | INT | 交易次数 |
| equity_curve | JSONB | 权益曲线数据 |
| trades | JSONB | 交易明细 |
| created_at | TIMESTAMP | 创建时间 |

### risk_rules

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键 → users |
| strategy_id | UUID | 外键 → strategies（NULL 表示全局规则） |
| rule_type | VARCHAR(32) | 规则类型（max_position / stop_loss / daily_limit / blacklist） |
| params | JSONB | 规则参数 |
| enabled | BOOLEAN | 是否启用 |

### alerts

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键 → users |
| strategy_id | UUID | 外键 → strategies |
| level | VARCHAR(8) | 级别（info / warning / error） |
| message | TEXT | 告警内容 |
| read | BOOLEAN | 是否已读 |
| created_at | TIMESTAMP | 创建时间 |

---

## 七、策略基类接口设计

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


@dataclass
class BarData:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: str


@dataclass
class TickData:
    symbol: str
    price: float
    volume: float
    timestamp: str


@dataclass
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: float
    price: Optional[float]
    status: str


@dataclass
class Trade:
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    qty: float
    price: float
    timestamp: str


class BaseStrategy(ABC):
    def __init__(self, params: dict):
        self.params = params
        self._context = None

    def set_context(self, context):
        self._context = context

    @abstractmethod
    def on_init(self, context) -> None:
        """策略初始化，加载指标参数等"""
        ...

    @abstractmethod
    def on_bar(self, bar: BarData) -> None:
        """K线数据回调，核心策略逻辑"""
        ...

    def on_tick(self, tick: TickData) -> None:
        """Tick 数据回调（可选覆写）"""
        pass

    def on_order(self, order: Order) -> None:
        """订单状态变更回调"""
        pass

    def on_trade(self, trade: Trade) -> None:
        """成交通知回调"""
        pass

    def on_stop(self, context) -> None:
        """策略停止回调（可选覆写）"""
        pass

    def buy(self, symbol: str, qty: float, price: float = None) -> str:
        """买入下单"""
        return self._context.send_order(
            symbol=symbol, side=OrderSide.BUY,
            order_type=OrderType.LIMIT if price else OrderType.MARKET,
            qty=qty, price=price
        )

    def sell(self, symbol: str, qty: float, price: float = None) -> str:
        """卖出下单"""
        return self._context.send_order(
            symbol=symbol, side=OrderSide.SELL,
            order_type=OrderType.LIMIT if price else OrderType.MARKET,
            qty=qty, price=price
        )

    def get_position(self, symbol: str) -> float:
        """查询当前持仓"""
        return self._context.get_position(symbol)

    def get_bars(self, symbol: str, length: int) -> list[BarData]:
        """获取历史K线"""
        return self._context.get_bars(symbol, length)

    def log(self, message: str):
        """记录日志"""
        self._context.log(message)
```

---

## 八、API 路由设计

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| GET | `/api/v1/auth/me` | 获取当前用户信息 |

### 行情

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/market/symbols` | 获取标的列表 |
| GET | `/api/v1/market/klines` | 获取K线数据 |
| GET | `/api/v1/market/ticks` | 获取Tick数据 |
| WS | `/ws/market/{symbol}` | 实时行情推送 |

### 策略

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/strategies` | 策略列表 |
| POST | `/api/v1/strategies` | 创建策略 |
| GET | `/api/v1/strategies/{id}` | 策略详情 |
| PUT | `/api/v1/strategies/{id}` | 更新策略 |
| DELETE | `/api/v1/strategies/{id}` | 删除策略 |
| POST | `/api/v1/strategies/{id}/start` | 启动策略 |
| POST | `/api/v1/strategies/{id}/stop` | 停止策略 |

### 回测

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/backtest/run` | 执行回测 |
| GET | `/api/v1/backtest/results` | 回测结果列表 |
| GET | `/api/v1/backtest/results/{id}` | 回测结果详情 |

### 交易

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/trade/order` | 手动下单 |
| DELETE | `/api/v1/trade/order/{id}` | 撤单 |
| GET | `/api/v1/trade/orders` | 订单列表 |
| GET | `/api/v1/trade/positions` | 当前持仓 |
| WS | `/ws/trade` | 交易状态实时推送 |

### 风控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/risk/rules` | 风控规则列表 |
| POST | `/api/v1/risk/rules` | 创建风控规则 |
| PUT | `/api/v1/risk/rules/{id}` | 更新风控规则 |
| DELETE | `/api/v1/risk/rules/{id}` | 删除风控规则 |
| GET | `/api/v1/risk/alerts` | 告警列表 |
| PUT | `/api/v1/risk/alerts/{id}/read` | 标记告警已读 |

### Dashboard

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/dashboard/overview` | 总览数据（总资产、日PnL等） |
| GET | `/api/v1/dashboard/equity-curve` | 权益曲线 |
| GET | `/api/v1/dashboard/strategy-ranking` | 策略排名 |

---

## 九、Docker Compose 服务编排

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql+asyncpg://quant:quant@postgres:5432/quant
      - REDIS_URL=redis://redis:6379/0

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: quant
      POSTGRES_PASSWORD: quant
      POSTGRES_DB: quant
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

---

## 十、开发规范

### 后端规范

- Python 3.11+，使用 `async/await` 异步编程
- 代码格式化: Ruff (formatter + linter)
- 类型注解: 所有函数必须有类型注解
- API 版本化: URL 前缀 `/api/v1/`
- 错误处理: 统一异常处理中间件，返回标准错误格式
- 日志: 结构化日志，使用 `structlog`

### 前端规范

- Vue3 Composition API + `<script setup>` 语法
- TypeScript strict mode
- 代码格式化: ESLint + Prettier
- 组件命名: PascalCase，文件名 PascalCase
- API 调用统一通过 `src/api/` 封装
- 状态管理使用 Pinia

### Git 规范

- 分支策略: `main` / `develop` / `feature/*` / `fix/*`
- Commit 格式: `type(scope): message`
  - type: feat / fix / docs / refactor / test / chore
  - 示例: `feat(strategy): add MA crossover strategy`
