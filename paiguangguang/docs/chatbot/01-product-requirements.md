# Portfolio Chatbot 产品需求文档

> 状态：待评审；版本：1.0；审计基线：Git `a47dcb0`（2026-07-12）。本文件只定义产品边界，不表示已经实施。

## 1. 项目背景

项目已提供登录、JWT/RBAC、PostgreSQL、Redis、ChromaDB、FastAPI、Next.js 与 DeepSeek 接入。现有 Portfolio Chat 只是验证前后端和模型调用的 V1 演示，本次要把它重构为登录用户独享、可恢复、可追踪、可扩展的 Chatbot 模块，同时不破坏 Knowledge、Browser、Office、Architecture 与 RBAC 等既有能力。

## 2. 当前实现与问题

审计确认的当前实现如下：

- `frontend/app/chat-bot/page.tsx` 只挂载 `frontend/features/chat-bot/chat-bot-panel.tsx`；后者在组件本地保存单个会话，没有侧边栏、URL 会话状态、分页、Markdown、流式输出、停止/重试或刷新恢复。
- 页面受 `frontend/components/route-guard.tsx` 保护，但 `chat-bot-panel.tsx` 调用 `POST /api/v1/chat/chat` 时没有携带 JWT；前端隐藏页面不能形成后端授权边界。
- `backend/app/api/v1/chat.py` 没有 `get_current_user_context` 依赖，任何调用者均可访问。
- `backend/app/services/portfolio_chat.py` 的 `PortfolioChatMemory` 使用进程内字典与线程锁；重启、多实例、TTL 或进程故障都会丢失历史，且客户端可任意声明 `session_id`。
- 每次请求把该 session 的完整历史发给模型；没有 token 预算、摘要、长期记忆或语义记忆。
- `backend/app/ai/deepseek.py` 是厂商特定同步客户端；`stream=True` 只是请求字段，不提供真正流式消费，也没有统一重试、调用记录或 Prompt 版本治理。
- PostgreSQL 现网 schema 位于 Alembic `0005_add_orig_filename_kb_state`，没有任何 chat/conversation/message/memory 表；实际数据库有 2 个用户，但没有聊天历史可迁移。
- Redis 实例当前没有 key；Chroma `portfolio_knowledge` collection 当前为 0 条。旧 Chat 只有易失内存数据，无法也无需迁移。
- `backend/app/schemas/common.py` 已有统一 envelope，但错误响应没有 `request_id`；`backend/app/core/logging.py` 没有脱敏器。`.env.example` 含疑似真实凭据，必须在实施前轮换并从示例文件移除。
- 前端没有自动化测试框架，也没有 Markdown 渲染依赖；当前共享请求层 `frontend/lib/api.ts` 只处理一次性 JSON 响应。

## 3. 重构目标与成功指标

### 3.1 目标

1. 每个已登录用户拥有完全隔离的 Conversation、Message 与 Memory。
2. 提供类似 ChatGPT 的多 Conversation 管理、历史恢复和流式交互。
3. PostgreSQL 成为对话与长期记忆的唯一业务事实源；Redis 与 Chroma 均可失效、可重建。
4. 建立统一、可 Mock、可观测的 LLM 调用层和分层 Memory/Context Assembly。
5. 为未来 RAG、Tool Calling、Agent 与 Human-in-the-loop 保留明确扩展点，不提前实现 Agent Runtime。

### 3.2 可度量指标

- 跨用户资源访问测试 100% 被拒绝，且不存在仅靠前端保护的接口。
- `client_request_id` 重放不重复创建用户消息、不重复调用 LLM。
- 已提交消息刷新后可从 PostgreSQL 恢复；Redis 全量清空后不丢历史。
- 正常流首事件目标 P95 ≤ 2 秒（不含上游模型不可控延迟时单独观测），接口可用性目标 99.9%。
- 所有 LLM run 可用 `request_id`、`conversation_id`、`message_id` 追踪，日志不含密钥/JWT/完整敏感正文。
- 对话列表和消息列表均为稳定游标分页，不随并发写入发生重复或跳项。

## 4. 用户角色

