# Portfolio Chatbot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有易失、无认证的 Portfolio Chat 重构为用户隔离、持久化、可流式恢复且具备分层 Memory 的生产级 Chatbot 模块。

**Architecture:** 在现有 FastAPI/Next.js 中采用模块化单体。PostgreSQL 是唯一事实源，Redis 是可重建短期层和并发优化，ChromaDB 是可重建语义索引，LLM 通过 provider-neutral client 调用；所有 Chatbot 业务代码位于独立 feature/module 内。

**Tech Stack:** Python 3.12、FastAPI、Pydantic 2、SQLAlchemy 2、Alembic、PostgreSQL、Redis 7、ChromaDB、httpx、pytest、Next.js 14、React 18、TypeScript、Tailwind CSS、SSE over fetch。

## Global Constraints

- 实施前必须评审并批准本目录四份文档；不得在文档评审阶段修改业务代码。
- 复用现有 PostgreSQL、Redis、ChromaDB、JWT/RBAC、FastAPI、Next.js；不新增数据库、消息队列或 Agent 框架。
- Chatbot API/Service/Repository/Schema/Model/Memory/LLM 代码统一进入 `backend/app/chatbot`；全局 Router 只做注册。
- 前端 feature 统一进入 `frontend/features/chatbot`，路由保持 `/chat-bot`。
- PostgreSQL 是 Conversation、Message、Summary、Memory、LLM run 的最终事实源；Redis/Chroma 必须可重建。
- 所有资源查询同时过滤 resource ID 和从 JWT 得到的 user ID；禁止客户端指定 owner。
- 模型、TTL、Top K、相似度、token budget、窗口和 timeout 必须配置化。
- API key、JWT、数据库/Redis URL、完整敏感正文不得写日志。
- 每个 Task 独立测试、评审、提交；失败时只回滚该 Task，不跨 Task 混合提交。
- TDD：先写失败测试并确认预期失败，再实现最小闭环，最后运行 Task 指定回归。

## 1. 阶段与依赖总览

```text
CB-000 → CB-001 → CB-002 → CB-003
                         ├→ CB-004 → CB-005 → CB-006
                         ├→ CB-007 → CB-008 → CB-009
                         └→ CB-010 → CB-011 → CB-012 → CB-013
CB-006 + CB-008 + CB-013 → CB-014 → CB-015
CB-005 → CB-016 → CB-017
CB-008 + CB-017 → CB-018
CB-014 + CB-018 → CB-019 → CB-020
CB-015 + CB-020 → CB-021 → CB-022
```

| Phase | Task | 可独立交付物 |
|---:|---|---|
| 0 | CB-000、CB-001 | 安全配置基线、request-id/error envelope |
| 1 | CB-002、CB-003 | ORM 模型与 Alembic migration |
| 2 | CB-004、CB-005 | 模块骨架、Repository |
| 3 | CB-006 | Conversation Service/API |
| 4 | CB-007 | Message Repository/历史 API |
| 5 | CB-008 | Provider-neutral LLM Client |
| 6 | CB-009 | 非流式 Chat 主链路 |
| 7 | CB-010 | SSE 流式链路 |
| 8 | CB-011 | Redis 短期记忆 |
| 9 | CB-012 | Conversation Summary |
| 10 | CB-013 | PostgreSQL 长期记忆 |
| 11 | CB-014 | Chroma 语义记忆 |
| 12 | CB-015 | Context Assembly 集成 |
| 13 | CB-016 | 前端测试基础与 Sidebar |
| 14 | CB-017 | 前端聊天主区与流消费 |
| 15 | CB-018 | 停止、重试、重新生成与恢复 |
| 16 | CB-019 | 安全、幂等与并发加固 |
| 17 | CB-020 | 日志、指标与错误治理 |
| 18 | CB-021 | 旧 Portfolio Chat 切换和清理 |
| 19 | CB-022 | 全量集成、迁移演练与验收 |

## 2. Task 明细

### Task CB-000（Phase 0）：安全配置与秘密轮换基线

**依赖：** 无。

**目标：** 移除仓库中的疑似真实凭据、统一环境变量名称、建立日志脱敏基线；外部凭据由人工轮换，不写入 Git。

**涉及文件：**

- 修改：`backend/.env.example`、`backend/app/core/config.py`、`backend/app/core/logging.py`、`backend/app/storage/cache.py`
- 修改：`docker-compose.yml`、`docker-compose.prod.yml`、`frontend/lib/api.ts`、`README.md`
- 新增：`backend/tests/test_logging_redaction.py`、`backend/tests/test_configuration_secrets.py`

**数据库变化：** 无。

**接口变化：** 前端/Compose 统一使用 `NEXT_PUBLIC_BACKEND_URL`；不改变业务路由。

**实现步骤：**

- [ ] 写测试，扫描示例配置不得出现 `sk-`、带凭据数据库 URL、真实 admin 密码，并验证 `log_event` 对 `authorization/token/api_key/password/*_url` 脱敏。
- [ ] 运行测试确认失败：`$env:PYTHONPATH='backend'; .\.venv\Scripts\python -m pytest backend/tests/test_logging_redaction.py backend/tests/test_configuration_secrets.py -v`。
- [ ] 把 `.env.example` 全部改为占位符；实现递归 key/URL 脱敏；删除 cache backend 日志中的原始 `redis_url`。
- [ ] 统一 Compose、README 和 `frontend/lib/api.ts` 的公开后端变量；保留 `http://127.0.0.1:8000` 本地默认值。
- [ ] 人工轮换已暴露的 DeepSeek、DashScope、数据库与 JWT 凭据，并记录在外部秘密管理系统；不得把新值写入仓库。

**单元测试：** 脱敏嵌套 dict/list、大小写 key、带 userinfo URL、普通非敏感字段保留。

**集成测试：** 使用占位环境启动 Settings，验证不打印秘密且前端 base URL 与 Compose 一致。

**验收条件：** 仓库扫描无真实凭据模式；日志输出不含原值；配置测试全绿。

**风险：** 轮换遗漏会保留外部访问风险；环境变量改名可能使已部署前端失联。

**回滚方式：** 回滚变量名代码但绝不恢复旧秘密；部署层临时同时注入新旧变量完成过渡。

**建议 Commit Message：** `security(chatbot-task00): remove exposed secrets and redact logs`

### Task CB-001（Phase 0）：Request ID 与统一错误契约

**依赖：** CB-000。

**目标：** 为 JSON 与未来 SSE 请求建立稳定 request_id 和 Chatbot 错误映射。

**涉及文件：**

- 修改：`backend/app/main.py`、`backend/app/schemas/common.py`、`backend/app/core/errors.py`
- 新增：`backend/app/core/request_id.py`、`backend/tests/test_request_id.py`、`backend/tests/test_error_envelope.py`

**数据库变化：** 无。

**接口变化：** 所有 JSON envelope 增加 `request_id`；响应 Header 增加 `X-Request-ID`；ErrorDetail 增加可选 `details`。

**实现步骤：**

