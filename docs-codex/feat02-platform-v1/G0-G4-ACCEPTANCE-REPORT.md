# feat02 智能助手平台 V1｜G0–G4 验收报告

> 日期：2026-11-08
> 代码基线：`dev` `e7de102` + 本轮安全响应头与验收报告提交
> 环境：local（Windows）+ GitHub Actions（ubuntu-latest）
> 生产：**未连接、未部署、未验收**
> 总体结论：**开发环境可执行范围已交付；完整 V1 仍为 BLOCKED**。

## 1. 交付结论

| Gate | 结论 | 依据 |
|---|---|---|
| G0 安全与迁移 | PARTIAL | 本地副本恢复/迁移/回退演练通过；生产盘点与恢复未执行 |
| G1 身份与权限 | PASS（开发环境） | 账户、会话、RBAC、恢复码、审核、匿名认领自动化与 E2E 通过；人工恢复单独 BLOCKED |
| G2 能力治理 | PASS（开发环境） | 四类能力 ACL、审核发布、版本回滚、个人 Skill/文件、MCP 授权通过 |
| G3 Runtime | PARTIAL / BLOCKED | Fake、Tool、MCP、Agent、Run/Trace 自动化通过；真实模型与外部 MCP 未联调 |
| G4 生产与全量回归 | BLOCKED | 生产 TLS/密钥/恢复未核验；38 场景为 23 PASS / 12 PARTIAL / 3 BLOCKED |

## 2. 自动化证据

| 检查 | 结果 |
|---|---|
| 后端 `pytest` | **57 passed** |
| 前端 `vitest` | **76 passed** |
| Playwright | **70 passed**（desktop + mobile） |
| TypeScript | 通过 |
| ESLint 10 | 通过 |
| Next.js 16 production build | 通过 |
| Alembic | `0001 → 0009`，`0009 ↔ 0008` 通过 |
| 前端生产依赖审计 | 0 critical / 0 high / 0 moderate |
| 后端 `pip-audit` | No known vulnerabilities |
| GitHub Actions | 所有已合并 PR 的两项必需检查均 success |

## 3. 数据库

迁移：

- `0003_identity_users`
- `0004_identity_sessions`
- `0005_conversation_user_ownership`
- `0006_capability_governance`
- `0007_personal_resources`
- `0008_runtime_runs`
- `0009_agent_dependency_versions`

F00 本地演练：

- 快照 SHA-256：`429e0ffd29a4bcb984b029d5aa5223a6999b2d405d625255dfd302ef26648dde`
- 快照与恢复库字节一致，`integrity_check=ok`
- 迁移前后保持 `9 conversations / 4 messages / 1 admin`
- 旧管理员 PBKDF2 摘要逐字复制到账号 `1`
- 回退到 `0002` 后旧数据计数不变

生产 revision、表计数、备份恢复尚未核验。

## 4. 38 场景

| 集合 | PASS | PARTIAL | BLOCKED |
|---|---:|---:|---:|
| U-01～U-17 | 15 | 1 | 1 |
| C-01～C-10 | 7 | 3 | 0 |
| R-01～R-06 | 0 | 5 | 1 |
| O-01～O-05 | 1 | 3 | 1 |
| **合计** | **23** | **12** | **3** |

逐条证据见 `G4-ACCEPTANCE-MATRIX.md`。

## 5. 真实 / 模拟证据

| 依赖 | 状态 | 证据 |
|---|---|---|
| Fake LLM | PASS（L3） | `[FakeProvider]` 输出、持久化终态、SSE |
| 真实 OpenAI-compatible 模型 | PARTIAL（本地适配器）/ BLOCKED（真实供应商） | 本地 SSE 成功流与 503 失败已验证；真实供应商无密钥、未调用 |
| Tool Gateway | PASS（L3） | 只读工具、JSON Schema、参数/结果上限 |
| MCP Client / 发现 / Runtime 调用 | PASS（L3） | MockTransport 与真实 loopback HTTP 均验证 `tools/list`、`tools/call`、Bearer、RunStep(type=mcp) |
| 外部真实 MCP Server | NOT_RUN | 未获批准外部服务，不访问未知地址 |
| 生产 HTTPS/部署 | BLOCKED | 未连接生产 |

## 6. 安全响应头

本轮新增：

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

TLS/HSTS 仍由生产反向代理负责，未在生产核验。

## 7. 仍阻断

1. 管理员辅助重置：无可信身份核验 SOP、双人复核与票据交付规则。
2. 真实 LLM：无批准密钥、模型与预算。
3. 真实外部 MCP Server：无批准测试服务。
4. 生产 HTTPS/443、证书、反代、Secure Cookie、GitHub secrets、部署权限。
5. 生产备份恢复、旧管理员真实登录、容器重启数据保留。
6. R-05 模型流开始后的并发撤权、R-06 断网恢复未专项 E2E。
7. C-10 预算不足/外部授权的精确前端优先级未完整覆盖。

## 8. 发布判定

- 当前可交付：开发环境阶段性成果评审。
- 不可交付：生产 V1 上线、完整 38 场景闭环、真实 AI 执行闭环。
- `main` 未合并、未部署；生产发布继续 BLOCKED。

## 9. 生产发布前清单

1. 生产只读盘点与备份恢复演练。
2. 配置 TLS/443、HTTPS Origin、Secure Cookie、真实 LLM Key。
3. 在隔离副本执行 `0009` 迁移与旧管理员登录。
4. 生产烟测注册 → Pending → 激活 → 登录 → 会话 → 刷新 → 文件 → 重启保留。
5. 完成真实模型、真实 Tool、真实 MCP、Agent Run 脱敏证据。
6. 完成 R-05/R-06、C-10 与剩余 UI 状态。
7. 通过最终 G4 评审后才允许 `dev → main`。