| 角色 | 能力 | 限制 |
|---|---|---|
| 匿名访客 | 访问公开首页、进入登录页 | 不得调用任何 Chatbot API |
| 登录用户 | 管理自己的 Conversation、Message 与可见 Memory | 永远不能指定或访问他人的数据所有者 |
| 系统管理员 | 本阶段与普通用户使用相同 Chatbot 资源接口 | 不自动获得查看用户聊天正文的能力；未来审计接口须单独授权 |
| 运维人员 | 查看脱敏指标、错误码和健康状态 | 默认不能查看 Prompt/消息正文 |

V1 不新增 Chatbot 专属 RBAC 权限；“已认证 + 资源所有权”即普通用户授权规则。管理员跨用户访问属于明确非目标。

## 5. 核心用户流程

1. 用户登录，进入 `/chat-bot`；前端加载最近 Conversation 或显示空状态。
2. 用户新建 Conversation，URL 更新为 `/chat-bot?conversation=<id>`。
3. 用户输入消息；客户端生成 UUID `client_request_id`，先保留草稿，再以 Bearer JWT 发起 POST SSE 请求。
4. 服务端认证、校验所有权和幂等性，保存用户消息与 pending Assistant 消息，然后开始流式返回。
5. 前端合并 `message.delta`，收到完成/失败/取消事件后以服务端状态为准；刷新页面可重新获取权威消息状态。
6. 用户可切换、重命名、归档、恢复或软删除 Conversation；列表按最后活动时间倒序。
7. 用户可查看、修改或删除已公开的长期记忆；低置信度和敏感候选不自动注入。

## 6. 功能范围

### 6.1 Conversation 管理

- 创建、列表、详情、重命名、自动标题、归档、恢复、软删除。
- 状态为 `active`、`archived`、`deleted`；删除后普通接口不可见，恢复仅适用于 archived。
- 列表按 `(last_message_at DESC, id DESC)` 稳定游标分页；默认 20、最大 100，均由配置/Schema 约束。
- 标题默认“新对话”；首轮成功后延迟生成，失败不影响聊天，用户手工标题永远优先。
- 所有查询同时过滤 `resource_id` 与从 JWT 获取的 `current_user_id`；不存在和无权访问统一返回 404，减少资源枚举。

### 6.2 Message 管理

- 支持 `user`、`assistant`，Schema 为未来 `system`、`tool` 预留角色。
- 状态为 `pending`、`streaming`、`completed`、`failed`、`cancelled`。
- 严格 sequence 排序、历史向前游标分页、流式生成、停止、失败重试、重新生成和 token 统计。
- 用户消息入库成功但 LLM 失败时保留用户消息，Assistant 标记 `failed` 并保存脱敏错误码；允许基于该 user message 重试。
- 同一 Conversation 默认只允许一个未终止 Assistant run；并发请求返回 `CHATBOT_CONVERSATION_BUSY`（409）。
- 客户端断线不删除数据；服务端尽力继续生成并落库。客户端重连后通过消息 GET 恢复最终状态。本版不承诺断点续传 token；SSE `id` 用于事件排序和诊断。

### 6.3 Memory 体验

- 对话历史：PostgreSQL 永久消息记录，可分页、可完整恢复。
- 短期记忆：Redis 中“摘要 + 最近消息滑动窗口”，默认最近 20 条、TTL 7 天；数值通过环境变量配置。
- 长期记忆：从已完成轮次提取稳定偏好、目标、项目背景和明确“请记住”事实，原文与状态存 PostgreSQL。
- 语义记忆：对激活的长期记忆建立 Chroma 索引；只用于相关召回，不替代长期记忆表。
- Memory API 在首版对登录用户开放列表、详情、修改和删除，以保证知情、纠错和遗忘权；不开放批量导入或跨用户共享。
- 低于配置置信度（默认 0.75）的记忆不自动注入；密码、密钥、token、支付卡、政府证件、精确健康/生物信息等禁止自动记忆。
- 提取、Embedding 或索引失败不阻塞主聊天；保留可重试状态，由无新增队列的延迟任务/运维补偿命令处理。

### 6.4 上下文装配

