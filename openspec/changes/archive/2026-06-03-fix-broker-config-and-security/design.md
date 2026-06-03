## Context

QuantPlatform 的券商配置链路当前处于不可用状态，涉及三层问题：

1. **配置层**：`backend/.env` 缺少 `ENCRYPTION_KEY`，导致加密/解密全部失败
2. **服务层**：`settings_service.py` 用 `try/except` 静默吞掉加解密异常，明文和密文在数据库中混淆
3. **UI 层**：前端券商页面只展示第一个 broker（binance），无法切换；`api_secret` 字段后端不返回但前端试图读取，导致表单状态异常
4. **认证层**：`init_admin.py` 默认密码 `admin`（5 位）不满足 `LoginRequest.password` 的 `min_length=8` 约束，管理员无法登录

数据库中已有两条用正确 `ENCRYPTION_KEY`（根 `.env` 中的 `4R8vxhKn...`）加密的 Fernet 密文记录，经验证可正常解密，无需数据迁移。

## Goals / Non-Goals

**Goals:**
- 管理员能够正常登录系统
- 券商 API Key/Secret 能够加密保存、正确解密读取
- 测试连接能够使用真实的 API 凭证执行真实的连通性检查
- 前端能切换和配置所有三种券商（Binance / Alpaca / AKShare）
- 关键配置缺失时应用拒绝启动，而非带着病态配置运行

**Non-Goals:**
- 不重新设计加密架构（继续使用 Fernet 对称加密）
- 不修改用户认证流程的核心逻辑（只修密码约束和初始密码）
- 不引入新的券商适配器
- 不做 API 接口版本升级或 breaking change

## Decisions

### D1: ENCRYPTION_KEY 配置策略 — 写入 backend/.env

**选择**：将根 `.env` 的 `ENCRYPTION_KEY` 值复制到 `backend/.env`

**备选方案**：
- A) 改 `config.py` 的 `env_file` 指向根 `.env` — 影响范围大，可能引入其他环境变量冲突
- B) 启动脚本中 `set -a; source ../.env; set +a` — 依赖运行方式，不可靠

**理由**：最简单直接，本地开发和 Docker 环境各自维护自己的 `.env`，符合 pydantic-settings 的惯例。

### D2: 加解密失败处理 — 抛异常而非静默降级

**选择**：
- `Encryption.encrypt()` 在 `ENCRYPTION_KEY` 为空时抛 `ValueError`（现有行为，保持）
- `settings_service.set_setting()` 不再 try/catch 加密异常，让异常传播到 API 层返回 500
- `settings_service.get_settings_category()` 解密失败时返回 `None` 并记录 `error` 级别日志

**备选方案**：
- A) 解密失败时返回空字符串 `""` — 无法区分"未设置"和"数据损坏"
- B) 解密失败时返回密文字符串 — 当前行为，会导致下游拿乱码当 api_key

**理由**：返回 `None` 让调用方知道数据有问题，同时不会把乱码传递给 broker 适配器。

### D3: Admin 密码修复 — 更改默认密码 + 重置已有账户

**选择**：
- `init_admin.py` 默认密码改为 `Admin@2024`（满足 8 位 + 包含大小写和特殊字符）
- 新增一个一次性脚本 `scripts/reset_admin_password.py`，仅当用户当前密码为已知弱默认值（`admin`、`admin123`）时才重置；若已被手动修改则跳过。支持 `--force` 参数强制重置
- 首次登录后前端提示修改默认密码（非强制，仅 toast 提醒）

**备选方案**：
- A) 降低 `LoginRequest.password` 的 `min_length` — 安全倒退
- B) 在 `init_admin.py` 中检测密码长度不足时自动补齐 — 增加隐式行为
- C) 使用 `admin123` 作为默认密码 — 仍为弱密码，生产环境有风险

**理由**：保持密码策略不变，修复源头（默认密码）并修复存量数据。`--force` 参数避免误覆盖已手动设置的强密码。

### D4: 启动校验 — 在 FastAPI lifespan 中校验

**选择**：在 `main.py` 的 `lifespan` context manager 中，**在 `init_db()` 之后**调用 `validate_config()` 函数，校验 ENCRYPTION_KEY（含尝试解密一条已有记录）、JWT keys、数据库连接。

**执行顺序**：`init_db()` → `validate_config()` → `event_bus.connect()` → 其他初始化

**备选方案**：
- A) 单独的 `healthcheck` 端点 — 太晚，应用已经启动了
- B) 在 `config.py` 的 `get_settings()` 中校验 — 缓存后只执行一次，但缺少文件/连接类校验

**理由**：lifespan 是 FastAPI 推荐的启动钩子，可以访问异步资源（数据库连接），校验失败时 `sys.exit(1)` 阻止应用启动。放在 `init_db()` 之后确保 DB 连接可用于解密验证。

### D5: 前端券商选择器 — 在现有卡片内增加 Select 组件

**选择**：在券商配置卡片顶部增加 `UiSelect` 下拉框，选项为 Binance / Alpaca / AKShare，切换时加载对应配置填入表单。

**理由**：后端已支持三种券商的 CRUD，只缺前端切换入口。复用现有 UI 组件库。

## Risks / Trade-offs

- **[已有加密数据兼容性]** → 已验证当前 ENCRYPTION_KEY 可解密 DB 中的密文，无风险。但如果 key 被更换，已有数据将永久丢失。启动校验中增加"尝试解密一条已有加密记录"的检查（已纳入 Task 3.1），确保 key 与存量数据匹配。
- **[启动校验过严]** → 如果某些开发场景需要不带 ENCRYPTION_KEY 启动（纯前端开发），校验会阻止。可通过环境变量 `SKIP_CONFIG_VALIDATION=true` 跳过。
- **[admin 密码重置脚本]** → 需要数据库连接，如果数据库不可用会失败。脚本应处理这种情况并给出清晰错误信息。加入 `--force` 保护机制防止误覆盖已设置的强密码。
- **[解密返回 None 的下游兼容]** → `get_settings_category()` 解密失败返回 `None` 后，调用方（如 `broker_factory.py`）使用 `config.get("api_key", "")` 取值，`None` 与 `""` 均可通过 `if not api_key` 检查。但需确保无调用方对返回值执行 `.strip()` 等 str 方法，否则会抛 AttributeError。
