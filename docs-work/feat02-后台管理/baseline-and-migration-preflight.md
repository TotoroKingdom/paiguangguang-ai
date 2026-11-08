# feat02 / F00 基线与迁移前置核验

> 版本：v0.1
> 日期：2026-11-08（Asia/Shanghai）
> 仓库：`TotoroKingdom/paiguangguang-ai`
> 任务：feat02 G0 / F00（只读基线、存量盘点、迁移与回滚前置）
> 文档性质：**只读核验记录与迁移契约草案，不是 F02 实施结果、不是生产验收报告**。
> 结论：**F00 = BLOCKED**。源码、Git 与本地静态基线可复核；生产数据库、生产备份恢复、生产运行状态和 PR #11 阻断项未获授权核验，不能把“未验证”写成“通过”。

---

## 0. 执行边界与结论摘要

本轮做到了：

- 锁定当前 worktree、未提交状态、`dev` / `main` / 文档分支 SHA。
- 阅读 `chore/local-env-data` 上的 feat02 总纲及 `01`～`06` 文档，确认 `06-实施TASKS.md` 为唯一 F 编号权威源。
- 核验 `dev` 源码中的 SQLite 表、Alembic revision、管理员身份、匿名 Owner、Cookie、CI、Docker 备份与发布工作流。
- 只读查询本地开发数据库的聚合计数，不读取会话正文、管理员哈希或恢复材料。
- 核验 PR #11 当前状态和最近 CI 运行。

本轮没有做、也不能声称做过：

- 没有读取或修改生产数据库。
- 没有执行生产备份、恢复、迁移、管理员重置或 destructive SQL（破坏性 SQL）。
- 没有对本地备份执行 `integrity_check`、恢复演练或迁移演练；没有明确授权，因此不执行。
- 没有启动 Docker、没有查看命名卷；本机 Docker daemon（守护进程）不可用。
- 没有实现 F02、没有新增用户表、没有改生产代码。

### 0.1 判定

| 项目 | 判定 | 说明 |
|---|---|---|
| Git 与 worktree 基线 | PASS | 当前分支、HEAD、远端分支、工作树状态均已固定 |
| 需求文档基线 | PASS | 总纲与 `01`～`06` 已读；`06` 的 F 编号作为权威 |
| `dev` 源码静态审查 | PASS | 迁移、表、身份、Cookie、CI、部署链路均已阅读 |
| 本地开发库聚合盘点 | PASS（仅本地） | 只读计数完成；不能代表生产 |
| 生产存量盘点 | NOT_VERIFIED | 无生产数据库或服务器访问 |
| 备份存在性 | PASS（仅文件存在） | 本地有一份候选备份文件，但未验证一致性或可恢复性 |
| 备份恢复演练 | BLOCKED | 没有明确授权，也未在隔离环境执行 |
| 生产迁移/回滚证据 | BLOCKED | 无生产或预发布环境证据 |
| PR #11 生产阻断复核 | BLOCKED | GitHub 状态可读；服务器 TLS、密钥、部署权限无法验证 |
| **F00 总体** | **BLOCKED** | 静态基线完成，但 F00 的恢复证据和生产盘点未满足 |

---

## 1. Git、worktree 与文档位置

### 1.1 当前 worktree

核验时间：`2026-11-08T13:41:31+08:00`。

| 项目 | 观测值 |
|---|---|
| 工作目录 | `C:\AI\paiguangguang-ai` |
| 当前分支 | `chore/local-env-data` |
| 当前 HEAD | `0382be00fda17e0f4c46dfed527595eb94096767` |
| HEAD 提交 | `docs: 规划文档` |
| HEAD 父提交 | `8bce4202ef601fdfc8665690e6baa3d0f723b630` |
| 本地与 `origin/chore/local-env-data` | 一致，`0 ahead / 0 behind` |
| 初始未提交修改 | 0（开始核验时工作树干净） |
| 已注册 worktree | 仅当前 worktree；未发现第二个 worktree |

本轮没有切换分支、没有重置、没有清理其他会话文件。文档写入后只应提交本任务新增的两个 Markdown 文件。

### 1.2 长期分支

| 分支 | SHA | 时间 | 说明 |
|---|---|---|---|
| `dev` | `fd7f40bfe787d872f44da51a3003e1a45cf78216` | 2026-11-08 01:25:59 +08 | `merge: make capability publication and audit atomic (#14)` |
| `main` | `a301e5503e44b65560fdacd6ea734407dd87b7a1` | 2026-11-07 14:43:00 +08 | `docs: add assistant session persistence plan` |
| `origin/dev` | `fd7f40bfe787d872f44da51a3003e1a45cf78216` | 同上 | 与本地 `dev` 一致 |
| `origin/main` | `a301e5503e44b65560fdacd6ea734407dd87b7a1` | 同上 | 与本地 `main` 一致 |

`dev` 相对 `main` 为 `0 behind / 20 ahead`，与文档 `05` 所述的 20 个提交一致。PR #11 的 `head_sha` 也是 `fd7f40b...`，即当前 `dev` 没有在 PR #11 后继续前进。