- [ ] 写失败测试：合法客户端 ID 沿用、非法/缺失 ID 生成、422/401/500 envelope 都带相同 ID。
- [ ] 运行：`$env:PYTHONPATH='backend'; .\.venv\Scripts\python -m pytest backend/tests/test_request_id.py backend/tests/test_error_envelope.py -v`，确认失败原因是中间件/字段缺失。
- [ ] 用 `contextvars.ContextVar` 实现 request-id middleware；只接受长度 ≤128 的 UUID/ULID 格式。
- [ ] 扩展 Schema 和异常 handler；Chatbot 业务错误预留 `code/http_status/details`，未知异常仅返回通用信息。
- [ ] 运行本 Task 测试与现有 `test_auth.py`、`test_portfolio_chat.py`。

**单元测试：** ID 校验、上下文清理、业务错误映射。

**集成测试：** FastAPI TestClient 校验 header/body/log 三处 ID 一致。

**验收条件：** 所有错误路径可用 request_id 追踪且不回显异常正文。

**风险：** contextvar 未清理导致并发请求串号。

**回滚方式：** 移除 middleware 与新增字段；客户端必须继续容忍没有 request_id 的旧响应。

**建议 Commit Message：** `feat(chatbot-task01): add request tracing and error envelope`

### Task CB-002（Phase 1）：Chatbot ORM 模型与元数据注册

**依赖：** CB-001。

**目标：** 定义五类核心表的 SQLAlchemy 模型、关系、状态约束和索引，不修改数据库。

**涉及文件：**

- 新增：`backend/app/chatbot/__init__.py`、`backend/app/chatbot/models/__init__.py`
- 新增：`backend/app/chatbot/models/conversation.py`、`message.py`、`memory.py`、`llm_run.py`
- 修改：`backend/alembic/env.py`
- 新增：`backend/tests/chatbot/test_models.py`

**数据库变化：** 仅声明 `chatbot_conversations`、`chatbot_messages`、`chatbot_conversation_summaries`、`chatbot_memories`、`chatbot_llm_runs`；尚不执行 migration。

**接口变化：** 无。

**实现步骤：**

- [ ] 写 metadata 测试，断言五张表、FK、唯一约束、状态 check、owner/分页索引与 cascade 行为。
- [ ] 运行 `$env:PYTHONPATH='backend'; .\.venv\Scripts\python -m pytest backend/tests/chatbot/test_models.py -v`，确认表未注册而失败。
- [ ] 按架构文档字段实现小文件模型，共用 `app.db.base.Base` 和 UUID/string(36) 现有风格。
- [ ] 在 Alembic composition root 显式 import Chatbot models，禁止把模型重新塞回 `backend/app/db/models.py`。
- [ ] 用临时 SQLite `Base.metadata.create_all` 验证基础关系；PostgreSQL 专属索引留 migration 测试。

**单元测试：** defaults、nullable、relationship、唯一/检查约束 metadata。

**集成测试：** 临时数据库创建、插入 user→conversation→messages→run→memory 并验证 FK。

**验收条件：** 模型职责分文件，Base metadata 完整且现有模型测试不回归。

**风险：** 循环 import 或 Alembic autogenerate 漏表。

**回滚方式：** 删除模块模型与 env import；此 Task 未改数据库。

**建议 Commit Message：** `feat(chatbot-task02): add chatbot database models`

### Task CB-003（Phase 1）：Alembic Migration 与数据库约束

**依赖：** CB-002。

**目标：** 创建可升级、可验证的 `0006` migration，数据库层保障幂等、sequence 和 active run。

**涉及文件：**

- 新增：`backend/alembic/versions/0006_create_chatbot_tables.py`
- 新增：`backend/tests/chatbot/test_migration_0006.py`
- 修改：`backend/tests/test_database_setup.py`

**数据库变化：** 创建五张表、FK、组合索引、`(conversation_id,sequence_number)` 与 `(user_id,conversation_id,client_request_id)` 唯一约束；PostgreSQL 部分唯一索引限制每会话一个 pending/streaming Assistant。

**接口变化：** 无。

**实现步骤：**

- [ ] 写 upgrade/downgrade 测试及 PostgreSQL constraint 测试，确认在 0005 上没有 Chatbot 表。
- [ ] 编写 revision，`down_revision="0005_add_orig_filename_kb_state"`，顺序创建 parent→child，逆序删除。
- [ ] 在临时数据库执行 `upgrade 0005 → head`，核对表、索引和 Alembic version；空库执行全链路 upgrade。
- [ ] 模拟重复 client_request_id、重复 sequence、双 active Assistant，断言数据库拒绝。
- [ ] 验证 downgrade 只用于无生产数据环境；文档注明有数据后采用应用回滚/forward-fix。

**单元测试：** revision metadata、upgrade/downgrade 操作顺序。

**集成测试：** PostgreSQL 上真实唯一/部分索引与 cascade；SQLite 只做兼容子集。

**验收条件：** 新库与 0005 升级都到 head；失败可完整回滚；现有 RAG/RBAC 表不变。

**风险：** 生产 PostgreSQL 锁表或 downgrade 丢数据。

**回滚方式：** 未产生数据时 downgrade 0005；有数据时关闭 feature flag，保留表并 forward-fix。

**建议 Commit Message：** `feat(chatbot-task03): add chatbot alembic migration`

### Task CB-004（Phase 2）：模块骨架与 Conversation Repository

**依赖：** CB-003。

**目标：** 建立 Chatbot 内部依赖方向和 owner-safe Conversation 持久化接口。

**涉及文件：**

- 新增：`backend/app/chatbot/constants.py`、`backend/app/chatbot/api/__init__.py`、`backend/app/chatbot/api/dependencies.py`
- 新增：`backend/app/chatbot/repositories/__init__.py`、`conversation_repository.py`
- 新增：`backend/tests/chatbot/test_conversation_repository.py`

**数据库变化：** 无新 schema；使用 CB-003 表。

**接口变化：** 暂无 HTTP API；内部产生 `ConversationRepository`。

**实现步骤：**

- [ ] 先写 owner 隔离、状态过滤、稳定 cursor、`FOR UPDATE` 获取和 next_sequence 分配测试。
- [ ] 定义方法签名：`create(user_id, title, model)`、`get_owned(conversation_id,user_id,include_deleted=False)`、`list_owned(user_id,status,position,limit)`、`lock_owned(conversation_id,user_id)`、`allocate_sequences(conversation,count)`。
- [ ] SQL 始终显式包含 user_id；list 多取一条计算 has_more，排序 `(last_message_at desc,id desc)`。
- [ ] cursor 编解码放 dependencies/common helper，验证版本和 filter，不在 repository 信任客户端字段。
- [ ] 运行 repository 测试和模型测试。

**单元测试：** cursor round-trip/非法输入、owner 参数必需、状态转换保存。

**集成测试：** 两用户同名会话，跨用户 get/update/delete 都不可见；同 timestamp 分页无重复。

**验收条件：** Repository 不依赖 FastAPI/Service，所有资源操作 owner-safe。

