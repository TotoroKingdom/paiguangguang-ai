# 智能助手产品架构重构与管理控制台 V1

## 1. 目标与边界

本次在不拆仓库、不新增域名、不引入微服务的前提下，把同一 Next.js 应用拆成三个清晰产品面：

1. 个人网站：继续承载首页、RAG、3D 实验室与智能助手入口。
2. 智能助手用户工作台：`/assistant`，继续提供聊天、文件、工具、技能、MCP 与智能体目录。
3. 智能助手管理控制台：`/assistant/admin`，提供管理员登录、能力注册、草稿编辑、版本发布、停用、运行记录与审计。

FastAPI 保持单体，但按领域建立模块边界。SQLite 与 Alembic 保持不变。

本次不实现真实 LLM、MCP Runtime、Agent Loop、微服务、多租户计费或插件市场。演示与模拟执行均在界面和记录中明确标注。

## 2. 前端路由与 Layout

实际 URL 全部保持兼容：

```text
frontend/src/app/
├── (portfolio pages remain at root)
│   ├── page.tsx
│   ├── rag/
│   ├── lab/3d/
│   └── threejs/
└── assistant/
    ├── layout.tsx                 # 最小共享 Layout，仅 metadata
    ├── assistant.css
    ├── (workspace)/               # URL 无变化
    │   ├── layout.tsx             # 用户工作台 Sidebar + Provider + Composer
    │   ├── page.tsx               # /assistant
    │   ├── chat/[id]/             # /assistant/chat/:id
    │   ├── tools/                 # /assistant/tools
    │   ├── skills/
    │   ├── mcp/
    │   ├── agents/
    │   └── files/
    └── (management)/
        └── admin/
            ├── layout.tsx         # 独立管理端 Provider + Frame + admin.css
            ├── login/             # /assistant/admin/login
            ├── page.tsx           # /assistant/admin
            ├── tools/
            ├── skills/
            ├── mcp/
            ├── agents/
            ├── capabilities/[id]/ # 统一能力详情页
            ├── releases/
            ├── runs/
            └── settings/
```

根级 portfolio 页面未强行迁入 `(portfolio)` Route Group，原因是它们与根 Layout、主页 Three.js 层和既有视觉验收存在强耦合；本次以“不破坏路由”为优先。Assistant 内部已完成工作台与管理端的 Layout 隔离，管理页面不会继承用户聊天 Sidebar。

## 3. 后端模块

```text
backend/app/
├── core/
│   └── security.py                # PBKDF2 密码哈希、Token 哈希
├── modules/
│   ├── identity/                  # 管理员、会话、登录限流、鉴权依赖
│   ├── capabilities/              # 能力定义、不可变版本、发布、公开目录、运行记录
│   └── observability/             # 审计事件
├── routers/conversations.py       # 既有用户会话 API
├── services.py                    # 会话服务，新增能力准入校验与运行记录
└── main.py                        # 应用组装、启动初始化、Origin/Body 防护
```

既有 `config.py`、`db.py`、`models.py` 等文件保留并复用，不为了目录形式强制搬迁已有会话实现。

## 4. 数据模型

新增表：

| 表 | 作用 |
| --- | --- |
| `admin_users` | 管理员身份、PBKDF2 密码哈希、角色与启停状态 |
| `admin_sessions` | 服务端会话，仅保存 Token 哈希与 CSRF 哈希 |
| `capability_definitions` | 能力统一元数据与当前生命周期状态 |
| `capability_versions` | 版本、状态、不可变 JSON 发布快照、发布时间 |
| `capability_dependencies` | 版本对其它能力的依赖关系 |
| `capability_runs` | 用户端真实的能力准入记录，标记 `demo` / `simulated` |
| `audit_events` | 管理登录、草稿保存、发布、停用等审计事件 |

既有 `conversations`、`messages` 保持不变。

## 5. 能力生命周期

```text
创建草稿 -> 编辑草稿 -> 发布快照 -> 用户目录可见 -> 停用 -> 用户目录移除且新调用被拒绝
```

