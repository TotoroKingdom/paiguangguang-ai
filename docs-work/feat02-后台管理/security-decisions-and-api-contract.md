# feat02 / F01 安全决策与 API 契约

> 版本：v0.1
> 日期：2026-11-08（Asia/Shanghai）
> 仓库：`TotoroKingdom/paiguangguang-ai`
> 任务：feat02 G0 / F01（冻结危险操作、安全规则与 API 契约）
> 文档性质：**安全设计草案与待审批决策记录，不是已实现接口，不是生产验收**。
> 结论：**F01 = BLOCKED / 待评审**。账号、密码、注册、会话和基础契约已有可评审草案；Q-02 人工辅助恢复、Q-03 旧 Admin 映射、Q-04 具体阈值、Q-06 预算、Q-07 生产安全和 Q-08 数据保留仍未取得有效批准。

---

## 0. 不可更改的产品边界

以下规则来自 feat02 总纲、`01`～`06` 及本轮固定产品决策，F01 不得擅自改变：

| 编号 | 已确认规则 |
|---|---|
| P-01 | 普通账号从 `100` 开始，按成功注册自然递增；`999 → 1000`、`9999 → 10000`；产品层不设固定三位数或人数上限；账号不可自选、不可回收复用。 |
| P-02 | 不使用邮箱、短信、第三方身份注册或找回。 |
| P-03 | 密码最低 **6 位**；不得为提高“强度”偷偷改成 8/12 位；可用弱口令黑名单、限流、延迟和异常告警补强。 |
| P-04 | 注册默认 `User / PENDING`，只有管理员激活后才可使用正式服务。 |
| P-05 | User、Creator、Admin 使用统一身份和统一会话；管理入口必须可见，服务端必须重新鉴权。 |
| P-06 | 密码找回使用**一次性高熵恢复码 + 受控人工辅助**；不存在“只凭数字账号直接重置”的后门。 |
| P-07 | 普通 User **只能连接平台已批准的 MCP Server**；不得提交任意 Server URL，不得绕过服务端访问外部地址。 |
| P-08 | 旧系统、旧管理员表和旧匿名会话必须保留；迁移必须 Expand（先扩展），不得直接清空或覆盖历史。 |
| P-09 | Demo、浏览器模拟回复、模拟 MCP 连接和 `accepted` 准入记录不能冒充真实执行或产品完成。 |
| P-10 | Admin 治理权限不等于读取用户私人聊天正文、文件正文、密码哈希、恢复码或第三方凭据明文的权限。 |

> 说明：首个管理员“受信任初始化、不占普通 100 序列”已在 `01`/`03` 中作为确认/建议方向记录；具体保留号、旧 `admin` 登录名兼容窗口仍属于 Q-03，不能写成已冻结实现。

---

## 1. 决策状态总表（Q-01～Q-08）

状态定义：

- `[已确认]`：产品规则已经固定，F01/F02 不得改变。
- `[建议默认]`：本轮推荐值，未获产品/安全负责人批准前不是冻结需求。
- `[待审批]`：需要责任人明确签字或书面确认。
- `[阻断]`：未批准前对应 API/UI/发布必须保持关闭或 BLOCKED。

