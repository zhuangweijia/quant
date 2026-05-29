# Tasks: Fix Deployment Gaps

## Phase 1: 安全基础设施（必须先完成）

### Task 1.1 — 创建环境初始化脚本
- [x] 新建 `scripts/setup-env.sh`
- [x] 检测 `.env` 中的占位符值
- [x] 自动生成 `POSTGRES_PASSWORD`（`openssl rand -hex 32`）
- [x] 自动生成 `ENCRYPTION_KEY`（Fernet key）
- [x] 自动生成 `REDIS_PASSWORD`
- [x] 生成默认 `ADMIN_USERNAME`（admin）和 `ADMIN_PASSWORD`
- [x] 设置 `CORS_ORIGINS` 为 `http://<server-ip>:3000`
- [x] 保留用户已自定义的值不变
- [x] 设置脚本可执行权限

### Task 1.2 — 更新 `.env.example`
- [x] 增加 `REDIS_PASSWORD` 字段
- [x] 增加 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD` 字段
- [x] 增加 `NGINX_SSL_ENABLED` 字段（默认 false）

### Task 1.3 — 运行 `setup-env.sh` 初始化 `.env`
- [x] 执行脚本生成真实密钥
- [x] 验证 `.env` 中无 `CHANGE_ME` 占位符

---

## Phase 2: Docker Compose 安全加固

### Task 2.1 — Redis 认证配置
- [x] 修改 `docker-compose.yml` Redis service：增加 `command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes`
- [x] 修改 Redis healthcheck 使用 `redis-cli -a $REDIS_PASSWORD --no-auth-warning ping`
- [x] 修改 backend 环境变量 `REDIS_URL` 为 `redis://:${REDIS_PASSWORD}@redis:6379/0`

### Task 2.2 — 网络隔离
- [x] 在 `docker-compose.yml` 底部定义两个网络：`frontend-net` 和 `backend-net`
- [x] frontend: 仅加入 `frontend-net`
- [x] backend: 加入 `frontend-net` + `backend-net`
- [x] postgres: 仅加入 `backend-net`
- [x] redis: 仅加入 `backend-net`

### Task 2.3 — Backend 端口不对外暴露
- [x] `docker-compose.yml` 中移除 backend 的 `ports: "8000:8000"`
- [x] 在 `docker-compose.prod.yml` 中确认不暴露 backend 端口
- [x] 注释说明开发调试时可通过 profile 临时暴露

---

## Phase 3: Nginx SSL 配置切换

### Task 3.1 — 修改 Frontend Dockerfile
- [x] 复制 `nginx.conf` 和 `nginx.ssl.conf` 到镜像
- [x] 新建 `frontend/entrypoint.sh`：根据 `NGINX_SSL_ENABLED` 环境变量选择配置
- [x] 若 `NGINX_SSL_ENABLED=true` 且证书文件存在，用 `nginx.ssl.conf` 替换默认配置
- [x] 否则使用 `nginx.conf`
- [x] Dockerfile ENTRYPOINT 改为 `entrypoint.sh`

### Task 3.2 — 更新 docker-compose.prod.yml
- [x] frontend 环境变量增加 `NGINX_SSL_ENABLED=true`

---

## Phase 4: 初始管理员创建

### Task 4.1 — 创建 init_admin.py 脚本
- [x] 新建 `backend/scripts/init_admin.py`
- [x] 使用 async SQLAlchemy 从 `DATABASE_URL` 连接数据库
- [x] 从环境变量读取 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD`
- [x] 检查该用户名是否已存在，不存在则创建
- [x] 使用 `bcrypt` 加密密码
- [x] 脚本幂等（重复运行不报错）

### Task 4.2 — 更新 backend Dockerfile 和 entrypoint
- [x] `backend/Dockerfile` 中 COPY `scripts` 目录
- [x] `backend/entrypoint.sh` 在 `alembic upgrade head` 之后调用 `python scripts/init_admin.py`

### Task 4.3 — 传递 admin 环境变量
- [x] `docker-compose.yml` backend 环境变量增加 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD`

---

## Phase 5: 健康检查增强

### Task 5.1 — 增强 /health 端点
- [x] 修改 `backend/app/main.py` 的 `/health`
- [x] 增加 DB 连通性检查（`SELECT 1`）
- [x] 增加 Redis 连通性检查（`PING`）
- [x] 全部正常返回 `{"status": "ok", "db": "ok", "redis": "ok"}`
- [x] 任一失败返回 HTTP 503 + 对应错误信息

---

## Phase 6: 资源适配

### Task 6.1 — 调整生产环境内存限制
- [x] `docker-compose.prod.yml` backend: memory 512M limit, 128M reservation
- [x] postgres: memory 256M limit
- [x] redis: memory 128M limit
- [x] frontend: memory 128M limit

### Task 6.2 — 创建 Swap 设置脚本
- [x] 新建 `scripts/setup-swap.sh`
- [x] 检测是否已有 swap（`swapon --show`）
- [x] 创建 2GB swap 文件（`fallocate -l 2G /swapfile`）
- [x] 设置权限 600，格式化，启用
- [x] 设置 `vm.swappiness=10`
- [x] 写入 `/etc/fstab` 持久化

---

## Phase 7: 备份持久化

### Task 7.1 — 备份目录 volume 挂载
- [x] `docker-compose.yml` postgres 增加 bind mount: `./backups:/backups`
- [x] 项目根目录创建 `.gitkeep` 在 `backups/` 目录

---

## Phase 8: Makefile 与便捷脚本

### Task 8.1 — 创建 Makefile
- [x] `make setup` — 运行 setup-env.sh
- [x] `make setup-swap` — 运行 setup-swap.sh（需要 root）
- [x] `make up` — `docker compose up -d --build`
- [x] `make up-prod` — `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
- [x] `make down` — `docker compose down`
- [x] `make logs` — `docker compose logs -f`
- [x] `make backup` — 执行 `scripts/backup.sh`
- [x] `make restore FILE=<file>` — 执行 `scripts/restore.sh`
- [x] `make rebuild` — `docker compose down && docker compose up -d --build`
- [x] `make status` — 查看服务状态 + 健康检查
- [x] `make clean` — `docker compose down -v`（带确认提示）

---

## 验收标准

1. `make setup && make up` 可一键启动所有服务
2. `docker compose ps` 显示所有 4 个服务 healthy
3. 访问 `http://<server-ip>:3000` 可看到登录页面
4. 使用 `.env` 中的 admin 凭据可成功登录
5. `docker network inspect` 确认 frontend 无法直连 postgres/redis
6. Redis 需要密码认证
7. Backend 8000 端口未暴露到宿主机
8. `make backup` 可成功创建数据库备份到 `backups/` 目录
