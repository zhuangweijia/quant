# StockAnalysis

A股AI选股分析平台 — 基于沪深300成分股，使用 LightGBM 多因子模型每日输出选股排名。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL + Redis |
| 前端 | Vue 3 + TypeScript + Vite + Tailwind CSS + ECharts |
| 数据源 | AKShare (A股日K线 / 基本面 / 北向资金) |
| ML | LightGBM + SHAP + pandas-ta |
| 部署 | Docker Compose |

## 功能模块

- **看板 (Dashboard)** — Pipeline 状态、今日强推 Top 10、市场概览
- **排名表 (Ranking)** — 全市场评分排名（强推/关注/观望/回避），支持标签筛选和分页
- **个股详情 (Stock Detail)** — 评分明细、SHAP 因素拆解（大白话）、K线图、基本面、北向资金
- **模型管理 (Model)** — 模型训练、激活、版本列表、分组回测验证
- **分析 Pipeline** — 收盘后自动执行：数据同步 → 特征计算 → 模型预测 → SHAP解释 → 排名生成
- **行情 (Market)** — 股票搜索、K线图（简化版）

## 分析引擎架构

```
每日收盘后:
  数据同步 (AKShare → PostgreSQL)
       ↓
  特征计算 (6大类 ~30个因子: 动量/估值/质量/成长/量价/技术/资金流)
       ↓
  LightGBM 预测 (跨截面收益预测 → 评分 0~1)
       ↓
  SHAP 解释 (Top3 正向 + Top2 负向因素 → 大白话)
       ↓
  排名生成 (Top10% 强推 / Bottom10% 回避)
```

## 快速开始

### 环境要求

- Python >= 3.11
- Node.js >= 18
- Docker & Docker Compose
- PostgreSQL 16
- Redis 7

### 使用 Docker Compose 启动

```bash
docker compose up -d
```

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/api/docs

### 首次配置与推荐生成

使用管理员账户登录后，在看板点击「一键初始化并生成推荐」。系统会依次同步沪深 300 成分股、历史行情和基本面数据，校验数据质量，训练并激活模型，然后生成首批推荐。该过程通常需要 30–60 分钟；刷新或离开页面不会丢失已持久化的进度，失败后可点击「继续初始化」安全重试。

首次配置完成后，看板会显示系统已就绪。需要更新当天推荐时，点击「运行今日分析」即可；如果模型当天没有筛出符合条件的强推股票，页面会明确显示正常的空结果，而不会提示 Pipeline 失败。

命令行环境仍可在 `backend/` 运行：

```bash
cd backend
python scripts/bootstrap_data.py
```

该命令与页面使用同一套可恢复的 SetupPipeline。

## 项目结构

```
quant/
├── docker-compose.yml
├── backend/
│   ├── pyproject.toml
│   ├── alembic/             # 数据库迁移
│   ├── scripts/
│   │   └── bootstrap_data.py  # 首次数据拉取
│   ├── models/              # LightGBM 模型文件
│   └── app/
│       ├── main.py          # 应用入口
│       ├── config.py        # 配置
│       ├── api/v1/          # REST API 路由
│       ├── ws/              # WebSocket
│       ├── models/          # SQLAlchemy 模型
│       ├── schemas/         # Pydantic Schema
│       └── services/        # 业务逻辑
│           ├── data_sync_service.py     # AKShare 数据同步
│           ├── feature_engine.py        # 特征工程
│           ├── ml_model.py              # LightGBM 训练/预测/SHAP
│           ├── ranking_service.py       # 排名生成
│           ├── model_validation_service.py  # 回测验证
│           └── analysis_pipeline.py     # 每日 Pipeline 编排
└── frontend/
    └── src/
        ├── views/
        │   ├── dashboard/    # 看板
        │   ├── ranking/      # 排名表
        │   ├── stock-detail/ # 个股详情
        │   ├── model/        # 模型管理
        │   ├── market/       # 行情
        │   └── settings/     # 设置
        ├── api/              # API 封装
        └── router/           # 路由
```

### 配置

主要配置项（`.env`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | 数据库连接 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 |
| `STOCK_UNIVERSE` | `csi300` | 股票池 |
| `ANALYSIS_TIME` | `17:00` | Pipeline 执行时间 |
| `MODEL_DIR` | `models` | 模型文件目录 |
| `FORWARD_RETURN_DAYS` | `5` | 标签预测窗口 |
| `MODEL_IC_THRESHOLD` | `0.02` | 激活门禁 IC 阈值 |

## License

Private