| ID | 主题 | 已确认内容 | 建议默认值 | 待审批事项 | 阻断原因/影响 |
|---|---|---|---|---|---|
| **Q-01** | 恢复码数量、生成与轮换 | 一次性、高熵、仅显示一次；服务端只存可验证摘要；不进入 URL、LocalStorage、日志、分析埋点。 | 每个用户同时只有 **1 枚** 有效恢复码；使用 `secrets.token_bytes(32)` 级别熵（约 256 bit）；服务端存 HMAC-SHA-256 摘要；成功后轮换；登录态重新验证密码后可主动轮换；V1 不自动过期，但显示签发时间。 | 是否允许 2 枚并存；是否设置 90/180/365 天自动过期；密码修改是否强制轮换恢复码。 | F04 的 API/UI 必须按最终数量实现；未定不影响 F02 内部数据模型，但影响 U-05/U-10 的确定断言。 |
| **Q-02** | 管理员辅助重置身份核验 | 不能凭数字账号直接重置；必须可信人工核验；管理员不能查看旧密码或恢复码。 | **人工重置默认关闭。** 若开启：用户经受控支持渠道提出；核验身份归属并形成外部核验案例；至少双人复核（请求 Admin + 另一名独立 Approver）；签发 10 分钟、单次使用的恢复票据；用户自行设置新密码；不产生管理员可读的临时密码；撤销旧会话并轮换恢复码；全流程审计。 | 谁有资格核验；可接受的身份证据；双人复核是否强制；单管理员/紧急 break-glass 条件；票据交付渠道；票据 TTL；是否允许远程视频核验。 | **硬阻断**：未冻结 SOP 前，不实现、不挂载、不显示“一键重置密码”。F04 可先完成用户自助恢复；G1 的“管理员辅助恢复”必须保持 BLOCKED。 |
| **Q-03** | 旧管理员统一归属与初始化 | 保留旧 `admin_users` 与历史；旧 Admin 迁移到统一用户；受信任初始化；不导出明文密码；重启不得覆盖人工改密。 | bootstrap Admin 使用保留数字账号 `1`，不消耗普通 `100` 序列；普通用户仍从 `100` 开始；其他 Admin 由现有用户提升角色并保留原账号；新增 `admin_user_links` 映射；复制旧 PBKDF2 摘要；旧 `/admin/auth/*` 在限时窗口内只做桥接/重定向，之后退役；CLI 只允许一次性 bootstrap。 | 保留号是否用 `1`；是否保留旧 `admin` 用户名兼容；旧管理员密码是否要求首次改密；旧会话何时强制失效；迁移窗口长度。 | 没有生产 `admin_users` 盘点，无法确定映射和回滚演练规模。F05 不得在 Q-03 批准前改管理员权威源。 |
| **Q-04** | 6 位密码的弱口令与限流阈值 | 最低 6 位；无邮箱/短信；注册、登录、恢复都需防刷/防枚举；数字账号可推测，响应不得泄露存在性。 | 密码最长 128 字符；拒绝常见弱口令（至少 10k 黑名单）、纯重复、连续序列、等于账号/昵称；登录 5 次失败/15 分钟/账号+IP，IP 维度 20 次/15 分钟，锁 15 分钟；注册 10 次请求/小时/IP、50 次/天/IP；恢复 5 次/小时/账号+IP、20 次/天/IP；管理员保留现有 5 次/5 分钟/15 分钟。所有阈值可配置。 | 最终阈值；是否加本地 CAPTCHA/人机校验；NAT/共享 IP 白名单；是否需要按设备信号（不可信）组合；失败响应统一为 401 还是部分 429。 | 当前登录限流是进程内字典，不满足多进程/多实例。F01 要求共享存储或等效安全方案；具体阈值未定不阻塞 F02 数据模型，但阻塞安全验收。 |
| **Q-05** | 能力默认可见范围与私人 Skill 转平台版 | MCP Server 必须平台批准；私人 Skill 默认私人；发布、可见、授权、就绪分离。 | Active 用户可看安全元数据；执行权限单独判断；私人 Skill 不上架；用户可提交“快照申请”，Admin 审核后复制为平台所有权版本；原私人 Skill 不被自动转移。 | 平台能力默认是全部 Active 可见还是按角色/授权；Creator 是否能看见他人摘要；平台版归属与署名。 | 属于 G2；不阻塞 F02/F03，但必须在 F08/F09/F11 前冻结。 |
| **Q-06** | 用户模型成本、并发与 Token 配额 | 必须有服务端预算/并发/超时护栏；不能只靠前端。 | 建议初始：每用户 20 请求/天、50k tokens/天、1 个并发 Run、单 Run 120 秒、10 次 Tool 调用、3 次 MCP 调用、最多 2 次重试；全局 kill switch；管理员可调。 | 具体请求/Token/金额预算；不同模型是否不同额度；超限提示；外部 MCP 成本计入方式；是否允许管理员临时提额。 | 属于 G3；F02/F03 不应实现模型调用，也不得用预算默认值宣称真实 Runtime。 |
| **Q-07** | TLS、生产密钥与依赖风险 | 生产必须 HTTPS、Secure/HttpOnly Cookie、可信 Origin；密钥/Token 不进日志；发布需备份与回滚。 | 生产仅允许 HTTPS；`ASSISTANT_OWNER_COOKIE_SECRET` ≥32 字符；`ASSISTANT_ALLOWED_ORIGINS` 仅 HTTPS；依赖审计不得有未批准 critical/high；发布前完成备份恢复演练。 | 实际 TLS 终止方式；GitHub secrets/variables；部署账号 sudo；Next.js 14.2.35 依赖升级/风险接受；生产服务器实际状态。 | **发布阻断**：PR #11 当前仍为 Draft/Open，正文自述缺 secret/variable、无 443/TLS、无 sudo、1 critical/3 high 依赖风险。未实时复核，不能标解决。 |
| **Q-08** | Disabled/Rejected 数据保留与申诉 | 停用不等于删除；历史保留；不能因治理操作默认读取私人正文。 | V1 默认不自动删除身份/账号记录；停用/拒绝只改状态并撤销会话；会话、消息、个人资源保留；账号号永不重用；用户删除/申诉走受控支持流程；保留期限另行批准。 | Rejected 最短保留期；Disabled 数据保留上限；用户删除请求的审批与匿名化；申诉渠道；是否需要法律/隐私评审。 | 属于 G1/G4 政策；未冻结前不得实现自动清理。F05 只能做状态变更，不做级联删除。 |

---

## 2. 安全红线

### 2.1 人工恢复红线

以下任意一项都**不能**单独触发密码重置、临时密码、恢复票据或账号接管：

- 知道或猜中数字账号。
- 知道昵称、注册时间、最后登录时间、大致使用记录。
- 能复述聊天内容、文件标题或能力名称。
- 拥有同一浏览器 Cookie、同一 IP、同一设备指纹或同一 User-Agent。
- 通过公开页面能看到账号存在。
- 管理员口头说“这是本人”，但没有形成可追溯核验案例。

正确路径只能是：

1. 用户通过预先批准的支持渠道提出请求；
2. 支持人员按 Q-02 冻结的核验标准核验身份归属；
3. 形成外部核验案例 ID（不在应用内存身份证明原件）；
4. 由第二名独立审批者复核；
5. 系统签发短期、单次、不可猜测的恢复票据；
6. 用户凭票据自行设置新密码；
7. 旧会话失效、旧恢复码失效、新恢复码只显示一次；
8. 审计记录请求、核验、审批、票据签发、消费、失败和撤销。

