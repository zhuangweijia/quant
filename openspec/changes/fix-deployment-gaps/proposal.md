# Proposal: Fix Deployment Gaps

## Problem

QuantPlatform 项目在当前服务器上无法直接通过 `docker compose up -d` 正常运行，存在以下关键问题：

### 安全问题
1. **`.env` 仍是占位符** — 数据库密码和加密密钥仍为 `CHANGE_ME_*`，服务无法安全启动
2. **Redis 无认证** — 生产环境 Redis 裸奔，无密码保护
3. **无网络隔离** — 前端容器可直接访问 PostgreSQL 和 Redis，缺乏最小权限原则
4. **Backend 端口暴露** — 生产环境下 backend:8000 不应暴露到宿主机

### 功能缺陷
5. **生产 SSL 配置无法生效** — `docker-compose.prod.yml` 挂载了 SSL 证书目录，但 Frontend Dockerfile 始终使用 `nginx.conf`（HTTP only），`nginx.ssl.conf` 从未被引用
6. **无初始管理员创建** — 首次部署后无法登录，缺少 seed/admin 初始化机制
7. **健康检查不充分** — `/health` 端点仅返回 `{"status": "ok"}`，不检查 DB/Redis 连通性

### 资源适配
8. **内存超限风险** — 服务器仅 1.6GB RAM，生产配置总计需 1.75GB（backend 1G + postgres 512M + redis 256M），无 swap
9. **无 swap 配置** — 内存不足时 OOM Killer 会直接杀掉容器

### 运维缺失
10. **备份目录未持久化** — `backup.sh` 默认写入 `/backups`，非 Docker volume，容器重建后丢失
11. **无便捷部署脚本** — 缺少 Makefile 或 deploy.sh 统一管理常用操作（启动/停止/备份/日志）

## Goal

让项目在当前服务器（1.6GB RAM / 2 CPU / 40GB 磁盘）上可通过一条命令安全稳定地运行起来，修复所有安全和功能缺陷。

## Non-goals

- 不涉及 SSL 证书申请（用户需自行准备或后续添加 certbot）
- 不涉及 CI/CD 流水线修改
- 不涉及应用功能开发
- 不涉及监控告警体系搭建（Prometheus/Grafana 等后续单独处理）