**风险：** cursor 与排序字段不一致产生漂移。

**回滚方式：** 删除模块骨架与 repository；数据库表保留未使用。

**建议 Commit Message：** `feat(chatbot-task04): implement conversation repository`

### Task CB-005（Phase 2）：Message、Memory 与 LLM Run Repository

**依赖：** CB-004。

**目标：** 提供消息历史、幂等查找、Memory 和 LLM run 的 owner-safe 数据访问。

**涉及文件：**

- 新增：`backend/app/chatbot/repositories/message_repository.py`、`memory_repository.py`、`llm_run_repository.py`
- 新增：`backend/tests/chatbot/test_message_repository.py`、`test_memory_repository.py`、`test_llm_run_repository.py`

**数据库变化：** 无。

**接口变化：** 暂无 HTTP API。

**实现步骤：**

- [ ] 写测试覆盖 message before cursor、顺序、owner、idempotency lookup、active run、memory active/expiry 与 run finalize。
- [ ] 实现 Message 方法：批量 create user+assistant、按 owner 分页、按 client_request_id 查原请求、checkpoint、终态 compare-and-set。
- [ ] 实现 Memory 方法：candidate/active list、normalized hash 去重、soft delete、embedding backlog claim。
- [ ] 实现 LLM run create/stream/finalize/stale scan；所有更新使用期望旧状态防终态反写。
- [ ] 运行三个 repository 测试和 CB-004 回归。

**单元测试：** 状态 CAS、分页转换、过期过滤、token 合计。

**集成测试：** 两用户 IDOR、重复幂等键、部分终态更新、删除 cascade。

**验收条件：** 任何 message/memory/run ID 都无法绕过 current_user_id；终态不可回退。

**风险：** repository 承担业务状态机导致职责膨胀。

**回滚方式：** 删除新增 repository；无外部 API 依赖。

**建议 Commit Message：** `feat(chatbot-task05): add chatbot persistence repositories`

### Task CB-006（Phase 3）：Conversation Service 与 API

**依赖：** CB-005。

**目标：** 交付登录用户的 Conversation 创建、列表、详情、修改、归档、恢复和软删除。

**涉及文件：**

- 新增：`backend/app/chatbot/schemas/common.py`、`conversation.py`
- 新增：`backend/app/chatbot/services/__init__.py`、`conversation_service.py`
- 新增：`backend/app/chatbot/api/conversations.py`、`router.py`
- 修改：`backend/app/api/router.py`
- 新增：`backend/tests/chatbot/test_conversation_service.py`、`test_conversation_api.py`

**数据库变化：** 写 `chatbot_conversations`；删除只设 deleted_at/cleanup_status。

**接口变化：** 新增文档 03 第 5 章七个 Conversation endpoints。

**实现步骤：**

- [ ] 先写 service 状态机和 API 认证/owner/分页/错误 envelope 测试。
- [ ] 实现 Pydantic Schema；title trim 后 1–200，model 由 Settings allowlist 验证。
- [ ] Service 管事务和 `active↔archived→deleted`；手工标题设 manual；不存在/非 owner 统一 not found。
- [ ] Router 每个入口依赖 `get_current_user_context` 与 `get_db_session`，只做协议映射。
- [ ] 在全局 router 只 include `chatbot_router`；运行新 API 测试和 auth/admin/router 回归。

**单元测试：** 状态转换、空 update、标题优先级、cursor、model allowlist。

**集成测试：** 创建/列表/详情/归档/恢复/删除闭环，另一用户所有操作 404。

**验收条件：** OpenAPI 与 03 文档一致；未登录 401；无 Chatbot 逻辑进入全局 `api/v1`。

**风险：** 全局 router 注册影响启动；删除清理尚未实现。

**回滚方式：** 移除 router 注册即可隐藏功能，表和数据保留。

**建议 Commit Message：** `feat(chatbot-task06): add conversation management api`

### Task CB-007（Phase 4）：Message 历史 Service 与 API

**依赖：** CB-006。

**目标：** 提供可稳定向上分页、刷新恢复的权威消息历史接口。

**涉及文件：**

- 新增：`backend/app/chatbot/schemas/message.py`、`backend/app/chatbot/services/message_service.py`
- 新增：`backend/app/chatbot/api/messages.py`
- 修改：`backend/app/chatbot/api/router.py`
- 新增：`backend/tests/chatbot/test_message_service.py`、`test_message_api.py`

**数据库变化：** 只读 messages；测试写 fixture。

**接口变化：** 新增 `GET /conversations/{id}/messages`。

**实现步骤：**

- [ ] 写最新页、before cursor、asc 响应顺序、failed partial、跨用户、deleted Conversation 测试。
- [ ] 实现 MessageData/Page Schema，隐藏 user_id、内部 error_message 和 system prompt。
- [ ] Service 先验证 owner/status，再调用 repository；cursor filter/version 错误映射 400。
- [ ] API 默认 limit=50、最大 100，返回 next_cursor/has_more。
- [ ] 运行 Message API、Conversation API 和 envelope 回归。

**单元测试：** cursor 边界、空列表、序列排序、安全投影。

**集成测试：** 120 条消息三页无重复/遗漏，并发插入不改变 before 边界。

**验收条件：** 页面刷新可只靠 PostgreSQL API 恢复消息和终态。

**风险：** 最新页 SQL 倒序取后未恢复 asc。

**回滚方式：** 移除 messages GET router；不影响 Conversation 数据。

**建议 Commit Message：** `feat(chatbot-task07): add paginated message history api`

### Task CB-008（Phase 5）：Provider-neutral LLM Client

**依赖：** CB-005。

**目标：** 把同步/流式模型调用、错误、usage、retry 与 provider 配置封装在 Chatbot LLM 层。

**涉及文件：**

- 新增：`backend/app/chatbot/llm/__init__.py`、`provider.py`、`client.py`、`deepseek_provider.py`
- 新增：`backend/app/chatbot/llm/streaming.py`、`prompt_builder.py`、`exceptions.py`
- 修改：`backend/app/core/config.py`
- 新增：`backend/tests/chatbot/test_llm_client.py`、`test_deepseek_provider.py`、`test_prompt_builder.py`

**数据库变化：** 无。

**接口变化：** 内部协议 `complete(request: ChatCompletionRequest) -> ChatCompletionResult` 与 `stream(request: ChatCompletionRequest) -> Iterator[LLMStreamEvent]`。

**实现步骤：**

- [ ] 用 httpx MockTransport 写同步、chunked SSE、usage、429/5xx、timeout、非法 JSON、断流测试并确认失败。
- [ ] 定义 provider-neutral request/result/event dataclass 与异常层级；上层不得 import `DeepSeekError`。
- [ ] 实现 DeepSeek OpenAI-compatible adapter，使用 `httpx.Client.stream` 增量解析 data 行和 `[DONE]`。
- [ ] retry 只允许在未产出 delta 且错误可重试时发生，默认 2 attempts，所有参数来自 Settings。
- [ ] PromptBuilder 返回 prompt_version，不记录原始敏感 Prompt；运行 LLM 单测和现有 `test_deepseek_client.py`。