### 1.3 feat02 文档所在分支

feat02 文档位于 `chore/local-env-data` 的 `docs-work/feat02-后台管理/`，`dev` 当前没有该目录。已存在：

- `产品逻辑与页面交互设计总结.md`
- `01-用户与角色权限-PRD.md`
- `02-四类能力业务闭环-PRD.md`
- `03-页面交互与状态-SPEC.md`
- `04-端到端业务验收.md`
- `05-现有代码差距与实施路线图.md`
- `06-实施TASKS.md`

该分支同时提交了 `.gitignore` 的本地数据忽略规则和 `docs-codex/assistant-session-v1/DEPLOYMENT.md` 的本地数据说明；这些**不是本任务的文档产物**。后续如把 feat02 文档同步到 `dev`，必须只带文档文件，不能把整个 `chore/local-env-data` 差异作为一次变更合并。

### 1.4 文档编号差异（必须记录）

`06-实施TASKS.md` 是 F 编号唯一权威源：

| 阶段 | `06` 的任务 |
|---|---|
| G1-A | F02 数字账号/注册；F03 会话/RBAC；F04 恢复码/受控重置；F05 旧 Admin/审核/角色 API |
| G1-B | F06 用户入口与后台 UI；F07 会话归属/匿名认领 |

`05-现有代码差距与实施路线图.md` 的 G1 分组存在错位：

- 把 F04 写成“审核、角色、重置”，但 `06` 的 F04 是一次性恢复码与受控重置。
- 把 F05 写成“前端路由/导航/账号状态”，但 `06` 的 F05 是旧 Admin 迁移、用户审核与角色/停用 API。
- 把 F06 写成“会话 `user_id` 迁移与匿名历史认领”，但 `06` 的 F06 是用户/后台 UI。
- 把 F07 写成“私人数据隔离”，但 `06` 的 F07 是会话 `user_id` 归属和旧匿名认领。

本文件及后续任务卡一律按 `06` 的 F 编号，不沿用 `05` 的错位编号。

---

## 2. `dev` 源码与迁移基线

### 2.1 Alembic revision

源码中只有两个 revision：

| revision | down_revision | 内容 |
|---|---|---|
| `0001_assistant_sessions` | 无 | `conversations`、`messages`、Owner 索引、迁移键唯一约束 |
| `0002_admin_capabilities` | `0001_assistant_sessions` | `admin_users`、`admin_sessions`、能力定义/版本/依赖/Run、审计事件 |

当前源码 head：`0002_admin_capabilities`。

入口脚本 `backend/docker-entrypoint.sh` 在启动 Uvicorn 前执行：

```sh
python -m alembic upgrade head
```

CI 的 Backend job 也会在临时 SQLite 文件上执行：

```text
python -m alembic upgrade head
python -m alembic downgrade base
```

这只证明迁移链可在 CI 临时空库上升级和降级，**不证明**已有数据库、生产数据库或备份可恢复。

### 2.2 现有数据表

源码模型与迁移共同包含以下表：

| 领域 | 表 | 关键事实 |
|---|---|---|
| 匿名聊天 | `conversations` | `owner_id` 是签名 Cookie 对应的匿名字符串；`migration_key` 只用于浏览器本地迁移幂等 |
| 匿名聊天 | `messages` | 以 `conversation_id` 归属；无 `user_id` |
| 管理员 | `admin_users` | 独立 `username`、`password_hash`、`role`、`is_active`，不是普通用户表 |
| 管理员 | `admin_sessions` | 独立管理员 Cookie 会话；`token_hash`、`csrf_hash`、过期时间 |
| 能力 | `capability_definitions` | 四类能力共用定义表 |
| 能力 | `capability_versions` | 版本快照，已有发布/退役状态 |
| 能力 | `capability_dependencies` | 依赖关系，当前未见版本锁定字段 |
| 执行 | `capability_runs` | 以 `owner_id` 归属，`status=accepted` 是准入记录，不是真实执行终态 |
| 审计 | `audit_events` | 管理操作审计 |

没有 `users`、`user_sessions`、`user_recovery_codes`、`account_sequences`、注册幂等表或统一角色表。`/api/v1/auth/me` 在 `dev` 的测试中明确断言为 404。

### 2.3 当前管理员身份

- `AdminUser` 只有 `username`，没有数字账号、没有 Pending/Active 账户状态机。
- `hash_password()` 当前硬编码“至少 12 个字符”，是管理员策略，不是普通用户策略。
- `ensure_bootstrap_admin()` 在启动时如果发现 `ASSISTANT_ADMIN_PASSWORD` 与现有哈希不匹配，会更新管理员密码。这意味着环境变量变更可能在重启时覆盖人工改密，F05 必须改造。
- `admin_cli.py` 也是创建或更新管理员，当前同样强制 12 位。
- 登录限流是 `LoginLimiter` 的进程内字典，不是跨进程/多实例共享存储。
- 管理员会话 Cookie：`paiguangguang_admin`，HttpOnly、SameSite=Strict、生产 Secure；CSRF Cookie 可被同源前端读取。
- 管理写操作使用 `require_csrf()`：校验 Origin/Sec-Fetch-Site 与 `X-CSRF-Token`。

