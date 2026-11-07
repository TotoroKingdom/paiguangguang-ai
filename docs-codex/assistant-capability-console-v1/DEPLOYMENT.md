# 部署与管理员初始化

## 1. 本地后端

在 `backend/` 下执行迁移并启动服务：

```powershell
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

管理员有两种初始化方式。

### 环境变量

只在本机 `.env` 或进程环境中设置，不提交到仓库：

```text
ASSISTANT_ADMIN_USERNAME=admin
ASSISTANT_ADMIN_PASSWORD=<至少 12 个字符的随机密码>
```

应用启动时会校验密码并写入 PBKDF2 哈希；数据库不保存明文。环境变量中的密码变更后，下次启动会更新对应管理员的密码哈希。

### 交互式 CLI

```powershell
python -m app.admin_cli --username admin
```

命令使用隐藏输入读取密码，并创建或更新管理员。不要通过命令行参数传递明文密码。

## 2. 本地前端

```powershell
cd frontend
npm ci
npm run dev
```

访问：

- 用户工作台：`http://localhost:3000/assistant`
- 管理员登录：`http://localhost:3000/assistant/admin/login`
- 管理控制台：`http://localhost:3000/assistant/admin`

Next.js Rewrite 默认把 `/api/v1/*` 代理到 `http://127.0.0.1:8000`。可通过 `ASSISTANT_API_INTERNAL_URL` 修改。

## 3. 生产配置

`docker-compose.yml` 新增：

```text
ASSISTANT_ADMIN_COOKIE_SECURE=true
ASSISTANT_ADMIN_USERNAME=admin
ASSISTANT_ADMIN_PASSWORD=<GitHub Secret>
```

GitHub Actions 需要：

- Variable：`ASSISTANT_ADMIN_USERNAME`
- Secret：`ASSISTANT_ADMIN_PASSWORD`

生产配置还会校验：

- `ASSISTANT_ADMIN_COOKIE_SECURE=true`
- `ASSISTANT_ADMIN_PASSWORD` 至少 12 个字符
- 数据库中至少存在一个启用状态的管理员，否则启动失败并要求先完成初始化

部署前保留 SQLite 备份。容器入口仍执行 `alembic upgrade head`，新增迁移为 `0002_admin_capabilities`。

## 4. Cookie 与代理

- 管理会话 Cookie：`paiguangguang_admin`，HttpOnly、SameSite=Strict、生产 Secure。
- CSRF Cookie：`paiguangguang_admin_csrf`，同源前端可读，生产 Secure。
- 管理写操作必须携带 `X-CSRF-Token`，并带可信 Origin。
- 反向代理必须正确传递 `Host`、`Origin` 与 HTTPS 协议；否则管理写请求会按设计返回 `403`。

## 5. 升级与回滚

```powershell
cd backend
python -m alembic current
python -m alembic upgrade head
```

本次迁移只新增表，不修改既有 `conversations` / `messages`。如需回滚：

```powershell
python -m alembic downgrade 0001_assistant_sessions
```

回滚会删除管理员、能力注册表、运行与审计数据。生产回滚前必须备份数据库。
