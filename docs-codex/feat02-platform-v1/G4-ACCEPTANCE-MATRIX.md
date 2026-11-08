# feat02 G4 验收矩阵（38 场景）

> 日期：2026-11-08
> 代码基线：`dev` `247e4a0` + PR #39（取消幂等）
> 证据层次：L1 API/单元、L2 浏览器 E2E、L3 可控集成；**L4 真实供应商/生产未执行**。

## 1. 汇总

| Gate | 用例数 | PASS | PARTIAL | BLOCKED | NOT_RUN |
|---|---:|---:|---:|---:|---:|
| G1 身份 U-01～U-17 | 17 | 16 | 0 | 1 | 0 |
| G2 能力 C-01～C-10 | 10 | 9 | 1 | 0 | 0 |
| G3 Runtime R-01～R-06 | 6 | 3 | 2 | 1 | 0 |
| G4 上线 O-01～O-05 | 5 | 2 | 2 | 1 | 0 |
| **合计** | **38** | **30** | **5** | **3** | **0** |

判定说明：

- `PASS` 仅表示当前已有自动化证据覆盖该用例的**开发环境范围**，不等于生产或真实外部服务通过。
- `PARTIAL` 表示关键路径已实现，但仍有失败分支、真实联调或浏览器覆盖缺口。
- `BLOCKED` 表示缺少外部审批、真实供应商或生产环境证据。
- `NOT_RUN` 表示本轮未执行。

## 2. 身份与权限 U-01～U-17

| ID | 状态 | 证据 | 缺口 |
|---|---|---|---|
| U-01 | PASS | 路由回归 `/assistant`；注册/登录页可直达；访客聊天明确标注模拟 | 无独立“登录入口可见”截图断言 |
| U-02 | PASS | `test_password_policy_keeps_six_character_minimum...`：5 位拒绝、6 位通过、弱口令拒绝、无邮箱字段 | 无 5 位密码的浏览器 UI 断言 |
| U-03 | PASS | `test_register_starts_at_100...`、`test_register_crosses_decimal_boundaries...`：100/101/999→1000/9999→10000 | 无生产迁移后的真实号段核对 |
| U-04 | PASS | 6 线程并发注册唯一；同幂等键重试不重复发号；不同请求体 409 | 无网络超时/断连重试的浏览器注入 |
| U-05 | PASS | 注册响应仅首次含恢复码；幂等重放不再返回；账号 E2E 显示真实账号与一次性恢复码 | 未在 E2E 中刷新成功页验证不可恢复 |
| U-06 | PASS | Pending 登录 `STATUS_ONLY`；聊天/能力 API 403；账号 E2E 到达 Pending 页 | 无 |
| U-07 | PASS | 账号 E2E：Admin API 激活 → 用户刷新 → 进入工作台；审计与状态同事务代码路径 | E2E 未直接查询审计事件 |
| U-08 | PASS | 拒绝/停用/恢复状态机、停用旧会话 401、恢复后重新登录、审计事件均有 L1；管理 UI 提供对应操作 | 无 |
| U-09 | PASS | 统一角色守卫、用户审核/角色 API；Creator 创作中心与 Admin 审核页可见；Creator→Admin 审核发布 E2E；User 无管理入口；统一 Admin 可查看内置角色矩阵并通过 UI 完成真实角色分配（桌面/移动） | 无 |
| U-10 | PASS | 恢复码一次性、旧会话撤销、旧密码失效、旧码重放 401 | 新码“只显示一次”的浏览器刷新断言缺失 |
| U-11 | BLOCKED | 可信人工核验 SOP 未批准；管理员辅助重置 API/UI 不存在 | 需产品/安全/运营冻结核验、双人复核与票据交付 |
| U-12 | PASS | 跨浏览器同账号会话可见；个人 Skill/文件 E2E 服务端持久化 | 文件正文跨浏览器下载未单独 E2E |
| U-13 | PASS | 第二用户会话 404；Skill/文件/MCP 连接隔离；Token 不回显 | Run/MCP 凭据跨用户调用仅 L1 |
| U-14 | PASS | 认领需登录用户 + 旧 Owner 签名；伪造请求 400 | 重复认领幂等与冲突规模未压测 |
| U-15 | PASS | `returnTo` 专用校验仅允许 `/assistant` 站内路径，拒绝外站、协议相对、反斜杠、控制字符；外站 `next` E2E 被拒绝；游客后台重定向与越权 403/404 已覆盖 | 无 |
| U-16 | PASS | 登录失败限流、注册限流、未知账号与错误密码同响应、最后 Admin 保护、审计 | 计时侧信道与 NAT 共享 IP 策略未专项压测 |
| U-17 | PASS | 桌面/移动账号、个人资源、Creator→Admin 审核发布 E2E 通过；导航支持键盘/移动抽屉 | 无 |

## 3. 能力治理 C-01～C-10

