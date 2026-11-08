# feat02 智能助手平台 V1｜连续执行报告

> 日期：2026-11-08
> 分支：`feat/feat02-platform-v1`（worktree `C:\AI\paiguangguang-ai-feat02`，从 `dev` `fd7f40b` 建立）
> 状态：开发环境连续实现；**未合并 `dev`、未触碰 `main`、未部署生产**。

## 1. 交付摘要

本轮从 F00 未完成项继续，完成 G0 开发门禁证据、G1 统一身份与权限、G2 能力治理与个人资源、G3 Fake/真实 Provider 双路径 Runtime，以及 G4 可本地执行的安全回归。

自动化结果：

- 后端：`46 passed`（`python -m pytest tests -q`；含 MCP 协议、工具发现、Runtime 调用、超时与取消）。
- 前端：`76 passed`（`npm test`）。
- Playwright：现有 64 条回归 + 2× 账号闭环 + 2× 个人资源闭环 + 2× Creator 审核发布，共 70 条通过（桌面/移动）。
- 前端 TypeScript：`npx tsc --noEmit` 通过。
- 前端 ESLint：`npm run lint` 通过。
- 前端生产构建：`npm run build` 通过（30 个路由）。
- Alembic：`0001 → 0008`、`downgrade base`、再次 `upgrade head` 均通过；`integrity_check=ok`。
- 依赖审计：前端生产依赖 0 critical/high；后端 `pip-audit` 无已知漏洞（详见 `DEPENDENCY-AUDIT.md`）。

## 2. 任务状态

| 任务 | 状态 | 说明 |
|---|---|---|
| F00 | PARTIAL | 本地独立副本完整性、恢复、Schema 对比、迁移/回退演练通过；生产盘点与恢复仍 BLOCKED |
| F01 | PARTIAL | 账号/密码/会话/恢复码/限流/迁移规则已冻结并实现；Q-02 人工恢复、Q-03 正式切换、Q-07 生产安全未获批 |
| F02 | PASSED（自动化） | `users`、`account_sequences`、幂等注册、100 起步、跨位数、并发唯一 |
| F03 | PASSED（自动化） | 统一登录、`FULL/STATUS_ONLY`、RBAC 服务端守卫、CSRF/Origin、会话撤销 |
| F04 | PARTIAL | 自助恢复码、改密、轮换、会话吊销完成；管理员辅助重置保持关闭（BLOCKED） |
| F05 | PASSED（自动化 + 副本演练） | 旧管理员映射账号 `1`、摘要逐字复制、审核/停用/恢复/角色 API、最后管理员保护 |
| F06 | PASSED（E2E） | 注册/登录/成功/待审核/个人中心/用户管理/创作中心/审核发布页面完成；账号闭环与 Creator 审核发布均有桌面/移动 E2E |
| F07 | PASSED（自动化） | `user_id` 归属、跨浏览器读取、匿名签名认领、跨用户 404 |
| F08 | PASSED（自动化） | 能力所有者、可见范围、`all_active/granted` ACL、停用后拒绝 |
| F09 | PASSED（自动化 + E2E） | Creator 测试→提交→Admin 审核→发布、审计、版本回滚接口；创作中心与审核发布页桌面/移动 E2E |
| F10 | PARTIAL | 正式目录过滤 Demo、生产强制关闭演示、非授权不显示；开发默认保留 Demo；前端访客仍保留明确标注的模拟回复；历史 Demo 未做归档迁移 |
| F11 | PASSED（自动化 + E2E） | 个人 Skill 服务端 CRUD、Markdown 导入、所有者隔离、Runtime 加载；服务端文件上传/下载/删除/正文校验；登录态前端已切换到服务端个人资源 |
| F12 | PASSED（自动化 + E2E） | 平台批准 MCP Server、管理端登记/发现工具、个人连接、Token Fernet 加密、未批准拒绝、Token 不回显；登录态 UI 只显示已批准服务且无任意 URL 输入；外部真实 Server 为 NOT_RUN |
| F13 | PARTIAL | OpenAI-compatible 流式适配器、Fake Provider、SSE 端点、Run 终态持久化完成；真实模型调用 NOT_RUN |
| F14 | PASSED（自动化） | Tool Gateway、参数 Schema 校验、2 个只读工具、大小/超时/副作用限制 |
| F15 | PARTIAL | MCP Client、工具发现、个人授权调用、最小 Agent Loop、Run/RunStep/RunTrace、取消/超时/失败代码完成；MCP 协议与 Runtime 调用用本地注入传输验证；外部真实 MCP NOT_RUN |
| F16 | BLOCKED | 依赖 critical/high 已清除（Next 16、FastAPI/Starlette/cryptography 升级）；生产 TLS、443、Secure Cookie、密钥、部署权限仍未核验 |
| F17 | PARTIAL | 38 场景矩阵：19 PASS / 16 PARTIAL / 3 BLOCKED（`G4-ACCEPTANCE-MATRIX.md`）；Playwright 70 条通过；真实模型/真实 MCP/生产仍阻断 |

