# QuantPlatform

多市场量化交易平台 — 支持 A 股、美股、加密货币的策略开发、回测、模拟盘/实盘交易。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL + Redis |
| 前端 | Vue 3 + TypeScript + Vite + Tailwind CSS + ECharts |
| 交易 | PaperBroker / Alpaca (美股) / Binance (加密货币) |
| 行情 | AKShare (A股) / Alpaca Market Data / Binance WebSocket |
| 部署 | Docker Compose |

## 功能模块

- **看板 (Dashboard)** — 总资产、权益曲线、日盈亏、持仓分布、策略表现
- **行情中心** — K 线图、实时报价、自选股、多时间周期、技术指标叠加
- **策略管理** — 策略 CRUD、策略执行引擎、代码编辑器、策略模板、运行日志
- **回测引擎** — 加载用户策略代码、模拟撮合、收益/回撤/夏普等指标、可视化报告
- **交易系统** — 手动/策略自动下单、订单管理、持仓查询、券商适配器
- **风控系统** — 止损/止盈、持仓限额、日亏损限制、自动强平、告警通知
- **系统设置** — 券商 API 配置、交易模式切换、通知配置、参数管理
- **实时通信** — WebSocket 推送行情、订单、持仓、风控告警

## 项目结构

```
quant/
├── docker-compose.yml
├── backend/                 # FastAPI 后端
│   ├── pyproject.toml
│   ├── alembic/             # 数据库迁移
│   └── app/
│       ├── main.py          # 应用入口
│       ├── config.py        # 配置
│       ├── database.py      # 数据库连接
│       ├── api/v1/          # REST API 路由
│       ├── ws/              # WebSocket
│       ├── models/          # SQLAlchemy 模型
│       ├── schemas/         # Pydantic Schema
│       ├── services/        # 业务逻辑
│       └── core/            # 事件总线、异常、类型
└── frontend/                # Vue 3 前端
    ├── package.json
    └── src/
        ├── views/           # 页面
        ├── components/      # 组件
        ├── stores/          # Pinia 状态管理
        ├── api/             # API 封装
        └── router/          # 路由
```

## 快速开始

### 环境要求

- Python >= 3.11
- Node.js >= 18
- Docker & Docker Compose
- PostgreSQL 16
- Redis 7

### 使用 Docker Compose 一键启动

```bash
docker compose up -d
```

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/api/docs

### 本地开发

**后端**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev,all-market]"
cp .env.example .env   # 编辑配置
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

### 配置

后端配置通过环境变量或 `.env` 文件注入，主要配置项：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://quant:quant@localhost:5432/quant` | 数据库连接 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 |
| `TRADING_MODE` | `paper` | 交易模式 (paper / live) |
| `JWT_PRIVATE_KEY_PATH` | `keys/private.pem` | JWT RSA 私钥 |
| `JWT_PUBLIC_KEY_PATH` | `keys/public.pem` | JWT RSA 公钥 |
| `ENCRYPTION_KEY` | — | API Key 加密密钥 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

## API 文档

启动后端后访问：

- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`

## 开发规范

- **后端**: Python 3.11+、async/await、Ruff 格式化、structlog 结构化日志
- **前端**: Vue 3 Composition API + `<script setup>`、TypeScript strict mode
- **Git**: `type(scope): message` 格式，如 `feat(strategy): add MA crossover strategy`
- **数据库变更**: 使用 Alembic 管理迁移

## License

Private