| ID | 状态 | 证据 | 缺口 |
|---|---|---|---|
| C-01 | PASS | Creator 创建 Tool → `/test` 校验 executor/只读工具 → 提交；审计 | 无独立 Tool Schema 编辑 UI |
| C-02 | PASS | Creator 无权发布；Creator UI 测试→提交，Admin UI 审核→发布；版本快照与回滚；桌面/移动 E2E | 驳回→重提未单测 |
| C-03 | PASS | `granted` 能力未授权不可发现；直接调用 403；授权后可见 | 撤权后立即拒绝未单测 |
| C-04 | PASS | 个人 Skill 服务端 CRUD、Markdown 导入、所有者隔离、Runtime 加载 | 无编辑/版本历史 UI |
| C-05 | PASS | 登录态仅显示 approved Server；无任意 URL 输入；E2E 断言 | 无 Creator 提交待审 Server 的 E2E |
| C-06 | PARTIAL | 个人连接隔离、Token 加密、Runtime 通过个人连接调用 MCP Tool（MockTransport） | 外部真实 MCP、过期/撤销后调用拒绝未 L4 |
| C-07 | PASS | Agent v1 锁定 Tool v1；发布 Tool v2、Agent v2 后新 Run 使用 v2；旧 Run 仍保存 v1；发布时校验依赖版本；回滚接口 | 无 |
| C-08 | PASS | 停用后新目录/执行拒绝；版本回滚并审计 | 依赖停用级联检查未覆盖 |
| C-09 | PASS | 正式目录过滤 Demo；生产关闭演示时启动归档存量 Demo，保留版本并写审计；Active 用户目录 503 时显示错误与空目录，不出现 Demo 卡片（桌面/移动 E2E）；未就绪能力禁用聊天；Provider 未配置返回失败 Run | 生产首次归档实跑为 NOT_RUN，归入 F16/F17 |
| C-10 | PASS | 服务端按“无权限 → 需 MCP 授权 → 未就绪 → 预算不足 → 可执行”返回唯一 `blockedReason/primaryAction`；前端显示对应禁用按钮或连接/登录入口；未授权 granted 能力对 Active 用户可见但不可执行 | 无 |

## 4. Runtime R-01～R-06

| ID | 状态 | 证据 | 缺口 |
|---|---|---|---|
| R-01 | BLOCKED | SSE + Fake Provider 流式、消息持久化、刷新恢复；无真实模型密钥 | **真实模型 NOT_RUN**；真实调用证据缺失 |
| R-02 | PARTIAL | Skill → Tool → MCP 的 L3 Agent 链；RunStep/Trace 持久化 | 真实模型与真实 MCP 未联调 |
| R-03 | PARTIAL | completed/failed/timed_out/cancelled 均持久化终态；超时、取消、真实用户重试同一助手消息均有自动化；重试不重复用户消息；流连接中断后按 `clientTurnId` 从服务端恢复已接收 turn，不误判为未发送（详见 `R03-NETWORK-RECOVERY.md`） | 等待授权/审批 Run 状态需产品与安全协议；完整浏览器断网注入未执行 |
| R-04 | PASS | 用户仅查本人 Run；Creator 仅看自己能力的 Run 汇总；Admin 全局脱敏列表；accepted 不改写 completed；汇总不返回正文 | 无 |
| R-05 | PASS | 执行开始和 Tool/MCP 后二次校验能力授权；turn 创建后撤权终止执行；模型流开始后撤权不篡改已通过的运行，但新执行 403；并发重试原子 claim；完成态取消幂等 | 无 |
| R-06 | PASS | 401/403/404/409/429/503、模型 503/不可达/流提前中断、Runtime MCP 不可达、浏览器 503 错误恢复均有自动化；失败 Run 不会自动重试，失败后仍只有 1 个 Run 和原消息对 | 无 |

## 5. 部署与全站 O-01～O-05

| ID | 状态 | 证据 | 缺口 |
|---|---|---|---|
| O-01 | BLOCKED | 生产配置校验代码要求 HTTPS/Strong secret/Secure Cookie | 生产 443、TLS 证书、反代、GitHub secrets 未实时核验 |
| O-02 | PASS | 账户激活与能力审核在审计写入失败时回滚，状态/版本不变；发布、审核与审计同事务 | 无 |
| O-03 | PARTIAL | 密码/恢复码/Token 只存摘要或密文；Admin 不返回私人正文；所有 API 响应禁止缓存；后端日志/错误响应与桌面/移动浏览器 URL、Cookie、LocalStorage、SessionStorage 自动化抽查通过（详见 `O-03-SECRET-LEAKAGE-AUDIT.md`） | 生产容器日志、反向代理缓存与生产浏览器样本 **NOT_RUN**，需生产只读访问 |
| O-04 | PASS | Playwright 路由回归 `/`、`/rag`、`/lab/3d`、`/threejs`、`/assistant/*`，桌面/移动；旧会话测试通过 | 无生产回归 |
| O-05 | PARTIAL | F00 本地快照/恢复/迁移/回退演练；旧 Admin 摘要逐字复制 | 生产盘点、生产备份恢复、真实旧管理员登录未验证 |

## 6. 真实调用证据边界

| provider / 依赖 | 本轮结果 | 证据 |
|---|---|---|
| Fake LLM | PASS（L3） | 输出以 `[FakeProvider]` 开头；Run 终态与步骤持久化 |
| OpenAI-compatible 真实模型 | NOT_RUN / BLOCKED | 未配置密钥；测试断言 `REAL_PROVIDER_NOT_CONFIGURED` |
| Tool Gateway | PASS（L3） | `system.current_time`、`system.catalog_search`；参数校验与只读限制 |
| MCP Client/发现/Runtime | PASS（L3，MockTransport） | `tools/list`、`tools/call`、个人 Token、RunStep(type=mcp) |
| 外部真实 MCP Server | NOT_RUN | 未获批准外部测试服务，不访问未知地址 |
| 生产 HTTPS/部署 | BLOCKED | 未触碰生产环境 |

## 7. 结论

- G1/G2 的开发环境闭环已基本成立，但 U-11 人工恢复、完整角色 UI、撤权/依赖分支仍缺失。
- G3 自动化基础成立，**真实模型与真实 MCP 未联调**，不能宣布真实执行闭环。
- G4 生产门禁未解除，不能合并 `main` 或部署。
- 因此 V1 完整闭环 **未完成**；当前可作为开发环境阶段成果评审。