## 3. 数据库与 API

新增 revision：

- `0003_identity_users`
- `0004_identity_sessions`
- `0005_conversation_user_ownership`
- `0006_capability_governance`
- `0007_personal_resources`
- `0008_runtime_runs`

新增主要 API：

- `/api/v1/auth/register|login|session|logout|password/change|recovery/complete|recovery/rotate`
- `/api/v1/me/status`、`/api/v1/me`、`/api/v1/me/legacy-conversations/claim`
- `/api/v1/admin/users*`
- `/api/v1/creator/capabilities*`
- `/api/v1/admin/capabilities/{id}/approve|reject|grants|rollback`
- `/api/v1/admin/governance/capabilities*`
- `/api/v1/me/skills`、`/api/v1/me/files`、`/api/v1/me/mcp/connections`
- `/api/v1/mcp/servers`、`/api/v1/admin/mcp/servers*`
- `/api/v1/assistant/runs`、`/api/v1/assistant/runs/stream`、`/api/v1/assistant/runs/{id}/cancel`

Schema 变化全部为 Expand（先扩展）：保留 `admin_users`、`admin_sessions`、`owner_id`、匿名会话与历史 Demo。

## 4. 兼容性

- 旧 `/api/v1/admin/auth/*` 与管理能力控制台仍可使用，作为迁移窗口桥接。
- 新 `/api/v1/admin/users`、`/api/v1/admin/mcp/*`、`/api/v1/admin/governance/*` 使用统一会话。
- 旧匿名聊天仍可访问；登录用户新建聊天写 `user_id`；旧匿名会话不会被自动认领。
- 旧管理员表不删除；`ensure_unified_admin()` 只创建缺失映射，不覆盖已人工修改的密码。

## 5. 安全验证

已由自动化覆盖：

- 账号从 100 起步、跨 999/9999、并发唯一、幂等冲突。
- 6 位密码边界、弱密码、请求注入账号/角色被拒绝。
- Pending 会话越权、停用后会话失效、恢复码重放失败。
- 跨用户会话、Skill、文件、MCP 连接隔离。
- 无 CSRF、外站 Origin 写操作拒绝。
- 最后管理员保护。
- 未批准 MCP Server 连接拒绝，响应不含 Token。
- 未配置真实模型时返回失败 Run，不回落模拟成功。

未验证：

- 38 个验收场景的逐条冻结证据与新增 Runtime/能力管理页面的完整浏览器覆盖。
- 真实模型、真实 MCP Server、真实外部 Tool。
- 生产恢复、TLS、依赖审计、部署回滚。

## 6. 真实执行与模拟证据区分

- `mode=fake`：Fake Provider，仅用于自动化与开发联调；输出明确带 `[FakeProvider]`。
- `mode=openai`：代码已实现 OpenAI-compatible 流式适配；本轮未配置密钥，测试结果为 `REAL_PROVIDER_NOT_CONFIGURED`，**不是真实调用成功**。
- MCP：注册、批准、工具发现、个人授权、凭据加密与 Runtime 调用已用本地 MockTransport 验证；未连接外部 MCP Server，真实外部 `tools/list` 与调用为 **NOT_RUN**。
- `capability_runs.status=accepted` 仍只代表旧准入事件，不代表真实执行完成。

## 7. 仍阻断的事项

1. **管理员辅助重置密码**：无可信身份核验 SOP、双人复核与票据交付规则；API/UI 未实现。
2. **生产环境 F00/F16**：无生产只读盘点、备份恢复、TLS/443、Secure Cookie、GitHub secrets、依赖审计证据。
3. **Q-03 旧管理员正式退役**：旧管理端仍作为兼容桥接，双权威源尚未关闭。
4. **真实 Runtime 联调**：无模型密钥、无已批准外部 MCP Server，真实调用 NOT_RUN。
5. **完整 38 场景 E2E**：未执行浏览器级验收，不能宣称 V1 全量闭环。

## 8. 下一步

1. 在获授权的隔离环境执行生产副本的 F00 只读盘点与恢复演练。
2. 补齐真实模型密钥与已批准 MCP Server 后，跑 R-01～R-06 真实联调。
3. 补齐个人 Skill 编辑/版本历史、聊天附件正文读取与 MCP 工具级权限细化。
4. 补齐 38 个验收场景的逐条证据表与剩余 Runtime/能力页面 E2E。
5. 生产发布前完成 TLS、Secure Cookie、Origin、生产镜像依赖复核与回滚演练。
