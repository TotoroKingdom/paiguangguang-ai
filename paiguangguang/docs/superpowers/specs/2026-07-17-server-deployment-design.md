# Paiguangguang 单服务器生产部署设计

日期：2026-07-17

## 1. 目标与约束

- 使用 `http://1.12.47.29:8080` 作为当前访问入口。
- 前端、后端部署在同一台 CentOS 服务器上。
- 复用 `/home/nginx` 中已有的 Nginx 容器，不影响服务器上的其他应用。
- PostgreSQL 使用 Neon 远程数据库，不在服务器上运行 PostgreSQL 容器。
- 前端、后端和 Redis 由应用自己的 Docker Compose 管理。
- 只有 Nginx 对宿主机暴露端口；前端、后端和 Redis 不直接暴露公网端口。
- Chroma 和 Redis 数据需要在容器重建后保留。
- GitHub Actions 在 `main` 分支更新时自动测试、构建并发布 GHCR 镜像。
- 服务器只拉取已构建镜像，不在生产服务器现场编译源码。

## 2. 推荐架构

服务器保留两个独立的 Compose 项目：

1. `/home/nginx` 管理公共 Nginx。
2. `/home/my-website-ui/paiguangguang` 管理前端、后端和 Redis。

两个项目通过预先创建的外部 Docker 网络 `web` 通信。应用内部再创建一个私有网络 `app_internal`，仅供后端和 Redis 使用。

请求路径：

```text
http://1.12.47.29:8080
  -> Nginx
     -> /api/* -> backend:8000
     -> /*      -> frontend:3000

backend
  -> Neon PostgreSQL（公网 TLS 连接）
  -> Redis（app_internal 私有网络）
  -> Chroma（Docker named volume）
```

## 3. Nginx 路由

Nginx 容器加入外部网络 `web`，宿主机映射 `8080:80`。新增独立站点配置，不修改现有 todo 站点的业务路由。

- `location /api/` 代理到后端网络别名 `paiguangguang-backend:8000`。
- `location /` 代理到前端网络别名 `paiguangguang-frontend:3000`。
- 转发 `Host`、客户端地址和 `X-Forwarded-*` 请求头。
- API 代理使用 HTTP/1.1。
- 对聊天流式响应关闭 `proxy_buffering` 和响应缓存，并将读取超时提高到 3600 秒。
- 当前阶段使用 HTTP；启用域名后再增加证书、HTTPS 跳转和 HSTS。

## 4. 前端生产运行方式

前端镜像使用多阶段构建：

1. 依赖阶段通过 `npm ci` 安装锁定依赖。
2. 构建阶段执行 `npm run build`。
3. 运行阶段设置 `NODE_ENV=production`，通过 `npm start` 启动 Next.js。

生产环境 API 基址使用空字符串，即浏览器请求同源的 `/api/*`。开发环境仍可通过 `NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000` 直连本地后端。

`NEXT_PUBLIC_*` 变量在 Next.js 构建阶段固化，因此生产值必须作为 Docker build argument 传入，不能只在容器运行时设置。

前端 `.dockerignore` 排除 `node_modules`、`.next`、日志、本地环境文件、测试缓存和 TypeScript 构建缓存，避免将宿主机依赖复制进 Linux 镜像。

## 5. 后端与 Neon

生产环境只配置 `DATABASE_URL`，不配置 `TEST_DATABASE_URL`。Neon 连接字符串必须包含 TLS 参数 `sslmode=require`。

当前单实例部署继续在 FastAPI 启动阶段执行 Alembic 迁移。后续扩展为多实例时，应将迁移拆为独立的一次性发布步骤，避免多个实例并发迁移。

后端镜像继续运行单个 Uvicorn 进程，因为当前应用内同时启动 Chatbot 后台任务循环。若以后增加多个 API worker，应先将后台任务拆为单独 worker 服务。

后端 `.dockerignore` 排除环境文件、私钥、测试、缓存、本地 Chroma 数据、文档和开发工具文件。登录私钥通过只读 volume 或服务器 Secret 挂载到容器固定路径。

## 6. Redis

Redis 只连接 `app_internal` 网络，不配置宿主机 `ports`，后端使用 `redis://redis:6379/0` 访问。

Redis 启用 AOF，并挂载 named volume `redis_data:/data`。在仅内部网络且服务器访问权限受控的当前阶段，可以不配置 Redis 密码；若服务器还运行不受信任的容器，应增加 ACL 或密码认证。

## 7. Chroma 持久化

后端配置 `CHROMA_PATH=/data/chroma`，并挂载 named volume `chroma_data:/data/chroma`。这样重新创建后端容器不会丢失向量索引。

Chroma 数据必须与 Neon 中的文档和 chunk 元数据同步备份。恢复时先恢复 Neon，再恢复同一时间点的 Chroma 数据；如果两者不一致，应通过管理端执行重新索引。

## 8. Compose 运行与健康检查

应用 Compose 包含三个服务：

- `frontend`：加入 `web` 网络，不映射宿主机端口。
- `backend`：同时加入 `web` 和 `app_internal` 网络，不映射宿主机端口。
- `redis`：只加入 `app_internal` 网络，不映射宿主机端口。