上下文按以下优先级纳入 token 预算：System Prompt > 当前用户消息 > 最近消息 > Conversation Summary > 已确认长期记忆 > 语义相关记忆。每段带内部来源标识，去重、过滤过期和低置信度内容，并将检索内容作为不可信数据而非指令。未来可插入 RAG Context、Tool Results、Agent State 和 Human Approval State。

### 6.5 LLM 治理

- 上层只依赖 `LLMClient` 协议，不直接引用 DeepSeek SDK/HTTP 字段。
- 支持同步与流式、超时、有限重试、统一异常、token usage、request tracing、Prompt 版本和 Mock。
- 首版默认仍使用现有 DeepSeek OpenAI-compatible API；模型、Base URL、超时、重试次数全部配置化。
- 只在请求尚未产生任何 token 且错误可重试时自动重试；避免产生重复/拼接答案。

## 7. 前端需求

### 7.1 Conversation Sidebar

列表、新建、切换、重命名、删除/归档、加载更多、当前项高亮及空/加载/错误状态。归档项可通过筛选查看。删除需要确认。

### 7.2 Chat 主区

历史向上加载、用户/Assistant 气泡、Markdown 与安全代码块、流式输出、停止、重新生成、失败重试、发送/错误状态。仅当用户位于底部附近时自动滚动；向上浏览时展示“回到底部”。404 显示不存在或无权访问的统一提示。

### 7.3 输入区

多行输入；Enter 发送、Shift+Enter 换行；空白与超长校验；生成中默认禁用新发送但提供停止；发送成功入队后清空输入，网络/认证失败前保留草稿。前端防重复只是 UX，最终幂等由后端保证。

### 7.4 状态边界

- PostgreSQL/API 是服务端状态权威；前端只缓存列表、分页消息、草稿与流中临时 delta。
- Conversation ID 保存在 URL query；刷新后先用 ID 拉详情，再拉消息。
- 不引入新的全局状态库：沿用 React hooks/context，按 feature 拆分 query/state hooks；如复杂度增长再单独评审。
- logout 时清空 Chatbot 内存缓存、流控制器和用户相关 local/session storage；不得把消息正文持久化到浏览器长期存储。

## 8. 后端需求

- 所有具体路由置于 `backend/app/chatbot/api`，业务服务、repository、schema、model、memory、llm 均留在 `backend/app/chatbot`。
- 全局 `backend/app/api/router.py` 只注册 Chatbot router；复用 `get_db_session`、`get_current_user_context`、`Settings`、cache/chroma 基础设施。
- Repository 必须把 `user_id` 作为所有资源查询参数；Service 管事务和状态机；Router 只做协议适配。
- 主链路事务只覆盖本地数据库状态转换，不跨越外部 LLM/Redis/Chroma 调用保持长事务。
- 统一错误 envelope 增加 `request_id`；通过中间件接受合法 `X-Request-ID` 或生成 UUID。

## 9. 生命周期

### 9.1 Conversation

`active` 可聊天、重命名、归档或删除；`archived` 只读，可恢复或删除；`deleted` 对用户接口不可见。删除是 PostgreSQL 软删除，事务提交后清理 Redis，再删除 Chroma 中该 Conversation 派生向量；清理失败记录重试状态。默认 30 天后才允许运维物理清理，保留期配置化。

### 9.2 Message

用户消息与 pending Assistant 在一个短事务中创建。Assistant 随流转为 `streaming`，最终进入 `completed`、`failed` 或 `cancelled`。终态不可再写 delta。重新生成创建新的 Assistant message，以原 user message 为 `parent_message_id`，不覆盖历史答案。

## 10. 非功能需求

- 安全：JWT、所有权、数据库唯一/外键约束、Chroma `user_id` 服务端过滤、Redis key 用户隔离、日志脱敏。
- 一致性：PostgreSQL 权威；Redis 锁只能优化并发，数据库唯一约束与行锁仍是最终保障。
- 性能：列表查询必须命中组合索引；SSE 禁用代理缓冲；Redis miss 可从 PostgreSQL 重建。
- 可用性：LLM、Redis、Chroma 分别降级，Redis/Chroma 故障不应使历史不可读。
- 隐私：默认不记录完整 Prompt/正文；保留与删除策略可配置，Memory 对用户可见可删。
- 可测试性：LLM、Redis、Chroma 均通过协议/适配器注入；单元测试无外网依赖。
- 兼容性：新 API 位于 `/api/v1/chatbot`。旧 `/api/v1/chat/chat` 只保留一个发布周期的明确弃用适配层，内部必须调用新 service，不保留双份逻辑；随后返回 410 并删除。

