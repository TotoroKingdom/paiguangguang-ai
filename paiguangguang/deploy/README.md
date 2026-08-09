# Paiguangguang 服务器部署手册

本手册对应当前测试入口 `http://1.12.47.29:8080`。应用镜像由 GitHub Actions 构建并发布到腾讯云 TCR，生产服务器由同一工作流自动登录 TCR、拉取镜像并启动容器。

## 1. 服务器前置条件

在服务器执行：

```bash
docker --version
docker compose version
curl --version
```

要求：

- Docker Engine 正常运行。
- 使用 Docker Compose v2，命令形式为 `docker compose`。
- 服务器可以访问配置的 TCR Registry、DeepSeek 和 DashScope，并且 `postgres17` 容器已经运行。
- 腾讯云安全组和 CentOS 防火墙允许 TCP 8080 入站。
- `/home/nginx` 中存在证书、`nginx.conf` 和 `conf.d` 目录。

检查 Nginx 基础文件：

```bash
test -f /home/nginx/nginx.conf
test -f /home/nginx/certs/www.paiguangguang.xyz.pem
test -f /home/nginx/certs/www.paiguangguang.xyz.key
```

## 2. 首次上传部署文件

先在服务器创建目录：

```bash
install -d -m 755 /home/my-website-ui/paiguangguang
install -d -m 700 /home/my-website-ui/paiguangguang/backend
install -d -m 755 /home/my-website-ui/paiguangguang-bootstrap
docker network inspect web >/dev/null 2>&1 || docker network create web
```

然后在本地 Git 仓库根目录执行：

```bash
scp -r paiguangguang/deploy/* root@1.12.47.29:/home/my-website-ui/paiguangguang-bootstrap/
scp paiguangguang/deploy/.deploy.env.example root@1.12.47.29:/home/my-website-ui/paiguangguang-bootstrap/
scp paiguangguang/backend/auth-login-private-key.pem root@1.12.47.29:/home/my-website-ui/paiguangguang/auth-login-private-key.pem
```

如果本地还没有登录加密私钥，在 `paiguangguang/backend` 下执行：

```bash
python -m scripts.generate_login_key --output auth-login-private-key.pem
```

## 3. 初始化应用运行文件

在服务器执行：

```bash
cd /home/my-website-ui/paiguangguang
cp /home/my-website-ui/paiguangguang-bootstrap/docker-compose.yml docker-compose.yml
cp /home/my-website-ui/paiguangguang-bootstrap/deploy.sh deploy.sh
test -f .deploy.env || cp /home/my-website-ui/paiguangguang-bootstrap/.deploy.env.example .deploy.env
chmod 755 deploy.sh
chmod 600 .deploy.env auth-login-private-key.pem
```

GitHub Actions 每次发布都会把仓库中的 `backend/prod.env` 安装到：

```text
/home/my-website-ui/paiguangguang/backend/prod.env
```

该文件权限为 `600`，生产数据库通过专用 Docker 网络连接同一台服务器上的 `postgres17`，不使用 PostgreSQL SSL：

```text
postgresql+psycopg://paiguangguang:postgres%40paiguangguang@postgres17:5432/knowledge_rag_agent
```

密码中的 `@` 在连接 URL 中必须写成 `%40`。`deploy.sh` 会自动创建 `paiguangguang_database` 网络，并把现有的 `postgres17` 容器接入该网络。

生产配置中禁止出现测试数据库地址：

```bash
test -f backend/prod.env
! grep -q '^TEST_DATABASE_URL=' backend/prod.env
grep '^DATABASE_URL=.*@postgres17:5432/knowledge_rag_agent$' backend/prod.env
test "$(stat -c '%a' backend/prod.env)" = 600
```

三个命令都应返回成功。

## 4. 部署主 Nginx

使用独立的 Nginx Compose 配置部署：

```bash
bash /home/my-website-ui/paiguangguang-bootstrap/nginx/deploy-nginx.sh \
  /home/my-website-ui/paiguangguang-bootstrap/nginx
```

部署脚本会写入 `/home/nginx/docker-compose.web.yml`。后续检查只使用该文件，不再与旧的 `/home/nginx/docker-compose.yml` 合并：

```bash
cd /home/nginx
docker compose -f docker-compose.web.yml config --quiet
docker compose -f docker-compose.web.yml ps
docker compose -f docker-compose.web.yml exec nginx nginx -t
```

确认 Nginx 已发布 8080：

```bash
docker compose -f docker-compose.web.yml ps
ss -lntp | grep ':8080'
```

旧的 `/home/nginx/docker-compose.yml` 仅作为历史文件保留，不得再用于启动生产 Nginx。

## 5. TCR 自动认证

不需要在服务器手动执行 `docker pull` 或长期维护手工登录状态。每次发布时，GitHub Actions 都会通过 SSH 将 TCR 凭据作为受保护的环境变量传给服务器，并使用 `docker login --password-stdin` 自动登录。TCR 密码只配置在 GitHub Actions Secrets 中，不得写入 `.deploy.env`、Compose、脚本或提交记录。