**禁止定义**以下路径：

- `POST /api/v1/admin/users/{id}/reset-password`
- `POST /api/v1/admin/users/{id}/set-password`
- 任何接受 `accountNumber` 后直接返回可用密码/Temp Password 的接口
- 任何在后台页面“输入账号 → 生成临时密码”的按钮

如果 Q-02 未批准，人工恢复 UI/API 必须不存在、返回 404 或保持 feature flag（功能开关）关闭；不能以“测试接口”留在生产路由表。

### 2.2 身份与权限红线

- 不能长期保留 `admin_users` 与 `users` 两套可写身份权威源。
- 不能在 React 中隐藏按钮就算权限控制；每个业务 API 必须服务端鉴权。
- 不能把 Pending、Disabled、Rejected 用户的会话当作正式会话使用。
- 不能让 Admin 默认读取用户私人聊天、文件正文、密码哈希、恢复码、MCP Token。
- 不能让最后一个有效 Admin 被停用、降级或删除。
- 不能把 `owner_id` 直接改名为 `user_id`，也不能自动把所有匿名历史归给当前登录用户。

### 2.3 秘密红线

- 恢复码明文只允许在“本次注册成功”或“本次恢复/轮换成功”的响应中出现一次。
- 不得写入 URL、LocalStorage、sessionStorage、日志、错误追踪、分析事件、截图或测试固定值。
- 管理员不能读取用户恢复码或旧密码。
- 服务端只存密码/恢复码/会话 Token 的摘要或哈希。
- 测试报告只能用运行时生成的测试秘密，不得提交固定明文密码。

### 2.4 真实能力红线

- F02/F01 不实现模型、Tool、MCP 执行，不得声称已有真实 AI 能力。
- `capability_runs.status=accepted` 不是 completed。
- 前端 `createMockReply()`、模拟 MCP `testConnection` 不能进入正式用户流程。
- 普通 User 的 MCP 页面不得出现任意 URL 输入。

---

## 3. 统一身份模型

### 3.1 用户、角色与状态

```text
Guest
  └─注册成功─> PENDING ──Admin 激活──> ACTIVE ──Admin 停用──> DISABLED
                  └────Admin 拒绝────> REJECTED              └─Admin 恢复─> ACTIVE
```

- 角色：`USER`、`CREATOR`、`ADMIN`。
- 状态：`PENDING`、`ACTIVE`、`DISABLED`、`REJECTED`。
- 角色与状态正交；`PENDING + ADMIN` 也不能绕过激活限制，除非是受信任的 bootstrap（首次初始化）流程。
- 注册只能产生 `USER + PENDING`；请求体不能指定角色、状态、账号。

角色序列化约定（建议）：数据库与 API 统一使用大写枚举 `USER / CREATOR / ADMIN`；迁移时把旧 `admin_users.role="admin"` 规范化为 `ADMIN`，旧 `"viewer"` 不成为 V1 产品角色（如果仍需只读管理员，应单独定义）。前端只负责把枚举映射为中文显示，不自行推导权限。

### 3.2 账号格式

- `accountNumber` 是十进制字符串，正则语义：`^[1-9][0-9]*$`。
- 不接受空串、前导零、正负号、空白、科学计数法、浮点数、千分位。
- 不设三位/四位 UI 限制；前端使用字符串，不使用 `parseInt` 后回写。
- 普通用户从 `100` 开始；bootstrap Admin 建议保留 `1`（Q-03 待批）。
- 内部资源归属使用不透明 UUID `user_id`，不使用可枚举账号作为外键。

### 3.3 会话范围

登录成功但状态非 Active 时，建议签发**受限会话**（status-only session），仅允许：

- `GET /api/v1/auth/session`
- `GET /api/v1/me/status`
- `POST /api/v1/auth/logout`

禁止访问聊天、能力目录、运行、文件、个人 Skill、MCP 连接、管理 API。

Active 用户会话为 `FULL`；Admin 角色仍由服务端按角色判断，前端只做显示。

---

## 4. API 通用契约

### 4.1 基础约定

- 新接口前缀：`/api/v1`。
- JSON 字段使用 camelCase（小驼峰），与现有前端 API 风格一致。
- 请求必须 `Content-Type: application/json`；否则 `415`。
- 登录、注册、恢复等匿名入口仍校验 `Origin`/`Sec-Fetch-Site`。
- Cookie 认证的 `POST`/`PATCH`/`DELETE` 必须同时校验 `Origin` 和 `X-CSRF-Token`。
- 不把 `returnTo` 交给后端作为开放跳转参数；前端只允许站内白名单相对路径，拒绝 `//`、反斜杠、编码绕过和外站 URL。
- 所有新接口的错误使用统一 envelope（错误封套），旧接口的 `{detail: ...}` 暂不强行改造，避免破坏现有客户端。

建议错误封套：

```json
{
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "账号或密码错误",
    "requestId": "req_...",
    "fields": {}
  }
}
```

### 4.2 错误码