**单元测试：** 事件转换、retry gate、timeout、finish reason、usage 缺失、资源 close。

**集成测试：** Mock provider 完整/部分/失败流；不访问外网。

**验收条件：** Service 可完全用 fake LLM 测试；同步和流式不依赖厂商字段。

**风险：** 上游 SSE 方言或多字节 chunk 边界解析错误。

**回滚方式：** 删除新 LLM 层；旧 Portfolio Chat 暂时仍用现有 client。

**建议 Commit Message：** `refactor(chatbot-task08): add provider neutral llm client`

### Task CB-009（Phase 6）：非流式 Chat 主链路

**依赖：** CB-006、CB-007、CB-008。

**目标：** 先建立可事务验证的持久化 Chat 编排，暂不暴露 SSE。

**涉及文件：**

- 新增：`backend/app/chatbot/schemas/chat.py`、`backend/app/chatbot/services/chat_service.py`
- 修改：`backend/app/chatbot/api/dependencies.py`
- 新增：`backend/tests/chatbot/test_chat_service.py`、`test_chat_failure_recovery.py`

**数据库变化：** 原子创建 user message、pending assistant、llm_run；完成事务更新消息/run/conversation。

**接口变化：** 仅内部 `ChatService.complete(user_id, conversation_id, content, client_request_id)`，不新增公开 endpoint。

**实现步骤：**

- [ ] 写成功、用户落库后 LLM 失败、timeout、重复 request、同会话 busy、状态 finalize 测试。
- [ ] 接受消息事务：lock owner Conversation、校验 active、幂等查找、分配两个 sequence、写三条相关记录后 commit。
- [ ] 事务外调用 `LLMClient.complete`，首版 context 仅 system + PostgreSQL 最近消息 + current message。
- [ ] 完成/失败各用短事务 CAS 更新 Assistant/LLM run/last_message_at；保存安全 error_code。
- [ ] 运行 Chat service、repository、LLM 全组测试。

**单元测试：** 状态机、幂等回放、payload hash conflict、token/latency 写入。

**集成测试：** LLM 失败后 user message 保留、Assistant failed 可查询、无长事务跨 LLM。

**验收条件：** PostgreSQL 可完整恢复每轮；重复请求只产生一组记录、一次模型调用。

**风险：** 接受事务与外部调用边界不清导致长锁。

**回滚方式：** 停用内部 service；已落记录保持可审计，不删除。

**建议 Commit Message：** `feat(chatbot-task09): implement durable chat orchestration`

### Task CB-010（Phase 7）：SSE 流式输出

**依赖：** CB-009。

**目标：** 按 03 文档契约把持久化 Chat 转为 POST fetch + SSE 流。

**涉及文件：**

- 修改：`backend/app/chatbot/services/chat_service.py`、`backend/app/chatbot/api/messages.py`、`backend/app/chatbot/api/router.py`
- 新增：`backend/app/chatbot/schemas/stream.py`、`backend/app/chatbot/services/stream_service.py`
- 新增：`backend/tests/chatbot/test_chat_stream.py`、`test_stream_api.py`

**数据库变化：** Assistant pending→streaming checkpoint→终态；LLM run 同步状态。

**接口变化：** 新增 `POST /conversations/{id}/messages`；事件为 `message.created`、`message.delta`、`message.completed`、`message.failed`、`message.cancelled`、`usage.updated`、`stream.end`，顺序严格遵循 03 文档。

**实现步骤：**

- [ ] 写每种事件固定 JSON、sequence、keepalive、Unicode chunk、零 delta、部分失败、客户端断线测试。
- [ ] 在 headers 前完成接受事务；StreamingResponse generator 只消费规范化 `LLMStreamEvent`。
- [ ] 实现按 1 秒或 512 字符配置 checkpoint，终态事件携带数据库最终 content。
- [ ] 捕获 socket 断开但默认继续后台消费并落终态；不得把成功 run 改 failed。
- [ ] 设置 `Cache-Control: no-cache`、`X-Accel-Buffering: no`；运行 SSE 和 Task SSE 现有回归。

**单元测试：** SSE encoder/parser fixtures、事件顺序、terminal exactly-once、usage missing。

**集成测试：** TestClient/httpx 流接收、LLM timeout、断流、刷新后 GET 最终消息。

**验收条件：** 事件完全符合 03 文档，失败前/后分别走 JSON/SSE 错误，数据库状态权威。

**风险：** FastAPI 同步 worker 在断线后执行生命周期、代理缓冲。

**回滚方式：** 移除 POST route，保留 CB-009 非流式 service 供后续修复。

**建议 Commit Message：** `feat(chatbot-task10): stream chatbot responses over sse`

### Task CB-011（Phase 8）：Redis 短期记忆与可重建状态

**依赖：** CB-010。

**目标：** 实现 recent/summary/state cache、TTL 与 PostgreSQL miss 重建，不把 Redis 当事实源。

**涉及文件：**

- 新增：`backend/app/chatbot/memory/__init__.py`、`short_term_memory.py`
- 新增：`backend/app/chatbot/memory/redis_adapter.py`、`backend/tests/chatbot/test_short_term_memory.py`
- 修改：`backend/app/core/config.py`、`backend/app/chatbot/services/chat_service.py`

**数据库变化：** 无。

**接口变化：** 无；内部 context 读取优先 Redis。

**实现步骤：**

- [ ] 写 key 隔离、TTL、hit、miss、version mismatch、Redis failure、PG rebuild 和多用户测试。
- [ ] 实现精确 key `chatbot:{env}:v{version}:user:{user}:conversation:{conversation}:{type}`。
- [ ] recent 默认 20、TTL 默认 7 天且全部 Settings 化；重建读取 latest completed summary + recent messages。
- [ ] DB commit 后 best-effort refresh；Redis exception 记录降级并继续，不使用内存数据冒充分布式一致性。
- [ ] 运行 fake Redis 单测和真实 Redis 集成标记组。

**单元测试：** key normalization、窗口裁剪、序列排序、TTL 参数、重建 payload。

**集成测试：** 清空 Redis 后下一次 context 与 PostgreSQL 一致；Redis 停机仍能回复。

**验收条件：** Redis 数据可全部删除而不丢聊天历史；key 必含 env/user/conversation/type/version。

**风险：** 当前通用 adapter 会重复 prefix/静默内存 fallback，不能直接用于锁语义。

**回滚方式：** feature flag 关闭 short memory，ChatService 直接查 PostgreSQL。

**建议 Commit Message：** `feat(chatbot-task11): add rebuildable short term memory`

### Task CB-012（Phase 9）：Conversation Summary

**依赖：** CB-011、CB-008。

**目标：** 生成版本化、连续区间摘要并在失败时安全降级。

**涉及文件：**

- 新增：`backend/app/chatbot/memory/conversation_summary.py`
- 修改：`backend/app/chatbot/repositories/conversation_repository.py`、`backend/app/chatbot/services/chat_service.py`
- 新增：`backend/tests/chatbot/test_conversation_summary.py`

