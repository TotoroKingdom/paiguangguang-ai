# Paiguangguang 部署手册

生产环境继续发布 frontend 与 backend 两个镜像，并保留 Redis 容器。backend 只负责健康检查，Nginx 将 `/api/` 反向代理到该容器。

## 前置条件

- Docker Engine 与 Docker Compose v2。
- 已创建 Docker `web` 网络。
- Nginx 证书与配置目录已准备好。
- `.deploy.env` 包含 `FRONTEND_IMAGE`、`BACKEND_IMAGE` 和 `IMAGE_TAG`。

不再需要 PostgreSQL、Chroma、后端环境变量或登录加密私钥。

## 发布验证

```bash
cd /home/my-website-ui/paiguangguang
docker compose --env-file .deploy.env -f docker-compose.yml config --quiet
docker compose --env-file .deploy.env -f docker-compose.yml ps
curl -fsS http://127.0.0.1:8080/
curl -fsS http://127.0.0.1:8080/api/v1/health
```

健康检查必须返回：

```json
{"status":"ok"}
```

发布脚本保留双镜像拉取、健康检查等待和自动回滚机制；详见 `deploy.sh`。