| HTTP | code | 语义 |
|---:|---|---|
| 400 | `BAD_REQUEST` | 请求格式或状态转移不合法 |
| 401 | `AUTH_INVALID_CREDENTIALS` | 账号/密码错误；不区分账号是否存在 |
| 401 | `AUTH_SESSION_REQUIRED` | 无有效会话 |
| 403 | `ACCOUNT_NOT_ACTIVE` | 账户非 Active，不能使用正式业务 API |
| 403 | `FORBIDDEN_ROLE` | 已认证但无角色/资源权限 |
| 403 | `CSRF_INVALID` | CSRF Token 缺失或错误 |
| 403 | `ORIGIN_NOT_ALLOWED` | Origin/同源校验失败 |
| 404 | `NOT_FOUND` | 私有资源不存在或无访问权；不泄露存在性 |
| 409 | `STATE_CONFLICT` | 状态/版本已被其他管理员修改 |
| 409 | `IDEMPOTENCY_CONFLICT` | 同一幂等键对应不同请求体 |
| 409 | `LAST_ADMIN_PROTECTED` | 操作会导致最后一个有效 Admin 消失 |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | 非 JSON |
| 422 | `VALIDATION_ERROR` | 字段校验失败 |
| 422 | `PASSWORD_TOO_SHORT` | 用户密码不足 6 位 |
| 422 | `PASSWORD_TOO_WEAK` | 命中弱口令/明显模式 |
| 422 | `PASSWORD_MISMATCH` | 两次密码不一致 |
| 422 | `ACCOUNT_NUMBER_INVALID` | 账号格式非法 |
| 429 | `RATE_LIMITED` | 限流；响应带 `Retry-After` 或 `retryAfterSeconds` |
| 503 | `SERVICE_UNAVAILABLE` | 数据库/认证依赖不可用；不得降级为假成功 |

### 4.3 幂等与并发

- 注册要求客户端生成 `Idempotency-Key`；服务端存 key 摘要，不存原值。
- 同 key + 同请求体：返回同一用户/账号结果，不重复发号。
- 同 key + 不同请求体：`409 IDEMPOTENCY_CONFLICT`。
- 用户表增加 `version` 整数；管理员写操作必须带 `expectedVersion`，状态冲突返回 `409 STATE_CONFLICT`。
- 激活、拒绝、停用、恢复、角色变更与审计同事务提交。

---

## 5. 认证与会话 API

### 5.1 `POST /api/v1/auth/register`

请求头：

```text
Content-Type: application/json
Origin: https://<same-site>
Idempotency-Key: <uuid>
```

请求体：

```json
{
  "password": "至少 6 位的密码",
  "passwordConfirm": "相同密码",
  "nickname": "可选昵称"
}
```

禁止字段：`accountNumber`、`role`、`status`、`isActive`。出现时必须 `422 VALIDATION_ERROR`，不能静默忽略。

成功 `201`：

```json
{
  "user": {
    "id": "<uuid>",
    "accountNumber": "100",
    "nickname": "可选",
    "role": "USER",
    "status": "PENDING"
  },
  "recovery": {
    "code": "<一次性高熵恢复码>",
    "issuedAt": "2026-11-08T05:00:00Z",
    "displayMode": "ONE_TIME"
  },
  "sessionIssued": false
}
```

约束：

- **F04 完成前，此接口不得作为生产注册入口开放**。F02 可以完成内部模型和测试，但只能用测试注入服务验证，不得临时返回弱随机码或固定码。
- 注册成功不自动登录；用户去统一登录页。
- 恢复码只在本次响应出现。刷新成功页不重新获取；页面只能用服务端返回的内存状态显示。
- 同一幂等键在 10 分钟“响应交付窗口”内可重放同一账户和恢复码；超过窗口或已确认交付后，重放只返回账户结果，不重新返回明文码（实现需在 F02/F04 任务卡中明确并测试）。

主要错误：

| 场景 | 响应 |
|---|---|
| 密码 5 位 | `422 PASSWORD_TOO_SHORT` |
| 密码与确认不一致 | `422 PASSWORD_MISMATCH` |
| 弱口令 | `422 PASSWORD_TOO_WEAK` |
| 请求指定账号/角色 | `422 VALIDATION_ERROR` |
| 同 key 不同请求体 | `409 IDEMPOTENCY_CONFLICT` |
| 注册刷号/限流 | `429 RATE_LIMITED` |
| 数据库/发号依赖不可用 | `503 SERVICE_UNAVAILABLE`；不得返回假账号 |

### 5.2 `POST /api/v1/auth/login`

请求体：

```json
{
  "accountNumber": "100",
  "password": "用户密码"
}
```

成功 `200`：

```json
{
  "authenticated": true,
  "user": {
    "id": "<uuid>",
    "accountNumber": "100",
    "nickname": "可选",
    "role": "USER",
    "status": "PENDING"
  },
  "session": {
    "scope": "STATUS_ONLY",
    "expiresAt": "2026-11-08T13:00:00Z"
  }
}
```

行为：

- `ACTIVE` → `scope: "FULL"`。
- `PENDING` / `DISABLED` / `REJECTED` → `scope: "STATUS_ONLY"`，可看状态和退出，不可用正式业务 API。
- 账号不存在、密码错误、账号格式合法但无记录：统一 `401 AUTH_INVALID_CREDENTIALS`，响应体和耗时不得暴露存在性。
- 限流：`429 RATE_LIMITED`，带恢复时间；不要在校验密码前泄露“账号存在”。
- 登录成功设置会话 Cookie 和 CSRF Cookie；登录请求本身不需要 CSRF，但需要 Origin 校验。