**数据库变化：** 写 `chatbot_conversation_summaries`，只读取最新 completed 版本。

**接口变化：** 无。

**实现步骤：**

- [ ] 写触发阈值、连续 start/end、版本递增、并发生成、LLM 失败保留旧版、Redis refresh 测试。
- [ ] 触发条件为未总结 completed 消息数或 token 比例达到 Settings 阈值；默认 20 条或预算 60%。
- [ ] 使用独立 summary prompt version 和模型配置；先写 pending，成功后 completed，不能覆盖旧行。
- [ ] 失败标 failed，不推进 summary_end；context 退化为旧 summary + 预算内 recent。
- [ ] 通过有界 delayed executor 提交，启动扫描陈旧 pending；不得引入消息队列。

**单元测试：** trigger、区间、版本、降级、标题/summary prompt 隔离。

**集成测试：** 40+ 消息生成两版摘要，Redis miss 从最新 completed 版重建。

**验收条件：** 任意失败不会“吃掉”未总结消息；多实例只产生一个有效版本。

**风险：** 进程内延迟任务崩溃丢执行机会。

**回滚方式：** 关闭 summary flag；保留历史表，Context 使用 recent messages。

**建议 Commit Message：** `feat(chatbot-task12): add versioned conversation summaries`

### Task CB-013（Phase 10）：PostgreSQL 长期记忆

**依赖：** CB-005、CB-008、CB-010。

**目标：** 从完成轮次延迟提取可解释、可去重、可由用户管理的长期记忆。

**涉及文件：**

- 新增：`backend/app/chatbot/memory/long_term_memory.py`、`memory_extractor.py`
- 新增：`backend/app/chatbot/services/memory_service.py`、`backend/app/chatbot/schemas/memory.py`
- 新增：`backend/app/chatbot/api/memories.py`
- 修改：`backend/app/chatbot/api/router.py`、`backend/app/core/config.py`
- 新增：`backend/tests/chatbot/test_memory_extractor.py`、`test_memory_service.py`、`test_memory_api.py`

**数据库变化：** 写/更新 `chatbot_memories`，维护 source_message_ids、normalized_hash、status、embedding_status。

**接口变化：** 新增 Memory list/detail/patch/delete 四个 endpoints。

**实现步骤：**

- [ ] 写明确“记住/忘记”、稳定偏好、低置信度、敏感模式、重复、冲突合并、来源、跨用户 API 测试。
- [ ] 规则层先排除 secret/password/token/payment/government-id/健康生物敏感模式，再调用 LLM 输出严格候选 Schema。
- [ ] 规范化 hash 去重；同 type 冲突创建新 active 并 supersede 旧 memory，保留来源；低于默认 0.75 不自动 active。
- [ ] 提取在主回复完成后延迟执行，失败写 failed/backlog，不改变 Message completed。
- [ ] Memory API 只允许本人 candidate/active/superseded；编辑内容令 embedding pending；删除先软删。

**单元测试：** 规则/LLM 混合、敏感拒绝、confidence/importance、dedupe/merge、source 校验。

**集成测试：** 回复成功而提取失败、用户编辑/删除、两用户同内容完全隔离。

**验收条件：** Memory 对用户可见可纠错可遗忘；敏感候选不入库为 active；提取不阻塞聊天。

**风险：** LLM 误提取或用户隐私预期不一致。

**回滚方式：** 关闭 extraction flag；保留 API 供用户查看/删除既有 memory。

**建议 Commit Message：** `feat(chatbot-task13): add governed long term memory`

### Task CB-014（Phase 11）：ChromaDB 语义记忆

**依赖：** CB-013。

**目标：** 为 active 长期记忆建立强制用户过滤、可重建的 Chroma 语义索引。

**涉及文件：**

- 新增：`backend/app/chatbot/memory/semantic_memory.py`、`memory_retriever.py`
- 新增：`backend/app/chatbot/commands/rebuild_memory_index.py`
- 修改：`backend/app/core/config.py`、`backend/app/chatbot/services/memory_service.py`
- 新增：`backend/tests/chatbot/test_semantic_memory.py`、`test_memory_index_rebuild.py`

**数据库变化：** 更新 memory embedding_status/model/version；PostgreSQL 原文不变。

**接口变化：** 无公开 API；新增运维命令 `python -m app.chatbot.commands.rebuild_memory_index --dry-run|--apply`。

**实现步骤：**

- [ ] 写 collection name、metadata、mandatory Chroma `where user_id+status`、PG revalidation、threshold、dedupe、delete/rebuild 测试。
- [ ] collection 使用 `chatbot_memory_{env}_{embedding_version}`；ID=memory_id，metadata 与 02 文档一致。
- [ ] query 默认 top_k=5、candidate multiplier=3、cosine threshold=0.72，全部 Settings 化。
- [ ] Chroma candidate 返回后按 user_id+active 回查 PostgreSQL；禁止沿用先多取后 Python owner filter 的 RAG search。
- [ ] 实现 dry-run/count/checksum/rebuild/switch 流程；写失败标 embedding failed 供补偿。

**单元测试：** where 参数精确断言、score 转换、memory_id/hash 去重、配置解析。

**集成测试：** 两用户相同文本只召回本人；清空 collection 后从 PG 重建计数一致。

**验收条件：** Chroma 丢失不影响事实数据；任何查询都在数据库调用层强制 user filter。

**风险：** embedding 版本/维度与 collection 不匹配。

**回滚方式：** 切回旧 embedding collection 或关闭 semantic flag；Context 跳过语义层。

**建议 Commit Message：** `feat(chatbot-task14): add isolated semantic memory index`

### Task CB-015（Phase 12）：Context Assembly 与 Memory 集成

**依赖：** CB-012、CB-013、CB-014。

**目标：** 用独立、可预算、可溯源的 Context Service 替换“全历史发送”。

**涉及文件：**

- 新增：`backend/app/chatbot/services/context_service.py`、`backend/app/chatbot/llm/token_estimator.py`
- 修改：`backend/app/chatbot/services/chat_service.py`、`backend/app/chatbot/llm/prompt_builder.py`、`backend/app/core/config.py`
- 新增：`backend/tests/chatbot/test_context_service.py`、`test_token_budget.py`、`test_prompt_injection_boundaries.py`

**数据库变化：** 只读 summary/messages/memories；更新 memory last_accessed_at 可延迟 best-effort。

**接口变化：** 无；Chat 生成质量和上下文来源发生内部变化。

**实现步骤：**

- [ ] 写优先级、token budget、recent 正序、过期/低置信度过滤、long/semantic 去重、Redis miss、Chroma failure 测试。
- [ ] 定义 `ContextSection(kind,content,source_ids,priority,trust_level,token_estimate)` 与不可变 `ContextBundle`。
- [ ] 固定优先级：system > current user > recent > summary > long-term > semantic；超预算从低优先级裁剪。
- [ ] 将 memory/retrieval 文本包在 untrusted delimiter，禁止提升为 system；超长单段安全截断。
- [ ] ChatService 只接收 ContextBundle 转换的 messages；记录各层命中计数而不记录正文。