### 2.4 当前匿名 Owner

- `owner.py` 使用 HMAC-SHA256 签名 `owner_id`，Cookie 名默认 `paiguangguang_owner`。
- 会话 CRUD 全部通过 `Conversation.owner_id` 过滤；换浏览器或清 Cookie 会产生新的匿名 Owner。
- 当前没有“匿名 Owner → 登录 User”的认领 API；只有浏览器本地状态向服务端匿名 Owner 迁移的 `migration_key` 机制。
- 不能把 `owner_id` 直接改名为 `user_id`。F07 必须新增可空 `user_id`、保留 `owner_id`、做显式认领和冲突处理。

### 2.5 当前演示/模拟边界

- `main.py` 启动时无条件调用 `ensure_demo_catalog()`；Demo 能力初始状态为 `published`。
- 前端仍有 `createMockReply()` 和模拟 MCP 连接/任意 URL 输入。
- `capability_runs.status` 记录为 `accepted`，不是真实模型/工具执行完成。
- 这些是 F10/G2/G3 的已知缺口。F02 不得把 Demo 或模拟结果当作真实用户/能力闭环证据。

### 2.6 CI 与发布链路

`.github/workflows/assistant-session-ci.yml`：

- 触发：PR 到 `dev`/`main`（仅 backend/frontend/部署相关路径）、push 到 `dev`、可复用工作流、手动触发。
- Backend：Python 3.12、compileall、pytest、Alembic 临时库 upgrade/downgrade。
- Frontend：TypeScript、ESLint、Vitest、production build、Playwright。
- `docs-work/**` 不在触发路径内；**纯文档 PR 到 `dev` 不会触发该 CI**。

`.github/workflows/deploy.yml`：

- 仅 `push` 到 `main` 触发，先复用 CI，再构建双镜像、SSH 预检、在线 SQLite 备份、Compose 重启、健康检查、公开 HTTPS 健康检查、失败回滚。
- 备份使用 Python `sqlite3` 的 `backup()` API 写入 `/opt/paiguangguang-ai/backups`，备份失败会阻断发布。
- 回滚保存旧 Compose、`.env` 和前端镜像 ID；数据库迁移不自动逆向回滚。
- **该工作流没有 `paths` 过滤：任何 `main` 推送（包括 docs-only）都会触发生产部署。** 因此文档同步 PR 绝不能直接合入 `main`。

---

## 3. 本地运行环境与脱敏计数

### 3.1 环境边界

| 项目 | 结果 |
|---|---|
| 本地后端 | `http://127.0.0.1:8000/api/v1/health` 返回 `{"status":"ok","service":"paiguangguang-assistant"}` |
| 本地前端代理 | `http://127.0.0.1:3000/api/v1/health` 返回同样健康响应 |
| 监听进程 | 端口 8000 为本地 Python；端口 3000 为本地 Node |
| Docker daemon | 不可用：`dockerDesktopLinuxEngine` 管道不存在 |
| Docker 容器/命名卷 | NOT_VERIFIED，未读取 |
| 生产服务器 | NOT_VERIFIED，未连接 |
| 生产数据库 | NOT_VERIFIED，未读取 |

本地健康响应只证明健康端点可用，不证明认证、注册、迁移、权限或会话持久化。

### 3.2 本地数据库文件

| 文件 | 大小 | 说明 |
|---|---:|---|
| `.env/assistant.db` | 204,800 bytes | 活动本地库；存在 WAL/SHM |
| `.env/assistant.db-wal` | 82,432 bytes | 未合并的 WAL（预写日志） |
| `.env/assistant.db-shm` | 32,768 bytes | SQLite 共享内存文件 |
| `.env/_backup/assistant-20261108-022047.db` | 204,800 bytes | 本地候选备份；文件名时间看起来是 UTC，文件系统时间为本地 10:20:47 |

活动库是**本地开发数据**，不是生产副本。不能从这些数字推断生产用户规模。

### 3.3 本地活动库聚合计数（只读）

查询方式：Python `sqlite3` 以 `mode=ro` 打开，并执行 `PRAGMA query_only=ON`；未读取会话正文、消息正文、密码哈希、Token、恢复码或管理员用户名。

| 表 | 行数 |
|---|---:|
| `conversations` | 9 |
| `messages` | 4 |
| `admin_users` | 1 |
| `admin_sessions` | 2（按 `expires_at` 聚合的未过期数量） |
| `capability_definitions` | 24 |
| `capability_versions` | 24 |
| `capability_dependencies` | 0 |
| `capability_runs` | 0 |
| `audit_events` | 4 |

补充聚合：