### 5.3 `GET /api/v1/auth/session`

- 有效会话：`200`，返回 `authenticated: true`、用户摘要、`scope`、`expiresAt`。
- 无/过期/已撤销会话：`401 AUTH_SESSION_REQUIRED`。
- 返回角色/状态必须从数据库/服务端当前权限读取，不能信任前端缓存。

### 5.4 `POST /api/v1/auth/logout`

- 需要有效会话、CSRF 和 Origin。
- 删除当前会话记录、清 Cookie。
- 成功 `204`；重复退出保持幂等语义，不返回 500。

### 5.5 `GET /api/v1/me/status`

- 任何有效会话可访问。
- 返回账号、昵称、角色、状态、状态原因摘要（不泄露内部备注/敏感审计）。
- `PENDING` 可轮询此接口；不自动高频轮询，提供手动刷新。

### 5.6 `GET /api/v1/me`

- 仅 `ACTIVE` 且 `FULL` 会话可访问。
- 非 Active：`403 ACCOUNT_NOT_ACTIVE`。
- 返回个人资料；不返回密码哈希、恢复码、会话 Token 或内部安全字段。

### 5.7 Cookie 建议

| Cookie | 属性 | 用途 |
|---|---|---|
| `paiguangguang_session` | HttpOnly、Secure（生产）、SameSite=Strict、Path=/ | 统一用户/管理员会话 |
| `paiguangguang_csrf` | 非 HttpOnly、Secure（生产）、SameSite=Strict、Path=/ | 前端读取后放入 `X-CSRF-Token` |

- 旧 `paiguangguang_admin` / `paiguangguang_admin_csrf` 在迁移窗口内只作为旧桥接；新代码不得长期双写。
- 旧 `paiguangguang_owner` 保留给匿名历史认领，不与用户会话混用。
- 会话有效期建议：User/Creator 7 天；Admin 8 小时；角色变为 Admin 时撤销旧会话并要求重新登录。具体时长可由安全负责人批准调整。

---

## 6. 密码恢复 API

### 6.1 用户自助恢复：`POST /api/v1/auth/recovery/complete`

匿名请求，JSON + Origin + 限流：

```json
{
  "accountNumber": "100",
  "recoveryCode": "<未使用的高熵恢复码>",
  "newPassword": "至少 6 位",
  "newPasswordConfirm": "相同密码"
}
```

成功 `200`：

```json
{
  "ok": true,
  "recovery": {
    "code": "<新的单次恢复码>",
    "issuedAt": "2026-11-08T05:10:00Z",
    "displayMode": "ONE_TIME"
  },
  "sessionsRevoked": true
}
```

事务要求：

1. 校验账号、恢复码摘要、未使用状态和限流。
2. 更新密码摘要（最低 6 位、弱口令规则）。
3. 标记旧恢复码已使用/失效并生成新摘要。
4. 撤销该用户全部旧会话。
5. 写审计（不含恢复码明文）。
6. 全部成功才提交；任一步失败回滚。

错误：

- 账号不存在、恢复码错误/已用/过期：统一 `401 RECOVERY_INVALID`（不区分）。
- 新密码过短/弱：`422 PASSWORD_TOO_SHORT` / `422 PASSWORD_TOO_WEAK`。
- 限流：`429 RATE_LIMITED`。

### 6.2 登录态轮换：`POST /api/v1/auth/recovery/rotate`

- 需要 `FULL` 会话、CSRF、Origin。
- 请求：当前密码 + 新恢复码的确认动作；不要求用户输入旧恢复码。
- 成功返回新码一次；旧码失效；可在响应中要求所有其他会话失效（建议撤销除当前会话外的会话）。
- 失败不能返回旧码或新码。

### 6.3 密码修改：`POST /api/v1/auth/password/change`

- 需要 `FULL` 会话、CSRF、Origin。
- 请求：`currentPassword`、`newPassword`、`newPasswordConfirm`。
- 成功后撤销其他会话；建议同时轮换恢复码（与 Q-01 最终批准一致）。
- 不允许通过该接口修改账号、角色、状态。

### 6.4 管理员辅助恢复（默认关闭，不是当前可调用接口）

如果 Q-02 获批准，建议使用“恢复请求/审批/票据”模型，而不是密码重置：

| 建议接口 | 用途 | 关键约束 |
|---|---|---|
| `POST /api/v1/admin/users/{userId}/recovery-requests` | 记录已核验的身份案例和请求 | 只能由有支持权限的 Admin 创建；必须带外部 `verificationCaseId` 和理由 |
| `POST /api/v1/admin/users/{userId}/recovery-requests/{requestId}/approve` | 第二名独立审批 | 不能由请求者本人批准；双人复核 |
| `POST /api/v1/admin/users/{userId}/recovery-requests/{requestId}/revoke` | 撤销未使用票据 | 留审计 |
| `POST /api/v1/auth/recovery/manual/complete` | 用户凭票据自行设新密码 | 票据 10 分钟、单次、高熵；成功后撤销会话并轮换恢复码 |

这些接口在 Q-02 未批准前**不挂载**。不得提供 `admin set password`、`admin view recovery code`、`admin generate password`。

---

## 7. 管理员用户 API