**单元测试：** 预算边界恰好/超一 token、顺序、hash 去重、来源、过滤与降级。

**集成测试：** Redis/Chroma 分别宕机仍完成回复；PG 历史恢复后 prompt 不含全量历史。

**验收条件：** 上下文可解释、预算不超配置、Memory 故障不阻塞主链路。

**风险：** 近似 tokenizer 与真实 token 偏差造成 provider 拒绝。

**回滚方式：** feature flag 切到受限的 PG recent-only builder，不能恢复全历史发送。

**建议 Commit Message：** `feat(chatbot-task15): assemble token bounded chat context`

### Task CB-016（Phase 13）：前端测试基础与 Conversation Sidebar

**依赖：** CB-006。

**目标：** 建立 Chatbot feature、类型安全 API client、URL 会话状态与完整 Sidebar。

**涉及文件：**

- 修改：`frontend/package.json`、`frontend/package-lock.json`、`frontend/app/chat-bot/page.tsx`
- 新增：`frontend/vitest.config.ts`、`frontend/test/setup.ts`
- 新增：`frontend/features/chatbot/api/client.ts`、`types/conversation.ts`、`stores/chatbot-store.ts`
- 新增：`frontend/features/chatbot/hooks/use-conversations.ts`
- 新增：`frontend/features/chatbot/components/chatbot-shell.tsx`、`conversation-sidebar.tsx`
- 新增：`frontend/features/chatbot/__tests__/conversation-sidebar.test.tsx`、`use-conversations.test.tsx`

**数据库变化：** 无。

**接口变化：** 前端消费 Conversation endpoints；不改后端。

**实现步骤：**

- [ ] 添加 Vitest、Testing Library、jsdom 与 test script；先写 URL、加载、空、错误、分页、切换、改名、归档/删除测试并确认失败。
- [ ] `client.ts` 复用 `frontend/lib/api.ts` token/envelope 约定，所有调用显式接收 auth token。
- [ ] store 只用 React reducer/context，不引入第二个状态库；按 user/session 生命周期保存 conversations/cursors/current ID。
- [ ] URL 使用 `?conversation=<uuid>`；刷新从 URL 恢复，404 清 URL；新建与切换更新 URL。
- [ ] logout effect 清 store；运行 `npm test -- --run`、`npm run lint`、`npm run build`。

**单元测试：** reducer、cursor append/dedupe、logout reset、URL helper。

**集成测试：** Sidebar 所有交互及 auth token；另一用户状态不得复用。

**验收条件：** Sidebar 满足 01 文档状态与操作；刷新/切换稳定；无消息正文写 localStorage。

**风险：** 新测试依赖增加 lockfile 变化；Next router mock 不准确。

**回滚方式：** `page.tsx` 切回旧 panel；保留后端 API，不回滚数据。

**建议 Commit Message：** `feat(chatbot-task16): add conversation sidebar feature`

### Task CB-017（Phase 14）：聊天主区、Markdown 与 SSE 消费

**依赖：** CB-007、CB-010、CB-016。

**目标：** 实现历史加载、流式消息合并、安全 Markdown、Composer 和滚动体验。

**涉及文件：**

- 修改：`frontend/package.json`、`frontend/package-lock.json`、`frontend/features/chatbot/components/chatbot-shell.tsx`
- 新增：`frontend/features/chatbot/api/stream.ts`、`types/message.ts`、`types/stream.ts`
- 新增：`frontend/features/chatbot/hooks/use-messages.ts`、`use-chat-stream.ts`
- 新增：`frontend/features/chatbot/utils/merge-stream-event.ts`
- 新增：`frontend/features/chatbot/components/message-list.tsx`、`message-item.tsx`、`chat-composer.tsx`
- 新增：`frontend/features/chatbot/__tests__/chat-stream.test.ts`、`message-list.test.tsx`、`chat-composer.test.tsx`

**数据库变化：** 无。

**接口变化：** 消费 Message GET 与 POST SSE；新增 `react-markdown`、`remark-gfm` 用于安全 Markdown（禁用 raw HTML）。

**实现步骤：**

- [ ] 写 SSE chunk 跨边界、未知事件、sequence 去重、created ID 替换、delta merge、completed 校准、failed/cancelled 测试。
- [ ] 使用 fetch + Bearer/Idempotency-Key + ReadableStream parser，不使用原生 EventSource。
- [ ] 实现历史向上分页并保持 scroll anchor；仅在距底部阈值内自动滚动，否则显示回到底部按钮。
- [ ] Composer：Enter 发送、Shift+Enter 换行、4000 字限制、发送中状态、网络错误保留草稿；UUID 一次生成并在同请求重试复用。
- [ ] Markdown 禁 raw HTML，链接仅 http/https/mailto 且外链 noopener；代码块按纯文本展示。
- [ ] 运行 frontend test/lint/build。

**单元测试：** SSE parser/reducer、键盘行为、草稿清理时机、滚动阈值、安全链接。

**集成测试：** 多页历史 + 流式回复 + 网络中断 + 最终 GET 校准。

**验收条件：** 主区覆盖 01 文档 11.2/11.3；流状态不覆盖权威服务端终态。

**风险：** SSE parser 在 CRLF/多字节边界出错；Markdown XSS。

**回滚方式：** feature flag 隐藏新页面并切旧 panel；不重复提交已持久化消息。

**建议 Commit Message：** `feat(chatbot-task17): add streaming chatbot workspace`

### Task CB-018（Phase 15）：停止、重试、重新生成与刷新恢复

**依赖：** CB-010、CB-017。

**目标：** 交付生成控制和所有失败/刷新恢复 UX。

**涉及文件：**

- 修改：`backend/app/chatbot/api/messages.py`、`backend/app/chatbot/services/chat_service.py`、`backend/app/chatbot/schemas/message.py`
- 新增：`backend/app/chatbot/services/cancellation_service.py`
- 修改：`frontend/features/chatbot/api/client.ts`、`hooks/use-chat-stream.ts`、`components/message-item.tsx`、`chat-composer.tsx`
- 新增：`backend/tests/chatbot/test_generation_controls.py`、`frontend/features/chatbot/__tests__/generation-controls.test.tsx`

**数据库变化：** 新 Assistant variant 保留旧答案；cancel request 更新 active run，终态不可反写。

**接口变化：** 新增 stop、retry、regenerate 三类 endpoints，契约见 03 第 8–9 章。

**实现步骤：**

- [ ] 写 stop 幂等/无 active、cancel race、retry 状态、regenerate latest-turn、刷新 pending/streaming/stale 测试。
- [ ] cancellation 使用进程 token + Redis key，多实例由 generator 轮询；数据库 CAS 是最终状态保障。
- [ ] retry/regenerate 复用原 user message、创建新 Assistant/run，不覆盖旧消息；V1 拒绝非最新 turn 分支。
- [ ] 前端 stop 明确调用 API；切换页面/abort reader不等于 stop；失败消息展示 retry，completed 展示 regenerate。
- [ ] 刷新先 GET Conversation active_generation + latest messages；不自动重新调用模型。

