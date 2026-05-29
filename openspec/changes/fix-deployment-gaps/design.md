# Design: Fix Deployment Gaps

## Overview

针对 proposal 中识别的 11 个问题，按安全、功能、资源、运维四个维度逐一设计修复方案。

---

## 1. 环境变量与密钥初始化

### 方案
创建 `scripts/setup-env.sh` 脚本：
- 检测 `.env` 是否仍为占位符
- 自动生成强随机密码（`openssl rand -hex 32`）
- 自动生成 Fernet 加密密钥（`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`）
- 设置合理的 `CORS_ORIGINS`（默认 `http://<server-ip>:3000`）
- 保留 `TRADING_MODE=paper` 作为安全默认值
- 写入 `.env` 文件

### 文件变更
- 新建 `scripts/setup-env.sh`
- 修改 `.env` — 脚本运行后填入真实值

---

## 2. Redis 认证

### 方案
- 在 `.env` 中增加 `REDIS_PASSWORD` 变量
- `docker-compose.yml` 中 Redis 启动命令改为 `redis-server --requirepass ${REDIS_PASSWORD}`
- `backend` 环境变量中 `REDIS_URL` 改为 `redis://:${REDIS_PASSWORD}@redis:6379/0`
- Redis healthcheck 改为 `redis-cli -a ${REDIS_PASSWORD} ping`（或使用 `--no-auth-warning`）

### 文件变更
- 修改 `docker-compose.yml` — Redis service command + healthcheck
- 修改 `.env` / `.env.example` — 增加 `REDIS_PASSWORD`

---

## 3. Docker 网络隔离

### 方案
定义两个网络：
- `frontend` — 仅 frontend 容器使用，可访问 backend
- `backend` — backend + postgres + redis 使用，前端不在此网络

这样 frontend 只能通过 backend 容器名访问 API，无法直连数据库。

### 文件变更
- 修改 `docker-compose.yml` — 增加 networks 定义，为每个 service 指定网络

---

## 4. Backend 端口不对外暴露

### 方案
- `docker-compose.yml` 中 backend 移除 `ports` 映射（只在 frontend 的 nginx 反代中访问）
- 开发需要调试时可通过 `docker compose port` 或临时映射

### 文件变更
- 修改 `docker-compose.yml` — 移除 backend `ports`（或仅在 dev profile 下暴露）

---

## 5. 生产环境 Nginx SSL 配置切换

### 方案
修改 `frontend/Dockerfile`：
- 同时复制 `nginx.conf` 和 `nginx.ssl.conf` 到镜像中
- 通过环境变量 `NGINX_SSL_ENABLED=true` 控制 entrypoint 脚本选择配置

新建 `frontend/entrypoint.sh`：
- 检测 `NGINX_SSL_ENABLED` 环境变量
- 若为 `true` 且 SSL 证书文件存在，替换默认 nginx 配置为 SSL 版本
- 否则使用 HTTP 配置
- 启动 nginx

`docker-compose.prod.yml` 中设置 `NGINX_SSL_ENABLED=true`。

### 文件变更
- 修改 `frontend/Dockerfile` — 复制两个配置 + entrypoint
- 新建 `frontend/entrypoint.sh` — 配置选择逻辑
- 修改 `docker-compose.prod.yml` — 增加 `NGINX_SSL_ENABLED` 环境变量

---

## 6. 初始管理员用户创建

### 方案
在 `backend/entrypoint.sh` 中增加初始化步骤：
- 调用新增的 `scripts/init_admin.py` 脚本
- 该脚本通过环境变量 `ADMIN_EMAIL` / `ADMIN_PASSWORD`（可选，有默认值）创建管理员账户
- 如果用户已存在则跳过（幂等）

新建 `backend/scripts/init_admin.py`：
- 使用 SQLAlchemy 直接操作数据库
- 从环境变量读取邮箱和密码
- 检查是否已存在，不存在则创建

### 文件变更
- 新建 `backend/scripts/init_admin.py`
- 修改 `backend/entrypoint.sh` — 调用 init_admin.py
- 修改 `backend/Dockerfile` — 复制 scripts 目录
- 修改 `.env` / `.env.example` — 增加 `ADMIN_EMAIL` / `ADMIN_PASSWORD`
- 修改 `docker-compose.yml` — 传递 admin 环境变量

---

## 7. 健康检查增强

### 方案
修改 `/health` 端点：
- 检查数据库连接（`SELECT 1`）
- 检查 Redis 连接（`PING`）
- 返回各项状态（`db: ok`, `redis: ok`）
- 任一失败返回 HTTP 503

### 文件变更
- 修改 `backend/app/main.py` — 增强 `/health` 端点

---

## 8. 资源限制适配小内存服务器

### 方案
当前服务器 1.6GB RAM，需调整生产配置：

| 服务 | 当前限制 | 调整后 |
|------|---------|--------|
| backend | 1G | 512M |
| postgres | 512M | 256M |
| redis | 256M | 128M |
| frontend | 无限制 | 128M |

总计 ~1024M，留 ~600M 给系统和其他进程。

同时配置 swap（见下一项），作为安全缓冲。

### 文件变更
- 修改 `docker-compose.prod.yml` — 调整所有资源限制

---

## 9. Swap 配置

### 方案
创建 `scripts/setup-swap.sh` 脚本：
- 检测是否已有 swap
- 若无，创建 2GB swap 文件
- 设置 `swappiness=10`（尽量少用 swap）
- 写入 `/etc/fstab` 持久化

此脚本需 root 权限手动执行一次，不在 Docker 容器内运行。

### 文件变更
- 新建 `scripts/setup-swap.sh`

---

## 10. 备份目录持久化

### 方案
- `docker-compose.yml` 中 postgres 增加一个 named volume `backups` 挂载到 `/backups`
- `backup.sh` 在容器内执行时写入此 volume
- 或者改为使用宿主机目录绑定（推荐，便于直接访问备份文件）

选择宿主机绑定方案：在项目根目录创建 `backups/` 目录，挂载到 postgres 容器。

### 文件变更
- 修改 `docker-compose.yml` — postgres 增加 backups volume mount

---

## 11. 部署运维脚本 / Makefile

### 方案
新建 `Makefile`，包含常用操作：

```makefile
make setup        # 初始化环境（运行 setup-env.sh, setup-swap.sh）
make up           # 启动所有服务（开发模式）
make up-prod      # 启动所有服务（生产模式）
make down         # 停止所有服务
make logs         # 查看实时日志
make backup       # 执行数据库备份
make restore      # 恢复数据库
make rebuild      # 重新构建并启动
make status       # 查看服务状态
make clean        # 清理 volumes 和 images
```

### 文件变更
- 新建 `Makefile`

---

## 总文件变更清单

| 文件 | 操作 |
|------|------|
| `.env` | 修改（由 setup-env.sh 填充） |
| `.env.example` | 修改（增加新变量） |
| `docker-compose.yml` | 修改 |
| `docker-compose.prod.yml` | 修改 |
| `backend/Dockerfile` | 修改 |
| `backend/entrypoint.sh` | 修改 |
| `backend/app/main.py` | 修改 |
| `frontend/Dockerfile` | 修改 |
| `scripts/setup-env.sh` | 新建 |
| `scripts/setup-swap.sh` | 新建 |
| `backend/scripts/init_admin.py` | 新建 |
| `frontend/entrypoint.sh` | 新建 |
| `Makefile` | 新建 |