## 6. GitHub 仓库配置

在 GitHub 仓库的 Actions Repository Secrets 中配置：

```text
SERVER_HOST=1.12.47.29
SERVER_USER=root
SERVER_SSH_KEY=服务器 root 账户对应的完整多行 SSH 私钥
TCR_USERNAME=腾讯云账号 ID（个人版登录用户名）
TCR_PASSWORD=TCR 个人版初始化密码
```

在 Actions Repository Variables 中配置：

```text
TCR_REGISTRY=ccr.ccs.tencentyun.com
TCR_NAMESPACE=已经创建的 TCR 命名空间
TCR_FRONTEND_REPOSITORY=已经创建的前端镜像仓库名
TCR_BACKEND_REPOSITORY=已经创建的后端镜像仓库名
```

个人版仓库名建议分别使用 `paiguangguang-frontend` 和 `paiguangguang-backend`。Variables 和 Secrets 必须配置在 Repository 级别；如果只配置在 `production` Environment 中，`publish-images` 作业将无法读取。

当前流程沿用 root 账户。建议限制该 SSH Key 的用途，并关闭服务器密码登录；后续可以改成具有 Docker 权限的独立部署账户。

工作流文件：

```text
.github/workflows/deploy-paiguangguang.yml
```

它只在 `main` 分支中的 `paiguangguang/**` 或工作流自身发生变化时自动运行，也支持手动触发。

## 7. 首次自动发布

开发改动先提交到 `dev`。确认完成后，在本地 Git 根目录执行：

```bash
git checkout main
git pull --ff-only origin main
git merge --no-ff dev
git push origin main
```

推送 `main` 后，GitHub Actions 会依次执行：

1. 前端测试、Lint、生产构建。
2. 后端完整测试。
3. 构建前端和后端镜像。
4. 使用完整 Commit SHA 和 `latest` 标签推送到 TCR。
5. 上传 `docker-compose.yml`、`deploy.sh` 和 `cleanup-images.sh`。
6. SSH 登录服务器执行健康检查部署。
7. 新版本失败时恢复上一组镜像仓库地址和 Commit SHA；首次从 GHCR 切换到 TCR 失败时也能恢复旧配置。
8. 发布成功后保留当前版本和上一个成功版本，清理其余 TCR/GHCR 前后端镜像标签。

首次部署没有上一版本可回滚，因此应在测试通过后再触发。

## 8. 发布后验证

在服务器执行：

```bash
cd /home/my-website-ui/paiguangguang
docker compose --env-file .deploy.env -f docker-compose.yml ps
curl -fsS http://127.0.0.1:8080/ >/dev/null
curl -fsS http://127.0.0.1:8080/api/v1/health
grep '^IMAGE_TAG=' .deploy.env
docker compose --env-file .deploy.env -f docker-compose.yml images
```

在外部电脑执行：

```bash
curl -fsS http://1.12.47.29:8080/ >/dev/null
curl -fsS http://1.12.47.29:8080/api/v1/health
```

浏览器打开 `http://1.12.47.29:8080`，验证登录、管理端、RAG 和 Chatbot。浏览器开发者工具中的 API 地址应全部为 `http://1.12.47.29:8080/api/...`，Chatbot 流式内容应逐步返回。

## 9. 日志和常用操作

```bash
cd /home/my-website-ui/paiguangguang

docker compose --env-file .deploy.env -f docker-compose.yml ps
docker compose --env-file .deploy.env -f docker-compose.yml logs --tail=200 frontend backend redis
docker compose --env-file .deploy.env -f docker-compose.yml logs -f backend
docker compose --env-file .deploy.env -f docker-compose.yml restart backend
```

前端、后端和 Redis 均不映射宿主机端口。正常情况下，服务器只需要对公网开放 Nginx 的 8080。

## 10. 手动回滚

自动部署失败时，`deploy.sh` 会恢复 `.deploy.env` 中的上一成功 SHA。需要手动回滚时：

```bash
cd /home/my-website-ui/paiguangguang
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=上一成功版本的完整CommitSHA/' .deploy.env
docker compose --env-file .deploy.env -f docker-compose.yml pull frontend backend
docker compose --env-file .deploy.env -f docker-compose.yml up -d --remove-orphans --wait --wait-timeout 180
curl -fsS http://127.0.0.1:8080/api/v1/health
```

镜像回滚不会回滚 PostgreSQL 数据或数据库迁移。包含不可逆迁移的版本必须先提供向后兼容方案。

## 11. 数据卷和备份

检查持久卷：

```bash
docker volume inspect paiguangguang_redis_data
docker volume inspect paiguangguang_chroma_data
```

Redis AOF 和 Chroma 索引在容器重建后保留。进行破坏性维护前，需要同时备份 PostgreSQL、`paiguangguang_redis_data` 和 `paiguangguang_chroma_data`。恢复时应保证 PostgreSQL 数据与 Chroma 索引来自相近时间点；不一致时通过管理端重新索引文档。