### 7.1 统一鉴权

- 所有 `/api/v1/admin/users*` 必须使用统一会话，并同时满足：
  - `status=ACTIVE`
  - `role=ADMIN`
  - 有效 CSRF/Origin（写操作）
- 旧 `admin_sessions` 只能在 F05 受控桥接窗口内被读取；不得与新 `user_sessions` 同时成为长期权威源。
- 每次请求从服务端读取角色/状态，或使用 `authz_version` 比对；角色变更/停用应立即生效。

### 7.2 管理视图

```json
{
  "id": "<uuid>",
  "accountNumber": "100",
  "nickname": "可选",
  "role": "USER",
  "status": "PENDING",
  "version": 1,
  "createdAt": "2026-11-08T05:00:00Z",
  "lastLoginAt": null
}
```

不返回：`password_hash`、恢复码、会话 Token、聊天正文、文件正文、MCP Token、身份核验材料原文。

### 7.3 端点

| 方法/路径 | 权限 | 语义 |
|---|---|---|
| `GET /api/v1/admin/users` | Admin | 分页；`status`、`role`、`q`（账号/昵称）、`cursor`、`limit`；返回 `items`、`nextCursor` 和可选聚合计数 |
| `GET /api/v1/admin/users/{userId}` | Admin | 用户基本信息、状态历史摘要、必要会话元数据；不返回私人正文 |
| `POST /api/v1/admin/users/{userId}/activate` | Admin | `PENDING → ACTIVE`；写审计 |
| `POST /api/v1/admin/users/{userId}/reject` | Admin | `PENDING → REJECTED`；`reason` 必填；写审计 |
| `POST /api/v1/admin/users/{userId}/disable` | Admin | `ACTIVE → DISABLED`；`reason` 必填；立即撤销会话；写审计 |
| `POST /api/v1/admin/users/{userId}/restore` | Admin | `DISABLED → ACTIVE`；`reason` 必填；不自动恢复旧会话；写审计 |
| `PATCH /api/v1/admin/users/{userId}/roles` | Admin | 修改 `USER/CREATOR/ADMIN`；`reason` 必填；不能自我越权；不能移除最后 Admin；写审计 |

写请求体统一建议：

```json
{
  "expectedVersion": 3,
  "reason": "审核理由"
}
```

响应 `200`：

```json
{
  "user": { "...管理视图..." },
  "auditEventId": "<uuid>"
}
```

错误：

- 非法状态转移：`409 STATE_CONFLICT`，返回当前版本/状态，要求刷新。
- 重复激活/重复拒绝：不得产生矛盾结果；可幂等返回当前状态，或 `409`。
- 最后一名有效 Admin 被停用/降级：`409 LAST_ADMIN_PROTECTED`。
- 普通 User 访问：`403 FORBIDDEN_ROLE`。
- 未知/无权用户 ID：`404 NOT_FOUND`。
- CSRF/Origin 错误：`403`。

### 7.4 状态转移规则

| 当前 | 允许动作 | 结果 |
|---|---|---|
| `PENDING` | activate | `ACTIVE` |
| `PENDING` | reject | `REJECTED` |
| `ACTIVE` | disable | `DISABLED`，撤销全部会话 |
| `DISABLED` | restore | `ACTIVE`，不恢复旧会话 |
| `REJECTED` | 默认无直接 restore；是否允许重新申请由 Q-08/后续政策决定 | 保持 `REJECTED` |

不允许从 `DISABLED` 直接删除、清空私人数据或改账号号码。

---

## 8. 旧 Admin 迁移与 bootstrap 契约

### 8.1 建议默认

- 新增 `admin_user_links(legacy_admin_id, user_id, migrated_at, migration_source, notes)`；`legacy_admin_id` 唯一。
- 旧 `admin_users` 表保留，不删除、不改历史密码摘要。
- bootstrap Admin 建议账号 `1`；普通序列仍从 `100`。
- 复制旧 `password_hash`（PBKDF2 格式）到统一用户；不生成新密码、不导出明文。
- 旧 `admin` 用户名只在受控兼容窗口内映射；统一登录仍以数字账号为主。
- 旧管理员会话在切换后过期或撤销；不得继续作为第二权威源写管理数据。

### 8.2 初始化规则

- CLI 仅在“系统没有 bootstrap 标记/没有有效 Admin”时允许创建首个 Admin。
- 生产启动日志/环境变量不得在每次重启时覆盖已有 Admin 密码。
- 初始化必须记录审计和 `bootstrap_at`；重复执行只提示已初始化，不静默改密。
- 旧管理员密码如果不足当前管理员策略，是否要求改密由 Q-03 审批；不得悄悄降低现有 12 位管理员初始化要求。

### 8.3 切换顺序

1. 备份并记录旧 `admin_users` 聚合计数。
2. 在隔离副本演练映射和旧管理员登录。
3. 新增统一 Admin 用户和映射，不删除旧表。
4. 验证统一登录、管理 API、旧会话兼容。
5. 关闭旧管理员登录写入口，保留只读兼容期。
6. 旧会话过期/撤销；确认只有一个身份权威源。
7. 保留回滚快照和映射审计。

---

## 9. 限流与弱口令规则

### 9.1 限流存储