**单元测试：** cancellation token、terminal race、variant mapping、按钮状态。

**集成测试：** streaming 中 stop、timeout 后 retry、completed regenerate、断线后刷新恢复。

**验收条件：** 不产生重复付费调用；所有控制操作有明确终态且历史可审计。

**风险：** stop 与 provider 完成竞态；跨实例 token 丢失。

**回滚方式：** 隐藏控制按钮并移除 routes；保留已生成 variants。

**建议 Commit Message：** `feat(chatbot-task18): add generation controls and recovery`

### Task CB-019（Phase 16）：安全、幂等与并发加固

**依赖：** CB-018、CB-003。

**目标：** 把所有权、DB 约束、Redis 锁、限流和 stale recovery 做成生产级防线。

**涉及文件：**

- 新增：`backend/app/chatbot/services/concurrency_service.py`、`backend/app/chatbot/services/recovery_service.py`
- 修改：`backend/app/chatbot/api/dependencies.py`、各 repositories/services、`backend/app/core/config.py`
- 新增：`backend/tests/chatbot/test_authorization_matrix.py`、`test_idempotency.py`、`test_concurrency.py`、`test_stale_recovery.py`

**数据库变化：** 使用既有行锁/唯一约束；不新增表。必要索引调整必须另建 `0007`，不得修改已发布 0006。

**接口变化：** 稳定 404/409/429 错误码；Header/body Idempotency-Key 一致性强制执行。

**实现步骤：**

- [ ] 建立 Conversation/Message/Memory/Chroma/Redis 的双用户攻击矩阵测试。
- [ ] 实现 Redis `SET NX PX` owner token、Lua compare-delete/renew；Redis 不可用时不宣称获得分布式锁。
- [ ] 数据库行锁 + 唯一约束捕获胜者；payload hash 冲突 409；不同会话允许并发。
- [ ] 增加 user/conversation rate limit、message max、模型 allowlist；只信认证用户。
- [ ] 扫描超过 `CHATBOT_STALE_RUN_SECONDS` 的 pending/streaming run 标 failed，不自动重调 LLM。
- [ ] 在真实 PostgreSQL 并发测试中同时发 10 个请求，断言一次成功/其余稳定冲突且 sequence 唯一。

**单元测试：** lock owner、renew/lost、idempotency mapping、rate limit、stale threshold。

**集成测试：** 多线程/多 session PostgreSQL、Redis 重启、跨用户 IDOR、Chroma where 捕获。

**验收条件：** Redis 失效仍不破坏一致性；跨用户矩阵 100% 拒绝；无 sequence 竞争。

**风险：** SQLite 测试无法证明 PostgreSQL 锁行为；分布式锁续租异常。

**回滚方式：** 关闭 Redis optimization，保留数据库串行化；不能回滚 owner filters/唯一约束。

**建议 Commit Message：** `security(chatbot-task19): harden isolation and concurrency`

### Task CB-020（Phase 17）：日志、指标与错误治理

**依赖：** CB-001、CB-015、CB-019。

**目标：** 建立完整 Chat 追踪、脱敏结构化事件和可操作的故障指标。

**涉及文件：**

- 新增：`backend/app/chatbot/observability.py`、`backend/app/chatbot/errors.py`
- 修改：`backend/app/core/logging.py`、`backend/app/main.py`、Chatbot services/stream handlers
- 新增：`backend/tests/chatbot/test_observability.py`、`test_error_codes.py`、`test_log_privacy.py`

**数据库变化：** 完整写入 `chatbot_llm_runs` 的 latency、first_token、usage、finish/error；不保存 Prompt。

**接口变化：** 错误码稳定为 03 第 13 章；SSE/JSON 使用同一 request_id。

**实现步骤：**

- [ ] 写每种错误映射、字段存在性、禁止字段和正文隐私扫描测试。
- [ ] 统一事件字段 request/user/conversation/message/run/provider/model/latency/usage/hits/status/error_code。
- [ ] 只记录 content length/hash（如确需关联）而不记录 content；user_id 可用稳定 hash 供非特权指标聚合。
- [ ] 记录 request、first token、complete/fail/cancel、Redis degrade、semantic degrade、summary/memory/cleanup backlog 事件。
- [ ] 当前无 metrics SDK 时用结构化日志 + SQL dashboard 查询，不新增监控平台依赖。

**单元测试：** error→HTTP/SSE、sanitizer、metric field、无 Prompt/API key/JWT/URL。

**集成测试：** 完整成功/超时/断线/Redis/Chroma 降级的关联 ID 一致。

**验收条件：** 任一失败可按 request_id 关联 run，日志隐私扫描无敏感值。

**风险：** 高基数字段和日志量；错误 details 泄露上游正文。

**回滚方式：** 降低事件采样但保留错误/LLM run；不得关闭脱敏。

**建议 Commit Message：** `feat(chatbot-task20): add chatbot observability and error governance`

### Task CB-021（Phase 18）：旧 Portfolio Chat 切换与清理

**依赖：** CB-017、CB-018、CB-020。

**目标：** 原子切换新前端/API，明确弃用旧无状态接口并删除重复逻辑。

**涉及文件：**

- 修改：`frontend/app/chat-bot/page.tsx`、`frontend/components/site-nav.tsx`、`backend/app/api/router.py`
- 删除：`frontend/features/chat-bot/chat-bot-panel.tsx`
- 删除（兼容期结束时）：`backend/app/api/v1/chat.py`、`backend/app/services/portfolio_chat.py`、`backend/app/schemas/chat.py`
- 修改/替换：`backend/tests/test_portfolio_chat.py`
- 新增：`backend/tests/chatbot/test_legacy_chat_compatibility.py`

**数据库变化：** 无历史数据迁移；审计确认旧 Chat 只有进程内 session，禁止映射到默认用户。

**接口变化：** 新前端只使用 `/api/v1/chatbot`；旧 `/api/v1/chat/chat` 在一个发布周期内由薄适配层调用新 service 或按批准直接 410。

**实现步骤：**

- [ ] 先写测试证明新旧之间无双写、旧接口有 Deprecation/Sunset/Link 且仍要求 JWT。
- [ ] 用 feature flag 切新 `ChatbotShell`，验证登录、刷新、Sidebar、流式闭环。
- [ ] 兼容层不得使用 session_id/in-memory memory，不得再次调用 LLM；无法安全映射旧请求时返回 410。
- [ ] 统计一个发布周期调用量为零后删除旧 Router/Service/Schema/component/test。
- [ ] 更新 README 的真实路径、认证和能力边界；禁止长期保留两套业务逻辑。

**单元测试：** legacy header/status、feature flag、无旧 import。

**集成测试：** 新页面端到端；旧调用不会产生重复 messages/runs。

**验收条件：** `rg 'PortfolioChatMemory|PortfolioChatService|/api/v1/chat/chat'` 只在迁移文档/兼容期测试出现，最终清理后代码零命中。

