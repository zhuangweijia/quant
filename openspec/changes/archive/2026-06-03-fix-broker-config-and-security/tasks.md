## 1. 环境配置修复

- [x] 1.1 将根 `.env` 中的 `ENCRYPTION_KEY` 值写入 `backend/.env`，确保后端能加载到有效的 Fernet key
- [x] 1.2 `scripts/init_admin.py` 将默认密码从 `admin` 改为 `Admin@2024`（满足 8 位 + 大小写 + 特殊字符）
- [x] 1.3 新建 `scripts/reset_admin_password.py` 脚本：检测当前 admin 密码是否为已知弱默认值（`admin`、`admin123`），若是则重置为 `ADMIN_PASSWORD` 环境变量值（默认 `Admin@2024`）；若已被手动修改则跳过并提示。支持 `--force` 参数强制重置

## 2. 加密/解密错误处理

- [x] 2.1 `app/core/security.py` 中 `Encryption._get_fernet()` 保持现有行为（ENCRYPTION_KEY 为空时抛 ValueError），不做修改
- [x] 2.2 `app/services/settings_service.py` 的 `set_setting()` 移除加密的 try/except，让加密异常直接传播到调用方
- [x] 2.3 `app/services/settings_service.py` 的 `get_settings_category()` 解密失败时将对应 key 设为 `None` 而非密文字符串，并将日志级别从隐式提升为 `error`
- [x] 2.4 排查所有 `get_settings_category()` 的调用方（`broker_factory.py`、`notification_service.py` 等），确保对返回值为 `None` 的情况不会调用 str 方法（如 `.strip()`、`.split()`），必要时加 `or ""` 兜底

## 3. 应用启动校验

- [x] 3.1 在 `app/core/` 下新建 `validation.py`，实现 `validate_config()` 异步函数，校验：ENCRYPTION_KEY（构造 Fernet）、JWT key 文件存在性、数据库连接、尝试解密一条已有加密记录（若存在）验证 key 与存量数据匹配
- [x] 3.2 `app/main.py` 的 `lifespan` 中，**在 `init_db()` 之后** 调用 `validate_config()`，校验失败时 `sys.exit(1)`；支持 `SKIP_CONFIG_VALIDATION=true` 跳过

## 4. 前端券商 UI 修复

- [x] 4.1 `SettingsView.vue` 券商配置卡片顶部增加 `UiSelect` 下拉框，选项为 Binance / Alpaca / AKShare，绑定 `brokerName`
- [x] 4.2 切换券商时重新从 `brokersData` 加载对应 broker 的配置到表单（api_key、has_secret、params 等）
- [x] 4.3 修复 `watch(brokersData)` 中的字段映射：`api_secret` 字段后端不返回，表单初始化时应清空而非读取 `d[0].api_secret`
- [x] 4.4 AKShare 选中时将 API Key/Secret 输入框标记为"可选"（非禁用），并显示说明文字"AKShare 基础功能无需凭证"
- [x] 4.5 `saveBroker()` 提交时发送当前选中的 `brokerName` 而非硬编码值
- [x] 4.6 `testBrokerConnection()` 提交时使用当前选中的 `brokerName`

## 5. AKShare 测试连接改进

- [x] 5.1 `broker_factory.py` 中 AKShare 的 `test_broker_connection` 改为实际调用轻量级接口（如 `ak.stock_zh_index_spot_em()` 取前 1 条），设置 10 秒超时，确认网络可达，`ImportError` 或网络错误均返回失败