- 不能继续使用进程内 `LoginLimiter` 作为用户登录唯一防线。
- 建议使用数据库表（SQLite 事务/唯一约束）或未来 Redis 等共享存储；多进程/多实例必须共享。
- 限流键使用 HMAC/摘要，不把明文账号、IP、User-Agent 直接拼成可枚举日志。
- 限流存储故障时登录/恢复应 Fail Closed（返回 503），不能自动放行。

### 9.2 建议阈值（待批准）

| 入口 | 建议 |
|---|---|
| 注册 | 10 次请求/小时/IP；50 次/天/IP；成功账号数异常时告警 |
| 登录 | 5 次失败/15 分钟/账号+IP；20 次/15 分钟/IP；锁 15 分钟 |
| 恢复码 | 5 次失败/小时/账号+IP；20 次/天/IP；锁 1 小时 |
| 管理员登录 | 保留现有 5 次/5 分钟/锁 15 分钟 |
| 响应 | 未知账号与错误密码同一错误文案；失败延迟接近；429 带恢复时间 |

### 9.3 弱口令

- 6 位是最低长度，不是“任意 6 位都可用”。
- 拒绝常见弱口令列表、纯重复（`111111`）、连续序列（`123456`）、账号本身、昵称本身。
- 不做会变相提高最低长度的复杂组合硬要求；具体黑名单和风险提示待安全负责人批准。

---

## 10. 服务端鉴权与资源边界

### 10.1 依赖分层

建议新增：

- `get_current_session`：解析 Cookie，校验 Token 摘要、过期、撤销和 `authz_version`。
- `require_authenticated`：任何有效会话（可用于状态页）。
- `require_active_user`：`ACTIVE` 才可访问正式业务。
- `require_role(role)` / `require_admin`：服务端角色守卫。
- `require_resource_owner`：会话/文件/Skill/Run/MCP 连接的对象级所有权检查。

### 10.2 资源规则

- 聊天会话：只有 `conversation.user_id == current_user.id`；旧匿名认领需旧 Cookie 证明。
- 文件、私人 Skill、MCP 连接、Run：只有 owner 本人可见/可改。
- 管理员列表只返回治理所需元数据；私人正文默认不返回。
- 越权访问私有资源统一 `404 NOT_FOUND`，避免 ID 枚举。
- 角色变更、停用、撤销授权在后续敏感操作前重新校验。
- 管理员不能通过请求体指定 `actorId`、`ownerId` 或伪造审计者。

### 10.3 MCP 边界

- 普通 User 只能从平台已批准 Server 中连接；不存在 `POST /mcp/servers` 或任意 URL 字段。
- 管理员/平台的 Server 注册必须做 URL 校验、SSRF 防护、DNS/IP 复检、重定向限制、工具发现和审批。
- 用户 MCP Connection 只能使用本人凭据；Token 只存服务端加密/引用，不返回明文。
- 断开、过期、撤销后，新调用必须服务端拒绝；不能共享管理员 Token。

---

## 11. 可写成确定断言的安全验收

这些断言应在 F02～F05 的单测/API/E2E 中落地：

1. **账号**：空库首号 `"100"`；`999 → 1000`、`9999 → 10000`；并发不重复；账号是字符串。
2. **密码**：5 位拒绝、6 位通过长度；弱口令拒绝；管理员 CLI 仍要求 12 位。
3. **注册**：请求不能指定账号/角色/状态；同幂等键不重复发号；失败不消耗号码；恢复码不明文入库。
4. **Pending**：正确登录只能访问状态页 API；直接调用聊天/能力/Run API 返回 `403 ACCOUNT_NOT_ACTIVE`。
5. **激活**：Admin 激活后状态变 Active；重复/冲突请求有确定响应；审计与状态同事务。
6. **会话**：停用、改密、恢复、角色变化后旧会话失效；跨浏览器登录同一账号可见本人数据。
7. **恢复码**：旧码重放失败；新码只显示一次；未知账号/错误码同一语义；日志/URL/LocalStorage 无明文。
8. **人工恢复**：仅账号不能创建可消费票据；没有 `/admin/.../reset-password` 路由；Q-02 未批时功能开关关闭。
9. **权限**：User 直接调用 admin API 被拒绝；Creator 不能发布；最后 Admin 不能停用/降级；对象级 IDOR 返回 404。
10. **CSRF/Origin**：无 CSRF 写请求 403；外站 Origin 403；`returnTo` 不能外跳。
11. **MCP**：User 无任意 URL 入口/API；未批准 Server 不可连接；A 的凭据不能给 B 使用。
12. **真实性**：无真实执行时不得返回模拟成功；`accepted` 不能当 `completed`。

---

## 12. 待审批与阻断清单

