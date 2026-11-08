# feat02 / F01 开发环境安全决策冻结记录

> 日期：2026-11-08
> 性质：在 F01 原契约基础上，记录本轮**已落地到开发实现**的默认值与仍被阻断的事项。
> 结论：开发环境默认值可执行；**人工辅助重置、旧管理员正式切换审批、生产发布仍为 BLOCKED**。

## 1. 已实现的确定性规则

| 编号 | 规则 | 实现位置 |
|---|---|---|
| D-01 | 普通用户账号从 `100` 开始，按成功注册递增，使用十进制整数运算，不使用字符串排序 | `identity/user_service.py`、`account_sequences` |
| D-02 | 请求体不能指定账号、角色、状态；额外字段直接 422 | `RegisterRequest(extra="forbid")` |
| D-03 | 普通用户密码最低 6 位、最长 128 位；拒绝常见弱口令、单字符重复、连续序列、等于账号/昵称 | `validate_user_password` |
| D-04 | 管理员初始化仍保持 12 位最低长度，已与普通用户策略分离 | `hash_password(min_length=12)` / `hash_user_password()` |
| D-05 | 注册默认 `USER + PENDING`；非 `ACTIVE` 只能获得 `STATUS_ONLY` 会话 | `UserIdentityService.register/login` |
| D-06 | 每个用户同时只有 1 枚有效恢复码；192-bit 随机值；服务端只存 HMAC-SHA-256 摘要 | `new_recovery_code` / `recovery_hash` |
| D-07 | 恢复成功、改密、主动轮换都会使旧恢复码失效并签发新码；新码只在本次响应出现 | `_issue_recovery_code` |
| D-08 | 恢复码明文不写数据库、日志、URL、localStorage 或 sessionStorage；前端仅保存在内存 Provider | `user_router.py`、`auth/provider.tsx` |
| D-09 | 登录/注册/恢复使用数据库共享限流，不依赖进程内计数 | `auth_rate_events`、`DbRateLimiter` |
| D-10 | 统一会话 Cookie 为 HttpOnly、SameSite=Strict，生产必须 Secure；写操作要求 Origin + CSRF | `user_router.py`、`dependencies.py` |
| D-11 | 停用、改密、恢复、角色变更会提升 `authz_version` 并撤销旧会话 | `UserIdentityService` |
| D-12 | 最后一个有效管理员不能被停用或降级 | `LAST_ADMIN_PROTECTED` |
| D-13 | 旧管理员使用保留账号 `1`，复制原 PBKDF2 摘要，新增 `admin_user_links`，不删除旧表 | `ensure_unified_admin` |
| D-14 | 启动时不再用环境变量覆盖已有管理员密码 | `AdminIdentityService.ensure_bootstrap_admin` |
| D-15 | `owner_id` 保留；新增可空 `conversations.user_id`；认领必须同时具备登录用户与旧 Owner 签名 Cookie | `0005`、`/me/legacy-conversations/claim` |
| D-16 | 普通用户只能连接 `approved` MCP Server；服务端无“用户提交任意 URL”接口 | `personal/router.py`、`mcp_client.validate_mcp_url` |
| D-17 | Demo 目录默认不在生产自动发布；`demo_catalog_enabled` 默认 false，生产为 true 时启动失败 | `config.py`、`capabilities/service.py` |
| D-18 | 执行额度默认每用户每日 20 次 Run、单 Run 120 秒、最多 6 步 | `config.py`、`RuntimeService` |

## 2. 限流默认值

| 入口 | 默认值 |
|---|---|
| 注册 | 10 次/小时/IP；50 次/天/IP |
| 登录 | 5 次/15 分钟/账号+IP；20 次/15 分钟/IP |
| 恢复码 | 5 次/小时/账号+IP；20 次/天/IP |
| 管理端旧登录 | 保留原有 5 次/5 分钟/锁 15 分钟 |

限流键使用 HMAC 摘要存储，不保存明文账号或 IP。

## 3. 明确保持关闭或阻断

| 事项 | 状态 | 原因 |
|---|---|---|
| 管理员辅助重置密码 | **BLOCKED / 未实现** | 无可信人工身份核验 SOP、双人复核与票据交付规则；路由不存在 |
| “输入账号即生成临时密码” | 禁止 | 违反安全红线 |
| 生产注册入口 | **未放行** | 需要生产 TLS、Secure Cookie、密钥与恢复演练；开发默认 `registration_enabled=true` 不代表生产放行 |
| 旧管理员正式退役旧 `/admin/auth/*` | 暂缓 | 旧管理端与能力控制台仍使用兼容桥接；双权威源尚未关闭 |
| Q-03 旧管理员切换窗口审批 | 待产品/运维批准 | 本轮仅在隔离副本验证映射 |
| Q-07 生产 TLS/密钥/依赖 | **BLOCKED** | 未访问生产环境 |

## 4. 开发环境可执行的确定断言

1. 空库注册返回 `100`，随后 `101`；`999→1000`、`9999→10000`。
2. 6 个并发注册得到 6 个不同账号，无重复。
3. 同一幂等键重试不重复发号；不同请求体返回 `409 IDEMPOTENCY_CONFLICT`。
4. `PENDING` 登录只能访问状态接口，聊天 API 返回 403。
5. 管理员激活后 `FULL` 会话可创建会话；另一个浏览器登录能读到同一条会话。
6. 第二个用户通过会话 ID 访问返回 404。
7. 恢复码旧值重放失败；恢复后旧会话与旧密码失效。
8. 停用账号后原会话立即 401。
9. 无 CSRF 的登录态写请求返回 403；外站 Origin 返回 403。
10. 普通用户无法创建/发布能力；Creator 测试未通过时不能提交；Admin 未批准时不能发布。
11. User 请求未批准 MCP Server 返回 403；连接响应不含 Token 明文。
12. 无真实模型配置时，`mode=openai` 返回失败 Run，`errorCode=REAL_PROVIDER_NOT_CONFIGURED`，不会生成模拟成功。