- 定义状态：`draft`、`published`、`disabled`。
- 版本状态：`draft`、`published`、`retired`。
- 已发布版本快照只读。编辑已发布能力时自动创建更高版本的草稿，不覆盖旧快照。
- 发布在同一数据库事务中退役旧发布版本、发布新版本并更新定义状态。
- 停用立即从公开目录移除，并让后续聊天消息的能力准入返回 `422`。
- 系统初始化 24 个演示能力，快照标记 `executionMode=demo`，与后续管理端创建的 `simulated` 能力区分。

## 6. 管理员安全

- 密码只以 `pbkdf2_sha256$390000$...` 哈希形式写入数据库。
- 管理员密码由环境变量或交互式 CLI 注入，仓库不提供默认明文密码。
- 登录成功生成随机会话 Token 与 CSRF Token；数据库仅保存 SHA-256 哈希。
- 管理会话 Cookie：`HttpOnly`、`SameSite=Strict`，生产环境强制 `Secure`。
- CSRF Cookie 非 HttpOnly，供同源前端读取并在写请求头回传；服务端与数据库中的 CSRF 哈希比较。
- 管理写请求要求可信 Origin；无 Origin 时仅接受 `Sec-Fetch-Site: same-origin|none`。
- 登录失败按 `IP + 用户名` 滑动窗口限流，达到阈值后临时锁定。
- 未登录管理 API 返回 `401`；非管理员角色或无效 CSRF 返回 `403`。
- 匿名浏览器 Cookie 继续只用于普通聊天会话隔离，不作为管理员身份。

## 7. 用户工作台联动

- `GET /api/v1/capabilities` 是用户端能力目录的数据源。
- 前端 `AssistantProvider` 启动时加载服务端目录；API 不可用时仅回退到内置演示目录。
- 公开目录不返回执行器配置、System Prompt、凭据引用等管理端字段。
- 聊天创建 Turn 时，服务端重新校验能力 ID、类型和发布状态，不信任客户端名称或客户端目录。
- 服务端将最终能力名称写回消息快照，并写入 `capability_runs`。
- 管理端发布后，用户重新进入或被浏览器 focus 触发刷新时可见；停用后新目录和新调用均不可用。

## 8. API 清单

### 管理员认证

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/admin/auth/login` | 管理员登录 |
| `GET` | `/api/v1/admin/auth/session` | 查询当前管理员会话 |
| `POST` | `/api/v1/admin/auth/logout` | 安全退出，需要 CSRF |

### 管理员能力治理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/admin/overview` | 仪表盘统计 |
| `GET` | `/api/v1/admin/capabilities` | 搜索、状态与类型筛选 |
| `POST` | `/api/v1/admin/capabilities` | 创建能力草稿 |
| `GET` | `/api/v1/admin/capabilities/{id}` | 能力详情与版本历史 |
| `PATCH` | `/api/v1/admin/capabilities/{id}` | 保存草稿或从发布版本创建新草稿 |
| `POST` | `/api/v1/admin/capabilities/{id}/publish` | 事务性发布版本 |
| `POST` | `/api/v1/admin/capabilities/{id}/disable` | 停用能力 |
| `GET` | `/api/v1/admin/releases` | 发布与退役版本记录 |
| `GET` | `/api/v1/admin/runs` | 用户能力调用记录 |
| `GET` | `/api/v1/admin/audit-events` | 管理审计事件 |
| `GET` | `/api/v1/admin/settings` | 只读运行环境与安全策略 |

### 用户目录

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/capabilities` | 仅返回已发布能力 |
| `GET` | `/api/v1/capabilities/{id}` | 仅返回已发布能力详情 |

### 既有会话

`/api/v1/conversations` 与 `/api/v1/conversations/{id}/turns` 等接口保持兼容，新增服务端能力准入校验。

## 9. 尚未实现

- 真实 LLM 调用、真实 MCP 连接测试、工具发现与 Agent Loop。
- 发布版本回滚、审批流、定时发布。
- 依赖图可视化、复杂 Schema 表单、资源文件上传。
- 多管理员 RBAC 管理页面（数据库已保留 `role` 字段）。
- 全量运行日志、成本与延迟指标。
