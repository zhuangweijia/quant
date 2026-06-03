## Why

系统当前无法正常使用：管理员无法登录（密码 5 位但登录接口要求 8 位）、券商配置保存后解密失败（ENCRYPTION_KEY 未配置导致加密静默降级为明文存储、读取时返回密文乱码）、前端券商 UI 缺少选择器（只能展示第一个 broker）。这三个问题形成连锁阻塞，系统处于不可用状态。

## What Changes

- 修复 `ENCRYPTION_KEY` 环境变量配置缺失：确保 `backend/.env` 包含有效的 Fernet key
- 修复 admin 初始密码与登录接口的 min_length 约束不一致：将默认密码改为 `Admin@2024`（8 位+大小写+特殊字符）
- 消除加密/解密的静默失败：加密失败直接报错，解密失败返回 null 并记录 error 日志
- 应用启动时校验关键配置（ENCRYPTION_KEY、JWT keys、数据库连接），并尝试解密已有记录验证 key 有效性，缺失时拒绝启动
- 前端券商配置页增加券商选择器（Binance / Alpaca / AKShare），支持切换和分别配置
- 修复前端表单读取已保存配置时的字段映射错误（api_secret 后端不返回但前端试图读取）
- AKShare 测试连接改为轻量级实际网络请求（指数行情接口）而非仅检查 import
- 密码重置脚本增加安全保护：仅重置已知弱默认密码，支持 `--force` 参数

## Capabilities

### New Capabilities
- `startup-validation`: 应用启动时校验关键配置项，缺失或不合法时拒绝启动并给出明确错误信息

### Modified Capabilities

## Impact

- **后端配置**: `backend/.env` 需补充 `ENCRYPTION_KEY`
- **后端代码**: `settings_service.py`（加密错误处理）、`security.py`（移除静默降级）、`config.py` / `main.py`（启动校验）、`scripts/init_admin.py`（默认密码）
- **前端代码**: `SettingsView.vue`（券商选择器 + 表单逻辑修复）
- **数据库**: 已有加密数据（`broker:binance` 的 api_key/api_secret）使用当前 key 可正常解密，无需迁移
- **API 行为**: 加密操作失败时从静默降级改为返回 500 错误