Redis 增加 `redis-cli ping` 健康检查。前后端增加 HTTP 健康检查；后端健康检查访问 `/api/v1/health`，前端健康检查访问 `/`。依赖关系使用健康状态而不是仅使用启动顺序。

所有服务设置 `restart: unless-stopped`。Docker 日志使用 `json-file` 驱动，并设置文件大小和数量上限，避免长期运行占满磁盘。

## 9. GitHub Actions 与 GHCR 发布

新增独立工作流 `.github/workflows/deploy-paiguangguang.yml`，保留现有 Todo 工作流不变。工作流在以下情况触发：

- 推送到 `main` 分支。
- 变更路径包含 `paiguangguang/**` 或工作流自身。
- 允许通过 `workflow_dispatch` 手动重新发布。

工作流分为三个阶段：

1. **验证**：前端执行依赖安装、测试、Lint 和生产构建；后端安装生产与测试依赖并执行完整测试。任一验证失败都不得构建或部署镜像。
2. **构建与推送**：使用 Docker Buildx 分别构建前端和后端镜像，推送到 GHCR。每个镜像使用完整 Git Commit SHA 作为不可变标签；`main` 最新成功构建可以额外更新 `latest` 标签，但部署只使用 SHA 标签。
3. **服务器部署**：通过现有的 `SERVER_HOST`、`SERVER_USER` 和 `SERVER_SSH_KEY` 登录服务器，设置本次 `IMAGE_TAG`，拉取两个镜像并启动应用 Compose，然后经 Nginx 执行健康检查。

工作流只需要 `contents: read` 和 `packages: write` 权限。镜像名称固定为：

- `ghcr.io/<github-owner>/<github-repository>-frontend:<commit-sha>`
- `ghcr.io/<github-owner>/<github-repository>-backend:<commit-sha>`

服务器需要预先通过具有 `read:packages` 权限的只读凭据登录 GHCR。生产 Compose 使用 `IMAGE_TAG` 选择镜像，不包含 `build` 配置。

为了避免并发发布互相覆盖，工作流使用固定的 production concurrency group，同一时间只允许一个部署任务运行。

## 10. 自动回滚

服务器在 `.deploy.env` 中保存当前成功部署的 `IMAGE_TAG`。部署新版本前读取并保存旧标签，然后执行以下流程：

1. 写入新 Commit SHA。
2. 拉取新镜像并重建前端、后端容器。
3. 等待容器健康检查通过。
4. 通过 `http://127.0.0.1:8080/` 和 `/api/v1/health` 验证 Nginx、前端和后端完整链路。
5. 验证成功后保留新标签。
6. 任一步骤失败时恢复旧标签、重新启动旧镜像，并让 GitHub Actions 任务失败。

Redis 和 Chroma 使用稳定的 named volume，镜像回滚不回滚数据。包含不可逆数据库迁移的版本必须提供向后兼容迁移，不能依赖镜像回滚恢复数据库结构。

## 11. 首次部署流程

1. 将项目部署到 `/home/my-website-ui/paiguangguang`。
2. 创建外部网络 `web`；已存在时跳过。
3. 将生产 Compose、`.deploy.env` 和后端运行环境变量放入应用目录。
4. 配置 Neon 连接和登录私钥挂载。
5. 让 Nginx Compose 和应用 Compose 都加入 `web` 网络。
6. 在服务器上登录 GHCR，并确认可以拉取私有镜像。
7. 配置并重载 Nginx。
8. 在 GitHub 仓库中配置 `SERVER_HOST`、`SERVER_USER` 和 `SERVER_SSH_KEY`。
9. 手动触发一次 GitHub Actions 工作流完成首次镜像发布和启动。
10. 从外部访问 `http://1.12.47.29:8080`，验证页面、登录、普通 API 和 Chatbot SSE。

发布失败时，不修改 Neon 数据，并保留 Redis、Chroma 两个 Docker named volume；应用回滚到上一个镜像版本并重新启动容器。

## 12. 验收标准

- `http://1.12.47.29:8080` 能打开前端页面。
- 浏览器所有 API 请求都发往同源 `/api/*`，不存在 `localhost` 或 `127.0.0.1` 请求。
- `/api/v1/health` 经 Nginx 返回成功。
- 登录、管理端、RAG 和 Chatbot 流式输出可用。
- 宿主机只需要开放 Nginx 的 8080 端口；3000、8000、6379 均不对公网监听。
- 后端成功连接 Neon，且没有读取 `TEST_DATABASE_URL`。
- 重建 Redis 和后端容器后，Redis AOF 数据及 Chroma 索引仍存在。
- Docker 日志大小受限，所有容器具有可观察的健康状态。
- 只有前后端验证全部通过时才会推送和部署镜像。
- 生产服务器运行的前端和后端镜像标签等于触发工作流的 Commit SHA。
- 连续触发多个发布时不会并发修改生产环境。
- 部署后健康检查失败会自动恢复上一成功镜像标签，并在 GitHub Actions 中显示失败。