**风险：** 未知外部调用方依赖旧 session_id 契约。

**回滚方式：** 应用层切回已验证的新 service 的兼容 UI/API；不能恢复易失内存作为事实源。

**建议 Commit Message：** `refactor(chatbot-task21): replace legacy portfolio chat`

### Task CB-022（Phase 19）：集成测试、迁移演练与验收

**依赖：** CB-021 以及所有前置 Task。

**目标：** 用完整证据验证生产级要求、回归既有模块，并形成可执行发布/回滚清单。

**涉及文件：**

- 新增：`backend/tests/chatbot/test_chatbot_end_to_end.py`、`test_failure_matrix.py`、`test_data_cleanup.py`
- 新增：`frontend/features/chatbot/__tests__/chatbot-workspace.test.tsx`
- 修改：`README.md`、`docs/chatbot/04-implementation-plan.md`（追加发布/回滚演练结果）
- 约束：当前仓库没有 CI 配置文件，本 Task 不凭空绑定某个 CI 平台

**数据库变化：** 在 staging 演练 0005→head、备份、验证计数和应用回滚；不执行生产 migration。

**接口变化：** 冻结 V1 OpenAPI/SSE fixture，任何不兼容差异退回对应 Task 修正。

**实现步骤：**

- [ ] 建立验收矩阵：Conversation CRUD、分页、send/SSE、stop/retry/regenerate、Redis miss、summary、long/semantic memory、跨用户、timeout/断流、幂等、cleanup。
- [ ] 后端全量：`$env:PYTHONPATH='backend'; .\.venv\Scripts\python -m pytest backend/tests -q`。
- [ ] 前端全量：`Set-Location frontend; npm test -- --run; npm run lint; npm run build`。
- [ ] staging 清 Redis、重建 Chroma，核对 PostgreSQL count/checksum；删除 Conversation 验证 Redis/Chroma 清理补偿。
- [ ] 演练 migration backup/upgrade/application rollback/forward-fix；验证 Knowledge、Browser、Office、Admin、Auth、RBAC 全回归。
- [ ] 安全扫描仓库与日志；压测同会话并发、不同会话并发、长历史分页和流首 token 指标。

**单元测试：** 本 Task 不重复单元逻辑，只补覆盖审计发现的缺口。

**集成测试：** 任务书 17.2/17.3 全部场景，使用 PostgreSQL、Redis、Chroma 与 fake LLM 的可复现实例。

**验收条件：** 四份设计文档全部需求可映射到测试或人工发布检查；全量测试/构建通过；跨用户与秘密扫描零失败；有可演练回滚。

**风险：** 测试环境与生产 Provider/代理行为不同；E2E flake 掩盖真实问题。

**回滚方式：** 发布前不推进；发布后关闭 Chatbot feature/router，保留 PostgreSQL 数据，按 forward-fix 修复，必要时切回兼容 UI。

**建议 Commit Message：** `test(chatbot-task22): add production acceptance coverage`

## 3. 配置清单

以下变量在对应 Task 加入 `Settings` 与 `.env.example`，值均可按环境覆盖：

```text
CHATBOT_ENABLED=false
CHATBOT_ENV=development
CHATBOT_REDIS_SCHEMA_VERSION=1
CHATBOT_DEFAULT_MODEL=deepseek-chat
CHATBOT_ALLOWED_MODELS=deepseek-chat
CHATBOT_LLM_TIMEOUT_SECONDS=60
CHATBOT_LLM_MAX_ATTEMPTS=2
CHATBOT_MESSAGE_MAX_CHARS=4000
CHATBOT_CONVERSATION_PAGE_SIZE=20
CHATBOT_MESSAGE_PAGE_SIZE=50
CHATBOT_RECENT_MESSAGE_LIMIT=20
CHATBOT_SHORT_MEMORY_TTL_SECONDS=604800
CHATBOT_CONTEXT_TOKEN_BUDGET=8000
CHATBOT_SUMMARY_MESSAGE_THRESHOLD=20
CHATBOT_SUMMARY_TOKEN_RATIO=0.60
CHATBOT_MEMORY_MIN_CONFIDENCE=0.75
CHATBOT_SEMANTIC_TOP_K=5
CHATBOT_SEMANTIC_CANDIDATE_MULTIPLIER=3
CHATBOT_SEMANTIC_SIMILARITY_THRESHOLD=0.72
CHATBOT_EMBEDDING_VERSION=v1
CHATBOT_SSE_KEEPALIVE_SECONDS=15
CHATBOT_STREAM_CHECKPOINT_SECONDS=1
CHATBOT_STREAM_CHECKPOINT_CHARS=512
CHATBOT_LOCK_TTL_SECONDS=90
CHATBOT_STALE_RUN_SECONDS=300
CHATBOT_DELETED_RETENTION_DAYS=30
CHATBOT_LONG_TERM_MEMORY_ENABLED=false
CHATBOT_SEMANTIC_MEMORY_ENABLED=false
```

生产环境初始只开启 durable Conversation/Message/SSE；长期/语义记忆分别灰度开启。配置解析必须有范围校验并在启动时 fail fast（秘密除外不得打印原值）。

## 4. 发布顺序与 Gate

1. **Gate A（CB-000–003）：** 秘密已轮换、migration 在 staging 成功；否则禁止继续。
2. **Gate B（CB-004–010）：** durable chat + SSE 通过 owner/idempotency/failure 测试；功能仍默认关闭。
3. **Gate C（CB-011–015）：** Redis/Chroma 清空与降级演练通过；先开 short memory，再灰度 long/semantic。
4. **Gate D（CB-016–020）：** 前端构建、安全矩阵、日志隐私和并发测试通过。
5. **Gate E（CB-021–022）：** 新前端切换；旧接口观测一个周期后删除；完成生产发布审批。

任何 Gate 失败都停止后续 Task，修复后重跑该 Gate 全部测试，不带已知失败发布。

## 5. 计划自检

- **需求覆盖：** 01 的 Conversation、Message、Memory、LLM、Context、前端、安全、可观测、迁移与未来扩展均映射到 CB-006–022。
- **API 一致性：** 路径、状态、SSE 事件、错误码、分页和幂等以 03 为契约；实施不得自行改名。
- **数据一致性：** 表名/状态/Redis key/Chroma metadata 与 02 一致；PostgreSQL 始终是事实源。
- **范围控制：** 不实现 Multi-Agent、WebSocket、消息队列、跨用户管理员读取或多模态。
- **占位语检查：** 实施前不得存在未决标记、空步骤或延后处理的模糊描述；任何新架构决策必须先回写并评审四份文档。
- **提交纪律：** 每个 CB Task 一个 commit；测试未通过不得提交，也不得把后续 Task 混入当前 commit。

## 6. 推荐起点

从 **CB-000 安全配置与秘密轮换基线** 开始。当前 `.env.example` 中存在疑似真实秘密，且日志可能记录完整 Redis URL；在该风险消除前，不应继续建设会持久化用户聊天内容的生产模块。
