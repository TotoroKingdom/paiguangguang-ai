# Paiguangguang 发版操作步骤

本文档用于将 `dev` 合并到 `main`，并由 GitHub Actions 自动发布应用、Nginx 路由以及 Todo 静态服务。

## 发布后的访问入口

- 主站：`https://www.paiguangguang.xyz/`
- Excalidraw 域名入口：`https://www.paiguangguang.xyz/draw/`
- Todo 域名入口：`https://www.paiguangguang.xyz/todo/`
- 主站公网 IP：`http://1.12.47.29:8080/`
- Excalidraw 公网 IP：`http://1.12.47.29:8081/`
- Todo 公网 IP：`http://1.12.47.29:8082/`

## 一次性服务器准备

### 1. 确认文件和端口

```bash
test -f /home/my-website-ui/todo-demo-ui/todo-app.html
test -f /home/nginx/docker-compose.yml
test -f /home/nginx/nginx.conf
test -f /home/nginx/certs/www.paiguangguang.xyz.pem
test -f /home/nginx/certs/www.paiguangguang.xyz.key

grep -nE \
  '(src|href)="/|fetch\("/|url\("/' \
  /home/my-website-ui/todo-demo-ui/todo-app.html || true

docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
ss -lntp | grep -E ':80|:443|:8080|:8081|:8082' || true
```

Excalidraw 必须继续发布宿主机端口 `8081`，例如：

```yaml
ports:
  - "8081:80"
```

主 Nginx Compose 将接管 `8082`，并直接挂载 `todo-app.html`。首次从旧结构升级时，应用部署脚本会通过 `--remove-orphans` 自动删除旧的 Todo Nginx 容器，不需要手动拉取镜像或停止该容器。

发布前只需确认 `8082` 没有被项目之外的进程占用：

```bash
docker ps --filter publish=8082
```

如果存在占用，先通过下面命令确认 PID 和进程，再使用对应的服务管理方式处理；不要删除 `todo-app.html`：

```bash
ss -lntp | grep ':8082'
```

### 2. 检查证书域名

```bash
openssl x509 \
  -in /home/nginx/certs/www.paiguangguang.xyz.pem \
  -noout -subject -ext subjectAltName
```

证书应同时覆盖 `paiguangguang.xyz` 和 `www.paiguangguang.xyz`。

### 3. 云防火墙

腾讯云安全组和 CentOS 防火墙需要允许 TCP：

```text
80, 443, 8080, 8081, 8082
```

生产稳定后可以按需关闭 `8080`，但本次要求保留的 `8081`、`8082` 不要关闭。

### 4. GitHub 仓库配置

Repository Secrets：

```text
SERVER_HOST=1.12.47.29
SERVER_USER=root
SERVER_SSH_KEY=<完整 SSH 私钥>
TCR_USERNAME=<腾讯云账号 ID>
TCR_PASSWORD=<TCR 个人版初始化密码>
```

Repository Variables：

```text
TCR_REGISTRY=ccr.ccs.tencentyun.com
TCR_NAMESPACE=<已经创建的命名空间>
TCR_FRONTEND_REPOSITORY=<已经创建的前端仓库名>
TCR_BACKEND_REPOSITORY=<已经创建的后端仓库名>
```

建议前后端仓库名分别为 `paiguangguang-frontend` 和 `paiguangguang-backend`。不需要手动登录服务器或执行 `docker pull`；工作流会在每次发版时自动登录 TCR。不要把 TCR 密码放入 Variables 或仓库文件。

## 合并前检查

在仓库根目录执行：

```bash
git switch dev
git pull --ff-only origin dev
git status --short
```

确保工作区没有遗漏的修改，然后执行项目验证：

```bash
cd paiguangguang/frontend
npm ci
npm test
npm run lint
npm run build

cd ..
python -m pytest backend/tests -q

cd ..
```

检查本次部署文件：

```bash
git diff --check
docker compose \
  -f paiguangguang/deploy/docker-compose.yml \
  config --quiet
```

本地执行 Compose 校验时，需要先提供 `BACKEND_IMAGE`、`FRONTEND_IMAGE` 和 `IMAGE_TAG` 环境变量，或者使用一份测试 `.env`。

## 合并并触发自动发布

```bash
git switch main
git pull --ff-only origin main
git merge --no-ff dev
git push origin main
```

推送 `main` 后，`.github/workflows/deploy-paiguangguang.yml` 会自动：

1. 执行前端测试、lint 和生产构建。
2. 执行后端测试。
3. 构建前后端镜像并推送到腾讯云 TCR。
4. 上传应用 Compose、部署脚本和 Nginx 配置。
5. 使用完整 Commit SHA 部署应用镜像。
6. 启动主 Nginx，由它直接提供 Todo 静态页面并公开 8082。
7. 校验并加载 `/draw/`、`/todo/` Nginx 配置。
8. Nginx 配置失败时恢复 `/home/nginx/backups/<时间戳>/` 中的上一版文件。

在 GitHub 仓库的 Actions 页面打开 `Deploy Paiguangguang`，等待所有任务变成绿色。若 production environment 配置了审批保护，需要手动批准 deploy job。

## 发布后验收

服务器内部：

```bash
cd /home/my-website-ui/paiguangguang
docker compose --env-file .deploy.env -f docker-compose.yml ps
curl -fsS http://127.0.0.1:8080/api/v1/health
curl -fsS http://127.0.0.1:8081/ >/dev/null
curl -fsS http://127.0.0.1:8082/ >/dev/null

cd /home/nginx
docker compose -f docker-compose.yml -f docker-compose.web.yml ps
docker compose -f docker-compose.yml -f docker-compose.web.yml exec nginx nginx -t
```

外部网络：

```bash
curl -fsSI http://1.12.47.29:8080/
curl -fsSI http://1.12.47.29:8081/
curl -fsSI http://1.12.47.29:8082/
curl -fsSI https://www.paiguangguang.xyz/
curl -fsSI https://www.paiguangguang.xyz/draw/
curl -fsSI https://www.paiguangguang.xyz/todo/
curl -fsS https://www.paiguangguang.xyz/draw/manifest.webmanifest
```

浏览器还要检查：

- `/draw/` 的 Network 面板没有根路径 `/assets/` 404。
- Excalidraw Service Worker 的 Scope 是 `/draw/`，不是 `/`。
- `/todo/` 和 `IP:8082` 显示相同页面。
- 主站登录、`/api/v1/health`、Chatbot 和流式响应正常。

## 回滚

应用镜像自动部署失败时，`deploy.sh` 会恢复上一组镜像仓库地址和成功的 Commit SHA。

如果发布成功后发现业务问题，优先在 Git 中 revert 本次合并提交并推送 `main`，让流水线重新发布：

```bash
git switch main
git pull --ff-only origin main
git log --oneline --merges -n 5
git revert -m 1 <本次合并提交SHA>
git push origin main
```

如只需紧急恢复 Nginx，可在服务器查看备份：

```bash
ls -lt /home/nginx/backups
```

选择正确的备份时间戳后，恢复其中的 `docker-compose.web.yml`、`conf.d/paiguangguang.conf` 和 `conf.d/locations/*.conf`，再执行：

```bash
cd /home/nginx
docker compose -f docker-compose.yml -f docker-compose.web.yml up -d nginx
docker compose -f docker-compose.yml -f docker-compose.web.yml exec nginx nginx -t
docker compose -f docker-compose.yml -f docker-compose.web.yml exec nginx nginx -s reload
```