| ID | 待审批/未决 | 责任人（待指派） | 影响 | 当前处置 |
|---|---|---|---|---|
| Q-01 | 恢复码数量、有效期、轮换时机 | 产品 + 安全 | F04/U-05/U-10 | 建议值可评审；F04 前不得上线弱码 |
| Q-02 | 人工核验证据、双人复核、票据渠道/TTL、break-glass | 产品 + 安全 + 运营 | F04、U-11、G1 | **阻断；人工重置 API/UI 关闭** |
| Q-03 | bootstrap 保留号、旧 `admin` 兼容、改密要求、切换窗口 | 产品 + 数据/运维 | F05、O-05 | **阻断；不得改管理员权威源** |
| Q-04 | 限流阈值、弱口令黑名单、共享存储实现 | 安全 + 后端 | F01/F03、U-16 | 建议值可评审；进程内 limiter 不可用 |
| Q-05 | 能力可见范围、平台版 Skill 归属 | 产品 | G2 | 非 F02 阻断 |
| Q-06 | 请求/Token/并发/运行时长/成本预算 | 产品 + 运维 + 财务 | G3/R-05 | 非 F02 阻断；不得假称 Runtime 完成 |
| Q-07 | TLS、密钥、依赖风险、部署权限 | 运维 + 安全 | G4/PR #11 | **发布阻断**；未实时复核 |
| Q-08 | 拒绝/停用保留期、删除/申诉、匿名化 | 产品 + 隐私/安全 | G1/G4 | 非 F02 阻断；不得自动清理 |

---

## 13. F01 结论与 F02 开工门禁

### 13.1 F01 判定

- **F01 = BLOCKED / 待评审**，不是 PASSED。
- 账号、密码、注册、会话、错误语义和旧系统保留原则已有可审查草案。
- Q-02 未批准，人工辅助重置必须保持关闭；这不阻止用户自助恢复的实现，但阻止 G1 的“管理员辅助恢复”通过。
- Q-03 未批准，旧 Admin 统一迁移不得开工；不能先改 `admin_users` 再补契约。
- Q-04 的阈值和共享限流实现未批准，登录/恢复安全验收不能标 PASS。

### 13.2 F02 开工门禁

F02（数字账号、用户实体、并发注册）只有在以下条件同时满足后才能进入实现：

1. **F00 已解除 BLOCKED**：获得独立副本恢复演练和生产只读盘点证据。
2. **F01-A 账号规则已批准**：账号计数器、幂等键、密码策略、Pending 状态、禁止请求指定角色/账号。
3. **F01-B 迁移契约已批准**：`0003_identity_users` 只新增表，不改旧表；一个 revision；无 `MAX()+1`。
4. **F01-C 会话/API 契约已批准**：统一 Cookie/CSRF、错误码、注册响应、恢复码交付窗口。
5. **生产注册开关默认关闭**：`USER_REGISTRATION_ENABLED=false`；F04 完成并验收前不得开放生产注册。
6. **不依赖 Q-02 的内部模型边界明确**：F02 不实现人工重置，不定义管理员改密接口；Q-02 只阻塞 F04/G1 的人工恢复部分。
7. **工作区隔离**：从当时最新 `dev` 新建临时分支/worktree；不与其他会话并行修改 `identity/*` 或 `main.py`。
8. **测试前置**：新空库、跨位数、并发、幂等、失败回滚、密码策略测试定义完成。

当前由于 F00 仍为 BLOCKED，F02 状态应为 **BLOCKED / NOT_STARTED**，不能以本文档替代门禁。

---

## 14. 拟议的后续最小任务卡

| 卡片 | 目标 | 交付 | 依赖/禁止 |
|---|---|---|---|
| `F01-A` Q-02 人工恢复 SOP 审批 | 冻结核验证据、双人复核、票据渠道、TTL、审计和拒绝条件 | 安全决策记录、责任人签署、失败路径 | 未批准前人工恢复 API/UI 不存在 |
| `F01-B` Q-03 旧 Admin 映射审批 | 冻结保留号、哈希迁移、bootstrap、旧登录兼容窗口 | 迁移契约、旧 Admin 回滚演练计划 | 不修改旧表、不覆盖人工改密 |
| `F01-C` API 契约评审 | 评审本文的注册/登录/会话/管理员用户/错误码 | 评审意见、冻结版本、OpenAPI 草案 | 不实现 F02 |
| `F02-A` 账户与迁移 | `users`、`account_sequences`、注册幂等、独立 `0003` | migration、模型、空库/跨位数/并发/幂等测试 | F00 PASSED；注册开关关闭 |
| `F02-B` 注册 API（内部） | 服务端发号、Pending、密码策略、幂等响应 | API 测试、失败回滚、日志秘密检查 | F04 前不开放生产入口 |
| `F03-A` 统一会话/RBAC | 用户会话、状态限制、角色守卫、CSRF/Origin | API/越权/过期/撤销测试 | 先冻结 Cookie 与错误语义 |
| `F04-A` 自助恢复码 | 一次性码、轮换、会话撤销 | U-05/U-10 测试、秘密泄漏检查 | Q-01 批准；不包含人工重置 |

**下一步不是直接写 F02 代码，而是先让 F00 恢复证据和 F01 的 Q-02/Q-03/Q-04 审批闭环。**

---

## 15. 参考

- `06-实施TASKS.md`：F00/F01 与 F02～F07 的唯一 F 编号来源。
- `05-现有代码差距与实施路线图.md`：Q-01～Q-08 的原始定义；其 G1 分组编号与 `06` 有错位，执行时以 `06` 为准。
- `01-用户与角色权限-PRD.md`：账号、状态、角色、恢复和旧数据迁移目标。
- `03-页面交互与状态-SPEC.md`：页面状态、错误文案、恢复码交互与后台入口。
- `04-端到端业务验收.md`：U-01～U-17、Q-01～Q-08、失败路径和证据要求。
- `baseline-and-migration-preflight.md`：本轮 Git、本地计数、备份存在性和 F00 BLOCKED 判定。