- 不同 `owner_id` 数量：2。
- 每个 Owner 的会话数分桶：`1 个会话` 的 Owner 1 个；`6–20 个会话` 的 Owner 1 个。
- 孤儿消息（无对应会话）：0。
- 管理员按角色/启用状态：`admin` 且启用 1 个。
- SQLite 版本：3.53.1。
- `PRAGMA user_version`：0。

### 3.4 本地库迁移状态风险

**活动本地库没有 `alembic_version` 表**。它的表集合与 `0002` 名称相符，但说明该库是由 `init_db()` 的 `Base.metadata.create_all()` 路径创建，而不是由 Alembic 建立版本记录。

影响：

- 不能把这个本地库当作“已升级到 `0002`”的证据。
- 不能直接对它执行 `alembic upgrade head` 来证明迁移；在没有版本记录时，迁移可能重复建表失败。
- 不能擅自 `alembic stamp`；这会掩盖真实历史。若本地数据需要保留，必须由数据所有者先做独立快照并明确选择处理方式。
- F02 迁移验证应使用全新的临时数据库或获授权的独立副本，不能使用活动开发库做实验。

---

## 4. 备份与恢复证据

### 4.1 已观测到的候选备份

本地存在：

`C:\AI\paiguangguang-ai\.env\_backup\assistant-20261108-022047.db`

- 大小：204,800 bytes
- SHA-256：`15C2E3ED5C4B6DDF94030C888C8DD40E2AAC62C294B568D7858AE2950B153B4B`
- 同目录文件数：1
- 文件存在时间：本地文件系统 2026-11-08 10:20:47

这只是**候选备份文件存在性证据**，不是可恢复性证据。没有打开它、没有执行 `PRAGMA integrity_check`、没有恢复、没有做向前迁移，也没有核对会话/消息/管理员数量。

### 4.2 工作流具备的备份动作

`deploy.yml` 在启动新后端前会：

1. 检查数据卷和 `/data/assistant.db` 是否存在。
2. 用 Python `sqlite3.Connection.backup()` 复制到 host 的 `backups/assistant-<UTC>.db`。
3. 备份失败则中止部署。
4. 启动新容器，等待健康检查。
5. 公开 HTTPS 健康检查失败时恢复旧镜像/Compose/环境。

该动作只被源码阅读确认存在；**没有生产运行日志、备份清单、哈希、恢复日志或校验和**可供本轮复核。

### 4.3 恢复证据结论

| 证据 | 状态 |
|---|---|
| 生产备份是否存在 | NOT_VERIFIED |
| 备份是否由 SQLite backup API 生成 | PR 自述/工作流代码表明应如此；未对实际生产备份验证 |
| 备份完整性 | NOT_VERIFIED |
| 备份恢复到隔离环境 | NOT_VERIFIED |
| 恢复后旧管理员登录 | NOT_VERIFIED |
| 恢复后匿名会话与消息数量/归属 | NOT_VERIFIED |
| 迁移后向前启动 | NOT_VERIFIED |
| 旧镜像/旧数据库回滚 | NOT_VERIFIED |

PR #11 正文声称历史本地 Docker 验证包含“SQLite 备份完整性”，但该正文是历史主张，不是本轮可复现证据，不能替代授权演练。

---

## 5. PR #11 与 CI 最新状态

### 5.1 PR #11