## 11. 错误与边界场景

| 场景 | 期望行为 |
|---|---|
| 未登录/Token 过期 | 401；前端保留未发送草稿并跳转登录 |
| Conversation 不存在或属他人 | 统一 404，不泄露存在性 |
| 重复 `client_request_id` | 返回原消息/run 状态，不再次调用 LLM |
| 同会话并发发送 | 一个成功，其余 409 busy |
| LLM 超时/错误 | 用户消息保留，Assistant failed，可重试 |
| 产生 delta 后断线 | 后端尽力完成并落库；刷新 GET 恢复，不自动重复调用 |
| Redis miss/宕机 | 从 PostgreSQL 重建；不可用时直接用数据库上下文继续 |
| Chroma 不可用 | 跳过语义记忆并记录降级指标，聊天继续 |
| Summary 失败 | 保留旧 summary，缩小 recent messages 时不得越过未总结边界 |
| 页面重复点击 | UI 禁用 + 相同 idempotency key + DB 唯一约束 |
| 删除时索引清理失败 | Conversation 保持 deleted；补偿任务重试，不恢复可见性 |

## 12. 本阶段明确不实现

- 完整 Multi-Agent Runtime、复杂工作流编排、任意第三方 Tool Marketplace。
- 企业级多 Provider 智能路由、跨用户共享记忆、管理员阅读用户对话。
- 多模态文件分析、音视频聊天、消息分支编辑、多人协作 Conversation。
- 未经确认的敏感信息自动记忆、全自动长期记忆无审核注入。
- WebSocket、跨节点可恢复的逐 token 事件日志、独立消息队列。

## 13. 验收标准

1. 登录用户能创建、分页浏览、打开、改名、归档、恢复和删除自己的 Conversation。
2. Conversation/Message/Memory 的跨用户 ID 访问全部返回 404，Chroma 查询强制 `user_id` filter。
3. 消息可流式显示并落 PostgreSQL；刷新后状态与内容一致。
4. LLM 失败、超时、取消均产生明确终态和稳定错误码，可重试/重新生成。
5. 重复 `client_request_id` 和并发发送不会重复调用模型或破坏 sequence。
6. 清空 Redis 后可从 PostgreSQL 恢复 recent/summary；清空 Chroma 后可从激活 memory 重建。
7. 用户可查看、修改和删除自己的长期记忆；删除同步触发向量清理。
8. 日志与错误响应均含 request_id；自动化扫描确认不含 JWT、API key、数据库/Redis URL 或完整敏感正文。
9. 前端满足侧边栏、历史分页、Markdown、停止、重试、滚动与 logout 清理需求。
10. 单元、集成、前端测试覆盖任务书列出的核心链路，现有 Knowledge/Browser/Office/Admin/Auth 测试不回归。

## 14. 未来扩展

`ContextSource`/`ContextSection` 可增加知识 RAG、Tool Result、Agent State；`LLMClient` 可增加 tool call 事件；Message 的 `content_json` 与 role 为结构化内容预留空间；LLM run 与 parent message 支持未来分支和 Human Approval。扩展仍必须遵守所有权、来源标识和 token 预算。

## 15. 待确认事项

以下事项无法仅凭仓库确定，均给出可实施默认值，不阻塞评审：

1. **物理清理保留期**：默认 30 天；如有合规要求应在实施前调整。
2. **长期记忆产品开关**：默认启用“用户可见可删”，自动提取可用环境变量逐步放量。
3. **旧接口兼容期**：默认一个发布周期；若没有外部调用方，可在新前端切换后直接返回 410。
4. **LLM 生成断线策略**：默认后端继续到终态；若上游成本优先，可改为检测断线即取消。