| 字段 | 当前值 |
|---|---|
| 仓库 | `TotoroKingdom/paiguangguang-ai` |
| PR | [#11](https://github.com/TotoroKingdom/paiguangguang-ai/pull/11) |
| 状态 | open |
| Draft | true |
| Merged | false |
| Mergeable | true |
| Base | `main` @ `a301e5503e44b65560fdacd6ea734407dd87b7a1` |
| Head | `dev` @ `fd7f40bfe787d872f44da51a3003e1a45cf78216` |
| 变更规模 | 20 commits、146 files、+10,544/-479 |

PR 正文仍自述以下生产阻断：

- GitHub 缺少 `ASSISTANT_OWNER_COOKIE_SECRET` secret 与 `ASSISTANT_ALLOWED_ORIGINS` variable。
- 生产服务器没有监听 443、没有 TLS 证书，Nginx 仅提供 80 端口 HTTP。
- 部署账号没有可用的非交互 sudo，无法安全补齐反向代理/证书。
- `npm audit --omit=dev` 报告 1 critical / 3 high 生产依赖风险；critical 位于 Next.js 14.2.35，修复需要 breaking major upgrade。

以上是 PR 自述，不是本轮对服务器、密钥或依赖审计的实时验证。Q-07 仍为 `[待核验]/BLOCKED`。

### 5.2 GitHub Actions

最近 `dev` 相关运行：

| Run | 触发 | SHA | 结论 |
|---|---|---|---|
| [42396288984](https://github.com/TotoroKingdom/paiguangguang-ai/actions/runs/42396288984) | PR #11 | `fd7f40b...` | success |
| [42396283828](https://github.com/TotoroKingdom/paiguangguang-ai/actions/runs/42396283828) | push `dev` | `fd7f40b...` | success |

这说明当前 `dev` 的 Application CI 在 GitHub 上通过；不等于：

- 生产部署成功；
- 生产 TLS/密钥/Origin 正确；
- 生产数据库可恢复；
- 用户注册/激活/统一会话已实现。

### 5.3 发布路径风险

- 只有 `dev → main` 的 PR 合并后才可能触发部署；本轮没有合并或推送。
- `deploy.yml` 对 `main` 的任意 push 都会触发，不限制路径。文档-only 变更若误入 `main` 也会尝试生产部署。
- 因此 feat02 文档同步应只走 `dev` 的 docs-only PR；不得直接改 `main`。

---

## 6. 已验证项与未知项

### 6.1 已验证

- 当前 worktree、分支、HEAD、`dev`/`main` 远端 SHA。
- feat02 文档在 `chore/local-env-data`，不在 `dev`。
- `06` 与 `05` 的 G1/F 编号不一致。
- `dev` 源码只有 `0001`、`0002` 两个 migration，head 为 `0002_admin_capabilities`。
- `conversations.owner_id` 仍是匿名归属，所有会话 API 按 Owner Cookie 过滤。
- `admin_users`/`admin_sessions` 仍是独立管理员身份，不是统一用户表。
- 普通用户注册、统一会话、恢复码、Pending 激活 API 均不存在。
- 当前密码哈希函数强制管理员密码至少 12 位。
- 当前登录限流是进程内内存实现。
- 本地活动库只读计数；它没有 `alembic_version`。
- 本地候选备份文件存在；没有做完整性或恢复。
- PR #11 仍为 open/draft/mergeable，CI 最近成功。
- 本地 8000/3000 健康端点可用；Docker daemon 不可用。

### 6.2 未知或未验证

| 未知项 | 影响 |
|---|---|
| 生产数据库 revision、表、行数和 `owner_id` 分布 | 无法确认生产迁移起点和真实风险 |
| 生产 `admin_users` 数量/状态、旧管理员能否登录 | 无法确认 F05 迁移范围 |
| 生产备份文件、校验、保管位置、可恢复性 | F00 恢复门禁不能通过 |
| 生产 TLS、443、Origin、Secure Cookie | 生产登录/管理端可能不可用或不安全 |
| GitHub secrets/variables 是否已补齐 | Q-07 不能判定 |
| 生产 Docker 卷和容器状态 | 无法确认备份/回滚链路 |
| 生产依赖审计现状 | critical/high 风险是否仍存在未知 |
| 本地活动库的创建路径和是否可安全 stamp | 不能作为迁移测试库 |
| 旧管理员密码能否在统一用户哈希校验下继续使用 | 需 F05 在隔离副本验证 |
| 匿名 Owner 到登录用户的认领冲突规模 | 需 F07 生产/副本盘点 |
| 真实模型、Tool、MCP、Run | 不是 F00/F01 的完成证据；当前仍为模拟/准入状态 |

---

## 7. 风险清单

| ID | 风险 | 等级 | 当前处置 |
|---|---|---|---|
| F00-R01 | 没有生产备份的可恢复证据 | 阻断 | F00 不通过；先做获授权的隔离恢复演练 |
| F00-R02 | 本地库无 Alembic 版本记录 | 高 | 不使用活动库做迁移实验；新建临时库验证 |
| F00-R03 | 生产数据量、revision、管理员数量未知 | 高 | 只读生产盘点前不得制定精确回滚窗口 |
| F00-R04 | 现有启动逻辑可能覆盖管理员密码 | 高 | F05 必须改为一次性初始化，禁止重启隐式改密 |
| F00-R05 | 管理员与普通用户两套身份 | 高 | F03/F05 统一会话，旧身份只作受控桥接 |
| F00-R06 | `owner_id` 直接改 `user_id` 会串户/丢历史 | 高 | F07 新增可空字段，显式认领，保留旧字段 |
| F00-R07 | 当前登录限流只在进程内 | 高 | F01 要求共享存储或等效多实例方案 |
| F00-R08 | 12 位管理员策略与 6 位用户策略混淆 | 中高 | 哈希算法与密码策略分离 |
| F00-R09 | `chore/local-env-data` 含非文档变更 | 中高 | 只提交文档；同步到 `dev` 另建 docs-only PR |
| F00-R10 | `main` 任意 push 触发部署 | 高 | 文档不得直接合入 `main`；发布需单独审批 |
| F00-R11 | 24 个 Demo 能力无条件发布、前端模拟回复 | 高（后续） | F10/G3 前不得宣称真实执行 |
| F00-R12 | PR #11 的 TLS/密钥/依赖阻断未实时复核 | 阻断（发布） | G4 前重新核验，不能以 CI 绿灯替代 |

---

## 8. 迁移契约（设计稿，未实施）

> 以下仅定义 F02～F07 的安全迁移边界，不是本轮代码。实际 revision 名称和字段必须在对应任务卡评审后确定。

### 8.1 总原则

1. **Expand first（先扩展）**：先新增表/可空字段/索引，不删除旧表、不重命名 `owner_id`、不清空旧数据。
2. **旧系统保留**：`conversations`、`messages`、`admin_users`、`admin_sessions` 在迁移窗口内保留；旧数据不自动改归属。
3. **一个任务一个 revision**：每个任务基于当时最新 head 新建 revision，不复用 revision ID，不并行改同一迁移文件。
4. **生产不执行破坏性回滚**：已写入的新用户/新会话不能靠 `downgrade` 删除；需要恢复到迁移前快照时必须先停写、校验备份、再恢复。
5. **迁移与审计同事务**：管理员映射、角色变更、激活/停用等管理操作与审计写入同事务提交。
6. **无明文秘密**：迁移只复制已有密码摘要（hash），绝不导出明文密码、恢复码或 Cookie。
7. **失败 Fail Closed（失败关闭）**：迁移失败时停止新入口，不回退到匿名正式写入或 Demo 伪成功。

### 8.2 建议 revision 序列

| 任务 | 建议 revision | 内容 | 是否改旧表 |
|---|---|---|---|
| F02 | `0003_identity_users` | `users`、`account_sequences`、注册幂等表 | 否 |
| F03 | `0004_identity_sessions` | `user_sessions`、共享限流记录、统一权限依赖所需字段 | 否 |
| F04 | `0005_identity_recovery` | `user_recovery_codes`、恢复/轮换审计所需字段 | 否 |
| F05 | `0006_identity_admin_links` | `admin_user_links` 或等价映射；一次性旧 Admin 映射 | 否；旧表保留 |
| F07 | `0007_conversation_user_ownership` | `conversations.user_id`、相关索引/约束；认领审计；旧 `owner_id` 保留 | 只新增可空列/索引 |

`capability_runs.user_id`、个人 Skill/文件/MCP 归属属于 G2，不应塞进 F02。

### 8.3 账号分配契约

- `users.id`：内部 UUID，稳定主键。
- `users.account_number`：用户可见登录号，存为**十进制字符串**，无前导零；唯一约束。
- `account_sequences`：单行计数器，初始 `next_account_number='100'`；管理员初始号不消耗该序列。
- 注册事务在 SQLite 上用 `BEGIN IMMEDIATE` 或等效的单写者序列化，读取十进制计数、在应用层做任意精度 `int` 递增、更新回文本、插入用户、写幂等记录，然后提交。
- 禁止 `MAX(account_number)+1`；禁止把账号当浮点数、科学计数法或三位数 ID。
- 唯一约束是最后防线；并发/重试不得让两个人拿到同一账号。
- 产品层不设 999/9999 或固定位数上限。SQLite `TEXT` 和 Python 大整数提供实际容量；技术容量应在运行手册中记录，但不得在 UI/API 暴露成产品上限。
- 账号永不回收：拒绝、停用、删除申请都不应把号码分配给下一个人。

### 8.4 注册幂等契约

- 客户端必须提供 `Idempotency-Key`（UUID 或等价高熵值）。
- 服务端只存 key 的摘要，不存原 key。
- 同 key + 同请求体：返回同一注册结果，不重复消耗账号。
- 同 key + 不同请求体：`409 IDEMPOTENCY_CONFLICT`，不得改绑到新用户。
- 注册失败回滚计数器、用户和幂等记录，或让失败记录处于不可重放终态；不能出现“号码已消耗但没有用户”的静默状态。

### 8.5 用户状态与约束

- `users.status` 至少支持 `PENDING`、`ACTIVE`、`DISABLED`、`REJECTED`。
- `users.role` 至少支持 `USER`、`CREATOR`、`ADMIN`；角色与状态正交。
- 注册只创建 `USER + PENDING`；请求体不得指定 `accountNumber`、`role`、`status`。
- 只有 Admin 激活后 `ACTIVE` 才能使用正式业务 API。
- 停用/拒绝不自动删除历史；会话在停用/拒绝时撤销。
- 最后一个有效 Admin 不能被停用或降级。

### 8.6 旧管理员映射契约

- 新增映射表，例如 `admin_user_links(legacy_admin_id, user_id, migrated_at, migration_source)`；不改写旧 `admin_users` 的历史记录。
- 受信任一次性迁移可复制旧 `password_hash` 到新 `users.password_hash`；不复制明文，不重新设置密码。
- 首个 bootstrap Admin 使用保留号（建议 `1`，不占普通 `100` 序列）；普通注册计数器仍从 `100` 开始。
- 迁移后 `admin_users` 只作历史/审计参考；新管理会话统一写 `user_sessions`。
- `ensure_bootstrap_admin()` 的持续覆盖行为必须移除或改为显式一次性 bootstrap；生产重启不得改变人工修改后的密码。

### 8.7 旧匿名会话契约

- F07 新增 `conversations.user_id`（可空），保留 `owner_id`。
- 用户认领时同时验证：有效登录用户 + 旧 Owner Cookie 签名 + 会话当前不属其他用户。
- 认领必须原子、幂等、可审计；失败不删除旧记录。
- 不自动把匿名历史绑定给当前用户；不跨浏览器、不跨账号自动合并。
- 完成 G1 证据前，不清除 `owner_id` 或旧 Cookie。

### 8.8 数据不变量

迁移前后必须核对以下**聚合量**，不读取正文：

- `conversations` 总数、按 Owner 的会话数分布。
- `messages` 总数、孤儿消息数、每个会话消息数分布。
- `admin_users` 总数、角色/启用状态分布。
- `admin_sessions` 总数、未过期数量。
- 能力定义/版本/依赖/Run/审计事件数量。
- 旧 `admin_users.password_hash` 迁移前后是否保持同一摘要格式与可验证性（只在受控环境验证，不输出哈希）。
- 新 `users.account_number` 唯一、无前导零、无重复；计数器下一个值与用户最大号一致。
- `PRAGMA foreign_key_check`、`PRAGMA integrity_check` 在**获授权的独立副本**上执行。

---

## 9. 迁移与回滚步骤（计划，不执行）

### 9.1 未来正式迁移前置

1. 冻结代码 SHA、镜像 SHA、数据库副本和迁移 revision。
2. 停止所有写入；对 SQLite 主库使用 backup API 生成一致快照，保留 WAL/SHM 关系说明。
3. 把快照复制到独立环境；记录 SHA-256、大小、SQLite 版本、表/索引列表。
4. 在独立环境执行 `PRAGMA integrity_check`、`foreign_key_check` 和迁移前后的脱敏计数。
5. 在独立环境从快照执行 `alembic upgrade head`，启动新代码，验证旧管理员登录、旧会话可读、旧消息数/归属不变。
6. 在独立环境执行回滚演练：停新应用、恢复快照、启动旧镜像、验证旧管理员和旧会话。
7. 记录每一步命令、结果、耗时、失败点和证据文件。

### 9.2 生产发布顺序

1. 运行 CI 与迁移测试。
2. 生产只读预检：磁盘、revision、表计数、备份列表、TLS/Origin、当前镜像。
3. 自动/人工 SQLite 一致备份；记录哈希并复制到独立介质或至少独立目录。
4. 部署新镜像，入口执行 `alembic upgrade head`。
5. 健康检查、同源 API、管理员旧登录/新登录、会话创建/消息持久化/刷新恢复。
6. 任一步失败：停止新写入，恢复旧镜像；若 schema 不兼容，先恢复备份再启动旧镜像。
7. 记录 `.deployment-record` 与验收证据。

### 9.3 回滚边界

- 代码回滚：恢复旧前端/后端镜像、旧 Compose 与旧 `.env`。
- 数据库回滚：只在 schema 不向后兼容或数据被错误写入时，使用**迁移前**快照恢复；恢复前必须停止写入并确认目标库身份。
- 禁止：
  - `docker compose down -v`
  - 删除命名卷
  - 直接 `downgrade` 后继续生产写入
  - 用 `stamp` 掩盖本地无版本记录
  - 用生产库做 `integrity_check`/迁移实验
  - 把“备份文件存在”当作“恢复成功”
- 已写入的新用户/新消息不能通过删除表来“回滚”；必须恢复到一致的迁移前快照，并明确数据丢失窗口。

---

## 10. F00 产物与后续任务卡

### 10.1 F00 判定

**BLOCKED。**

- 静态基线、源码审查、本地聚合盘点完成。
- 但 F00 的验收要求包含“旧数据可恢复、旧管理员可登录、迁移失败可回退”的证据；本轮没有明确授权执行恢复演练，也没有生产/预发布环境访问。
- 在没有这些证据前，不能把 F00 标为 PASSED，也不能用 CI upgrade/downgrade 代替真实备份恢复。

### 10.2 解除 F00 阻断所需最小证据

1. 一份**明确授权的独立数据库副本**（不是生产库本身），带 SHA-256、大小、生成时间。
2. 隔离环境中的 `integrity_check`、`foreign_key_check` 结果。
3. 恢复后旧 `admin_users` 登录与匿名会话/消息计数核对结果。
4. `0002 → 新 head` 的前向迁移结果和旧应用回退结果。
5. 生产只读盘点的脱敏报表：revision、表计数、管理员数量、Owner 分布、备份清单。
6. PR #11 的 TLS/443、secrets/variables、部署权限、依赖审计实时复核。

### 10.3 建议的最小任务卡

| 卡片 | 范围 | 产出 | 门禁 |
|---|---|---|---|
| `F00-A` 独立副本恢复演练 | 获授权副本、隔离临时目录、SQLite backup/integrity、旧应用启动 | 恢复证据报告 + 校验值 | 不触碰生产；失败即 BLOCKED |
| `F00-B` 生产只读盘点 | SSH 只读、容器/卷/备份/revision/计数 | 脱敏 preflight 报告 | 不读秘密值、不改环境 |
| `F01-A` Q-02 人工恢复 SOP | 身份核验、双人审批、票据交付、审计 | 安全决策审批记录 | 未批准则管理员重置保持关闭 |
| `F01-B` Q-03 旧 Admin 映射 | 保留号、哈希迁移、一次性 bootstrap、旧路由退役 | 迁移契约 | 不覆盖人工改密 |
| `F02-0` 账户模型与迁移 | `users`、账号分配、幂等注册、测试 | 独立 migration + 测试 | F00 PASSED、F01 账号/密码规则冻结 |

---

## 11. 复核命令（只读）

以下命令记录本轮使用的可复现检查；均不写生产、不删卷、不改代码。

```powershell
git status --short --branch
git worktree list
git rev-parse dev
git rev-parse main
git rev-parse HEAD
git rev-list --left-right --count origin/dev...dev
git rev-list --left-right --count origin/main...main
git ls-tree -r --name-only chore/local-env-data -- docs-work/feat02-后台管理
git show dev:backend/alembic/versions/0001_assistant_sessions.py
git show dev:backend/alembic/versions/0002_admin_capabilities.py
git show dev:backend/app/modules/identity/models.py
git show dev:backend/app/modules/identity/service.py
git show dev:backend/app/owner.py
git show dev:backend/app/routers/conversations.py
git show dev:.github/workflows/deploy.yml
```

本地数据库只读检查使用 `sqlite3` 的 `mode=ro` 和 `PRAGMA query_only=ON`，只查询 `COUNT(*)`、`COUNT(DISTINCT owner_id)` 和分桶，不查询正文、哈希、Token 或恢复码。

---

## 12. 参考

- [feat02 总纲](https://github.com/TotoroKingdom/paiguangguang-ai/blob/chore/local-env-data/docs-work/feat02-%E5%90%8E%E5%8F%B0%E7%AE%A1%E7%90%86/%E4%BA%A7%E5%93%81%E9%80%BB%E8%BE%91%E4%B8%8E%E9%A1%B5%E9%9D%A2%E4%BA%A4%E4%BA%92%E8%AE%BE%E8%AE%A1%E6%80%BB%E7%BB%93.md)
- [01 用户与角色权限 PRD](https://github.com/TotoroKingdom/paiguangguang-ai/blob/chore/local-env-data/docs-work/feat02-%E5%90%8E%E5%8F%B0%E7%AE%A1%E7%90%86/01-%E7%94%A8%E6%88%B7%E4%B8%8E%E8%A7%92%E8%89%B2%E6%9D%83%E9%99%90-PRD.md)
- [02 四类能力业务闭环 PRD](https://github.com/TotoroKingdom/paiguangguang-ai/blob/chore/local-env-data/docs-work/feat02-%E5%90%8E%E5%8F%B0%E7%AE%A1%E7%90%86/02-%E5%9B%9B%E7%B1%BB%E8%83%BD%E5%8A%9B%E4%B8%9A%E5%8A%A1%E9%97%AD%E7%8E%AF-PRD.md)
- [03 页面交互与状态 SPEC](https://github.com/TotoroKingdom/paiguangguang-ai/blob/chore/local-env-data/docs-work/feat02-%E5%90%8E%E5%8F%B0%E7%AE%A1%E7%90%86/03-%E9%A1%B5%E9%9D%A2%E4%BA%A4%E4%BA%92%E4%B8%8E%E7%8A%B6%E6%80%81-SPEC.md)
- [04 端到端业务验收](https://github.com/TotoroKingdom/paiguangguang-ai/blob/chore/local-env-data/docs-work/feat02-%E5%90%8E%E5%8F%B0%E7%AE%A1%E7%90%86/04-%E7%AB%AF%E5%88%B0%E7%AB%AF%E4%B8%9A%E5%8A%A1%E9%AA%8C%E6%94%B6.md)
- [05 现有代码差距与实施路线图](https://github.com/TotoroKingdom/paiguangguang-ai/blob/chore/local-env-data/docs-work/feat02-%E5%90%8E%E5%8F%B0%E7%AE%A1%E7%90%86/05-%E7%8E%B0%E6%9C%89%E4%BB%A3%E7%A0%81%E5%B7%AE%E8%B7%9D%E4%B8%8E%E5%AE%9E%E6%96%BD%E8%B7%AF%E7%BA%BF%E5%9B%BE.md)
- [06 实施 TASKS（唯一 F 编号源）](https://github.com/TotoroKingdom/paiguangguang-ai/blob/chore/local-env-data/docs-work/feat02-%E5%90%8E%E5%8F%B0%E7%AE%A1%E7%90%86/06-%E5%AE%9E%E6%96%BDTASKS.md)
- [PR #11](https://github.com/TotoroKingdom/paiguangguang-ai/pull/11)
- [`dev` 迁移目录](https://github.com/TotoroKingdom/paiguangguang-ai/tree/fd7f40bfe787d872f44da51a3003e1a45cf78216/backend/alembic/versions)
- [`dev` 部署工作流](https://github.com/TotoroKingdom/paiguangguang-ai/blob/fd7f40bfe787d872f44da51a3003e1a45cf78216/.github/workflows/deploy.yml)
