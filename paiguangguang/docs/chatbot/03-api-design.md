# Portfolio Chatbot API 设计

> 状态：待评审；版本：1.0；基础路径：`/api/v1/chatbot`。本文件定义后续实施契约，本阶段尚未新增接口。

## 1. 设计原则

- 所有 Chatbot API 必须使用现有 Bearer JWT，通过 `backend/app/services/auth.py:get_current_user_context` 获取用户；请求体和查询参数不接受 `user_id`。
- 资源查询始终同时过滤资源 ID 与当前用户 ID。资源不存在、已删除或属于他人统一返回 404，避免枚举。
- 普通 JSON 响应复用 `ApiResponse[T]` envelope；流式接口使用 SSE，流建立前错误返回 JSON envelope，流建立后错误作为 SSE event。
- Conversation 和 Message 使用稳定 cursor pagination；cursor 只表示位置，不承担授权。
- 消息发送使用客户端 UUID 幂等键；Redis 可做快速命中，PostgreSQL 唯一约束是最终保障。
- API V1 只允许同一 Conversation 一个生成中的 Assistant；并发发送返回 409。

## 2. 协议与通用约定

### 2.1 请求头

| Header | 必需 | 规则 |
|---|---:|---|
| `Authorization: Bearer <JWT>` | 是 | 所有 `/api/v1/chatbot/**` 接口必需 |
| `Content-Type: application/json` | 写接口是 | UTF-8 JSON |
| `X-Request-ID` | 否 | 合法 UUID/ULID 时沿用，否则服务端生成；响应总是返回 |
| `Idempotency-Key` | 发送/重试/重新生成是 | UUID，必须与 body `client_request_id` 相同 |
| `Accept: text/event-stream` | 流式发送是 | POST fetch 接收 SSE |

### 2.2 JSON envelope

成功：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "request_id": "0198a6f0-5c62-7ba1-a682-22f731c33545"
}
```

失败：

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "CHATBOT_CONVERSATION_NOT_FOUND",
    "message": "Conversation not found",
    "details": null
  },
  "request_id": "0198a6f0-5c62-7ba1-a682-22f731c33545"
}
```

后续应扩展 `backend/app/schemas/common.py`：`ApiResponse` 增加 `request_id`；`ErrorDetail` 增加可选 `details`。不得把上游响应正文、Prompt、JWT 或内部堆栈放进 `message/details`。

### 2.3 时间、ID 与空值

- 资源 ID、`client_request_id`、`request_id` 为 UUID 字符串。
- 时间使用 UTC RFC 3339，例如 `2026-07-13T02:15:30.123Z`。
- 可选值用 JSON `null`，不使用空字符串表示未知；Chroma metadata 的空串规范仅限存储适配层。
- 枚举值小写、稳定；新增枚举值属于向后兼容扩展，客户端必须容忍未知值并降级显示。

### 2.4 Cursor Pagination

列表统一返回：

```json
{
  "items": [],
  "next_cursor": "eyJ2IjoxLC4uLn0",
  "has_more": true
}
```

- `limit` 默认 20，范围 1–100。
- cursor 为 versioned、URL-safe base64 编码位置；客户端不得解析或修改。
- Conversation cursor 编码 `(last_message_at, id, status_filter, v=1)`，排序固定 `last_message_at desc, id desc`。
- Message cursor 编码 `(sequence_number, id, direction, v=1)`；默认返回最新一页并按 `sequence_number asc` 展示，传 `before` 向历史方向加载。
- cursor 与当前 filter 不匹配返回 `CHATBOT_INVALID_CURSOR`（400）；授权仍由 user filter 保证。

## 3. 路由总览

| 方法 | 路径 | 用途 | 响应 |
|---|---|---|---|
| POST | `/conversations` | 创建 Conversation | JSON 201 |
| GET | `/conversations` | Conversation 列表 | JSON 200 |
| GET | `/conversations/{conversation_id}` | Conversation 详情 | JSON 200 |
| PATCH | `/conversations/{conversation_id}` | 修改标题/模型 | JSON 200 |
| DELETE | `/conversations/{conversation_id}` | 软删除 | JSON 200 |
| POST | `/conversations/{conversation_id}/archive` | 归档 | JSON 200 |
| POST | `/conversations/{conversation_id}/restore` | 恢复归档 | JSON 200 |
| GET | `/conversations/{conversation_id}/messages` | 历史消息 | JSON 200 |
| POST | `/conversations/{conversation_id}/messages` | 发送并流式生成 | SSE 200 |
| POST | `/conversations/{conversation_id}/messages/{message_id}/retry` | 重试失败轮次 | SSE 200 |
| POST | `/conversations/{conversation_id}/messages/{message_id}/regenerate` | 重新生成答案 | SSE 200 |
| POST | `/conversations/{conversation_id}/stop` | 停止当前生成 | JSON 202/200 |
| GET | `/memories` | 当前用户长期记忆列表 | JSON 200 |
| GET | `/memories/{memory_id}` | 长期记忆详情 | JSON 200 |
| PATCH | `/memories/{memory_id}` | 修改/激活记忆 | JSON 200 |
| DELETE | `/memories/{memory_id}` | 删除记忆 | JSON 200 |

以下章节中的路径省略 `/api/v1/chatbot` 前缀。

## 4. Pydantic Schema

### 4.1 通用类型

```python
ConversationStatus = Literal["active", "archived", "deleted"]
MessageRole = Literal["user", "assistant", "system", "tool"]
MessageStatus = Literal["pending", "streaming", "completed", "failed", "cancelled"]
MemoryStatus = Literal["candidate", "active", "superseded", "deleted", "failed"]
LLMRunStatus = Literal["pending", "streaming", "completed", "failed", "cancelled"]
```

### 4.2 Conversation

```python
class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    model: str | None = Field(default=None, min_length=1, max_length=100)

class ConversationUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    model: str | None = Field(default=None, min_length=1, max_length=100)

class ConversationData(BaseModel):
    id: UUID
    title: str
    title_source: Literal["default", "auto", "manual"]
    status: ConversationStatus
    model: str
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None

class ConversationPageData(BaseModel):
    items: list[ConversationData]
    next_cursor: str | None
    has_more: bool

class DeleteResultData(BaseModel):
    id: UUID
    status: Literal["deleted"]
    cleanup_status: Literal["pending", "completed", "retry"]
```

`ConversationUpdateRequest` 至少一个字段非 null；客户端不能修改 status、owner、prompt version 或时间戳。

### 4.3 Message

```python
class MessageData(BaseModel):
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    content_json: dict[str, Any] | None
    sequence_number: int
    status: MessageStatus
    model: str | None
    parent_message_id: UUID | None
    client_request_id: UUID | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime

class MessagePageData(BaseModel):
    items: list[MessageData]
    next_cursor: str | None
    has_more: bool

class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    client_request_id: UUID
    model: str | None = Field(default=None, min_length=1, max_length=100)

class GenerationRequest(BaseModel):
    client_request_id: UUID

class StopGenerationRequest(BaseModel):
    assistant_message_id: UUID | None = None

class StopGenerationData(BaseModel):
    conversation_id: UUID
    assistant_message_id: UUID
    status: Literal["cancellation_requested", "cancelled", "already_terminal"]
```

Message 的 `user_id` 不返回给普通客户端，防止形成客户端所有权逻辑；owner 永远由认证上下文决定。

### 4.4 Memory

```python
class MemoryData(BaseModel):
    id: UUID
    conversation_id: UUID | None
    memory_type: Literal["preference", "goal", "project_context", "explicit", "fact", "work_context"]
    content: str
    importance: float
    confidence: float
    source_message_ids: list[UUID]
    status: MemoryStatus
    last_accessed_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

class MemoryPageData(BaseModel):
    items: list[MemoryData]
    next_cursor: str | None
    has_more: bool

class MemoryUpdateRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    status: Literal["candidate", "active"] | None = None
    expires_at: datetime | None = None
```

编辑 content 会重新规范化、更新版本并令 `embedding_status=pending`；敏感内容过滤仍适用。普通用户不能设置 confidence、importance、source IDs 或 owner。

## 5. Conversation API

### 5.1 创建

`POST /conversations`

```http
POST /api/v1/chatbot/conversations HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{"title":"生产级 Chatbot 设计"}
```

201 返回 `ApiResponse[ConversationData]`。未传标题时使用“新对话”与 `title_source=default`。模型必须来自服务端 allowlist；未知模型返回 `CHATBOT_MODEL_NOT_ALLOWED`（422）。

### 5.2 列表

`GET /conversations?status=active&limit=20&cursor=<opaque>`

- `status` 默认 `active`，可为 `active|archived`；普通列表不允许查询 deleted。
- 排序固定为最后活动时间倒序，避免任意 sort 扩大索引面。
- 空列表返回 `items=[]`，不是 404。

### 5.3 详情

`GET /conversations/{conversation_id}` 返回 owner 的非 deleted Conversation。若正在生成，可附加只读字段：

```json
"active_generation": {
  "assistant_message_id": "...",
  "status": "streaming",
  "started_at": "2026-07-13T02:15:30Z"
}
```

该字段帮助刷新恢复，不代表可恢复丢失的 SSE delta；最终以 Message GET 为准。

### 5.4 修改

`PATCH /conversations/{conversation_id}`。手工修改标题后 `title_source=manual`，自动标题任务不得覆盖。archived Conversation 可改标题/模型但不能发送消息；deleted 不可修改。

### 5.5 归档与恢复

- `POST /conversations/{id}/archive`：active → archived；已有 active generation 时返回 409 busy。
- `POST /conversations/{id}/restore`：archived → active。
- 对目标状态重复调用返回当前资源并保持 200，操作幂等。

### 5.6 删除

`DELETE /conversations/{id}` 软删除并返回 `ApiResponse[DeleteResultData]`。删除重复调用仍统一 404，避免 deleted 资源枚举。若存在生成，先请求取消并在同一数据库事务将资源标 deleted；Redis/Chroma 在提交后清理，失败不改变用户可见删除结果。

## 6. Message 历史 API

`GET /conversations/{conversation_id}/messages?limit=50&before=<cursor>`

- `limit` 默认 50、最大 100。
- 无 `before` 时选择最新 N 条，但响应 `items` 始终按 sequence asc。
- `next_cursor` 指向更老一页；到达第一条时为 null。
- 默认返回 system/tool 消息的安全展示版本；内部 system prompt 不作为历史 Message 暴露。
- failed/cancelled Assistant 返回已 checkpoint 的部分 content、error_code，不返回内部 error_message。

刷新恢复：先 GET Conversation，若存在 active generation，再 GET 最新消息。若状态仍 pending/streaming，前端显示“生成状态恢复中”并轮询详情；服务端 stale recovery 最终会把陈旧状态改为 failed。

## 7. 发送消息与 Streaming API

### 7.1 请求

`POST /conversations/{conversation_id}/messages`

```http
POST /api/v1/chatbot/conversations/70ec.../messages HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json
Accept: text/event-stream
Idempotency-Key: 33d02ac4-4727-46d7-99b1-24f59e020ad5

{
  "content": "请总结当前架构选择",
  "client_request_id": "33d02ac4-4727-46d7-99b1-24f59e020ad5"
}
```

服务端在发出 SSE headers 前完成：认证、owner/status 检查、幂等检查、Conversation 行锁、sequence 分配、用户消息/Assistant pending/LLM run 落库。失败时返回普通 JSON。

### 7.2 幂等重放

- 首次请求处理中重复：若能接入原进程流则不承诺共享连接；返回 409 `CHATBOT_REQUEST_IN_PROGRESS`，details 含已创建的 message IDs。
- 原请求已终止：返回 200 SSE 快照，依次发送 `message.created`（replayed=true）、对应终态事件、usage（如有）、`stream.end`；不调用 LLM。
- Header 与 body ID 不同返回 400；同 ID 但 content hash 不同返回 409 `CHATBOT_IDEMPOTENCY_CONFLICT`。

### 7.3 SSE 线格式

```text
id: 4
event: message.delta
data: {"schema_version":"1","request_id":"...","conversation_id":"...","assistant_message_id":"...","sequence":4,"delta":"架构","content_length":12,"created_at":"..."}

```

- UTF-8，事件块用空行分隔；`data` 必须是单行 JSON。
- `id` 是当前 HTTP 流内单调递增整数，不是数据库 sequence。
- 每 15 秒可发送 `: keepalive` comment；代理不得缓冲。
- 所有 data 都有 `schema_version="1"`、`request_id`、`conversation_id`、`assistant_message_id`、`sequence`、`created_at`。

### 7.4 SSE 事件 Schema

#### `message.created`

发送一次，建立权威 ID；幂等回放时 `replayed=true`。

```json
{
  "schema_version": "1",
  "request_id": "...",
  "conversation_id": "...",
  "assistant_message_id": "...",
  "sequence": 1,
  "created_at": "...",
  "replayed": false,
  "user_message": {"id":"...","sequence_number":1,"status":"completed","content":"..."},
  "assistant_message": {"id":"...","sequence_number":2,"status":"pending","content":""}
}
```

#### `message.delta`

零到多次。`delta` 为本事件新增文本；`content_length` 是应用后 Assistant 累计 Unicode code point 数，用于检测遗漏/重复。

```json
{"schema_version":"1","request_id":"...","conversation_id":"...","assistant_message_id":"...","sequence":2,"created_at":"...","delta":"PostgreSQL","content_length":10}
```

#### `message.completed`

```json
{
  "schema_version":"1",
  "request_id":"...",
  "conversation_id":"...",
  "assistant_message_id":"...",
  "sequence":15,
  "created_at":"...",
  "message":{"id":"...","status":"completed","content":"完整最终正文","sequence_number":2,"model":"deepseek-chat","updated_at":"..."},
  "finish_reason":"stop"
}
```

最终正文用于客户端校准 delta 合并结果。

#### `message.failed`

```json
{
  "schema_version":"1",
  "request_id":"...",
  "conversation_id":"...",
  "assistant_message_id":"...",
  "sequence":8,
  "created_at":"...",
  "error":{"code":"CHATBOT_LLM_TIMEOUT","message":"Generation timed out","retryable":true},
  "partial":true,
  "content":"已持久化的部分正文"
}
```

#### `message.cancelled`

```json
{"schema_version":"1","request_id":"...","conversation_id":"...","assistant_message_id":"...","sequence":9,"created_at":"...","reason":"user_requested","content":"已持久化的部分正文"}
```

#### `usage.updated`

最多一次，通常在 completed 之后；Provider 不提供 usage 时三个字段为 null，数据库记录 0 并标来源 unknown。

```json
{"schema_version":"1","request_id":"...","conversation_id":"...","assistant_message_id":"...","sequence":16,"created_at":"...","prompt_tokens":812,"completion_tokens":143,"total_tokens":955,"source":"provider"}
```

#### `stream.end`

每个已建立的 SSE 流必须最后尝试发送一次。

```json
{"schema_version":"1","request_id":"...","conversation_id":"...","assistant_message_id":"...","sequence":17,"created_at":"...","final_status":"completed"}
```

合法顺序：

```text
message.created
→ message.delta *
→ exactly one of message.completed | message.failed | message.cancelled
→ usage.updated ?
→ stream.end
```

### 7.5 断线处理

- 客户端 `fetch` Abort/网络中断只关闭当前响应；默认不自动取消上游生成。
- 客户端不得仅凭断线重用新 `client_request_id` 自动重发，否则可能重复付费；应使用原 ID 查询/重放。
- V1 不支持 `Last-Event-ID` 逐 token 续传，因为不永久保存全部 SSE 事件。刷新后通过 Message API 恢复 checkpoint/终态。
- 后端完成后即使 socket 写失败，也必须持久化终态并记录 `CHATBOT_STREAM_CLIENT_DISCONNECTED` 指标，而不是把 completed 改成 failed。

## 8. 停止生成

`POST /conversations/{conversation_id}/stop`

```json
{"assistant_message_id":"c5f9..."}
```

- owner 校验后设置共享 cancellation token；多实例通过 Redis cancellation key + 数据库状态轮询协作。
- 首次接受取消返回 202 `cancellation_requested`；已经 cancelled 返回 200 `cancelled`；已经 completed/failed 返回 200 `already_terminal`。
- 省略 ID 时停止该 Conversation 唯一 active run；没有 active run 返回 `CHATBOT_NO_ACTIVE_GENERATION`（409）。
- stop 幂等，但不会删除部分正文。原 SSE 收到 `message.cancelled` 和 `stream.end`。

## 9. 重试与重新生成

### 9.1 Retry

`POST /conversations/{conversation_id}/messages/{message_id}/retry`

- `message_id` 必须是 failed/cancelled Assistant；服务端找到其 parent user message。
- 创建新的 Assistant message 与 LLM run，旧消息不修改；新 Assistant 的 `parent_message_id` 指向同一 user message。
- request body 只有新的 `client_request_id`；响应 SSE 与普通发送一致。
- completed Assistant 不允许 retry，返回 `CHATBOT_MESSAGE_NOT_RETRYABLE`（409）。

### 9.2 Regenerate

`POST /conversations/{conversation_id}/messages/{message_id}/regenerate`

- `message_id` 可为 completed/failed/cancelled Assistant；根据其 parent user message 重新生成。
- 同样创建新 Assistant，不覆盖历史；前端将多个答案显示为 variants。
- parent user message 之后若已有新的 user turn，V1 返回 `CHATBOT_REGENERATE_NOT_LATEST_TURN`（409），避免隐式创建分支。未来分支对话另行版本化。

## 10. Memory API

### 10.1 列表

`GET /memories?status=active&memory_type=preference&conversation_id=<id>&limit=20&cursor=<opaque>`

- 默认 status=active；可查询 candidate、active、superseded，不允许查询 deleted。
- 排序 `(updated_at desc,id desc)`；conversation filter 仍强制 owner。
- 不返回 normalized_content、normalized_hash、embedding_id 或内部失败信息。

### 10.2 详情

`GET /memories/{memory_id}` 同时过滤 ID 与 current user。`source_message_ids` 只返回仍属于当前用户的 ID；源消息已删除时保留审计关联但客户端不提供正文跳转。

### 10.3 修改

`PATCH /memories/{memory_id}`。允许修改 content、candidate/active 状态和 expires_at；编辑触发去重与重新 embedding。与现有 active memory 冲突时返回 409 `CHATBOT_MEMORY_CONFLICT`，details 只包含冲突 memory_id。

### 10.4 删除

`DELETE /memories/{memory_id}` 软删 PostgreSQL，提交后删除 Chroma vector；返回 `DeleteResultData`。Chroma 清理失败返回业务删除成功和 `cleanup_status=retry`，不以 5xx 误导用户重试删除。

## 11. 认证、授权与权限矩阵

| API | 匿名 | 登录用户自己的资源 | 登录用户他人资源 | system_admin 他人资源 |
|---|---:|---:|---:|---:|
| Conversation CRUD/archive/restore | 401 | 允许 | 404 | 404 |
| Message list/send/retry/regenerate/stop | 401 | 允许 | 404 | 404 |
| Memory list/detail/update/delete | 401 | 允许 | 404 | 404 |

V1 不复用 `system_admin` 作为聊天正文审计权。未来管理员接口必须使用独立路径、权限、审计日志和隐私审批，不得在普通 repository 中加 `bypass_owner=True`。

## 12. 幂等与并发规则

| 操作 | 幂等键/策略 |
|---|---|
| create conversation | 非幂等；前端一次点击一次请求 |
| patch/archive/restore | 目标状态幂等 |
| delete | 首次成功；后续统一 404 |
| send/retry/regenerate | Header + body UUID；DB 唯一约束 + content hash |
| stop | assistant ID 幂等 |

Message send 事务锁 Conversation，验证 `next_sequence` 与 active run。相同幂等键的竞态由唯一约束捕获并读取胜者；不同幂等键同会话并发时一个成功、其他 409 busy。不得依赖前端按钮禁用或 Redis 锁作为唯一保障。

## 13. 错误码

| HTTP | Code | 场景 | 可重试 |
|---:|---|---|---:|
| 400 | `CHATBOT_INVALID_CURSOR` | cursor 非法或 filter 不匹配 | 否 |
| 400 | `CHATBOT_IDEMPOTENCY_KEY_MISMATCH` | Header/body ID 不同 | 否 |
| 401 | `AUTHENTICATION_ERROR` | 缺失/无效/过期 JWT | 登录后 |
| 404 | `CHATBOT_CONVERSATION_NOT_FOUND` | 不存在、deleted 或非 owner | 否 |
| 404 | `CHATBOT_MESSAGE_NOT_FOUND` | 不存在或非 owner | 否 |
| 404 | `CHATBOT_MEMORY_NOT_FOUND` | 不存在或非 owner | 否 |
| 409 | `CHATBOT_CONVERSATION_BUSY` | 同会话已有生成 | 稍后 |
| 409 | `CHATBOT_REQUEST_IN_PROGRESS` | 同幂等请求仍运行 | 查询状态 |
| 409 | `CHATBOT_IDEMPOTENCY_CONFLICT` | 相同 key、不同 payload | 换 key/修请求 |
| 409 | `CHATBOT_NO_ACTIVE_GENERATION` | stop 时无 active run | 否 |
| 409 | `CHATBOT_MESSAGE_NOT_RETRYABLE` | 消息状态不允许重试 | 否 |
| 409 | `CHATBOT_REGENERATE_NOT_LATEST_TURN` | V1 不支持分支重生 | 否 |
| 409 | `CHATBOT_MEMORY_CONFLICT` | active memory 冲突 | 用户处理 |
| 422 | `VALIDATION_ERROR` | Schema 校验失败 | 修请求 |
| 422 | `CHATBOT_MODEL_NOT_ALLOWED` | 模型不在 allowlist | 修请求 |
| 429 | `CHATBOT_RATE_LIMITED` | 用户/Conversation 限流 | 是 |
| 502 | `CHATBOT_LLM_PROVIDER_ERROR` | 上游协议/服务失败 | 视 retryable |
| 504 | `CHATBOT_LLM_TIMEOUT` | LLM 超时 | 是 |
| 500 | `CHATBOT_STREAM_ERROR` | 内部流处理失败 | 是 |
| 500 | `CHATBOT_INTERNAL_ERROR` | 未分类内部错误 | 是 |

JSON 错误可有受控 `details`；SSE error 只使用 `message.failed.error`。错误 message 面向用户稳定，内部诊断通过 request_id 查脱敏日志。

## 14. 前端调用流程

### 14.1 页面加载

1. `AuthProvider` 完成认证后，带 token GET Conversation list。
2. URL 有 conversation ID 时 GET 详情；404 时清除 URL 并显示统一提示。
3. GET 最新 Message page；如有 active generation，显示恢复状态并定时刷新。
4. 切换会话时 abort 旧列表请求和旧 SSE reader，但不调用 stop；stop 只来自用户明确操作。

### 14.2 发送与消费 SSE

1. 在用户点击时生成一次 UUID，保存到当前内存 mutation state；网络重试复用同一个 ID。
2. 使用 `fetch` 设置 JWT、Idempotency-Key、Accept 和 JSON body。
3. 响应非 2xx 或非 `text/event-stream` 时按 JSON envelope 处理。
4. 用 `ReadableStream.getReader()` + `TextDecoder` 按空行解析事件；按 SSE sequence 去重。
5. `message.created` 用服务端 ID 替换 optimistic ID；delta 追加；completed 用最终 content 校准。
6. 终态后刷新 Conversation 列表的 last_message_at/title，清理 AbortController。
7. 网络断线保留已收 delta，标“连接中断”，用 Message GET 恢复；不得自动新建请求。

### 14.3 logout

`AuthProvider.logout()` 除清 JWT 外，Chatbot feature 必须 abort stream、清 Conversation/Message 内存 cache、cursor、draft 映射和 request IDs。不得在 localStorage 长期存消息正文。

## 15. 版本兼容策略

- URL major 版本保持 `/api/v1`；SSE data 另带 `schema_version="1"`。
- 可选字段和新 SSE event 为向后兼容；删除/改名/含义改变需要 `/api/v2` 或双读迁移。
- 客户端忽略未知 SSE event，但遇到未知 schema major 必须停止合并并刷新 Message API。
- 旧 `POST /api/v1/chat/chat` 最多保留一个发布周期；兼容层不得保留内存 session 或双份 LLM 逻辑。响应增加 `Deprecation: true`、`Sunset` 与 `Link`；迁移期结束后返回 410。
- 当前前端必须原子切换到新 API，不进行新旧双写。

## 16. API 测试矩阵

- 认证：每类接口缺 token、过期 token、有效 token。
- 隔离：Conversation/Message/Memory 用另一用户 ID 读取、修改、删除、stop、regenerate 均 404。
- 分页：同 timestamp、并发插入、cursor filter mismatch、边界 limit、无重复/遗漏。
- 幂等：顺序重放、并发重放、相同 key 不同 content、Redis 清空后 DB 命中。
- 并发：同会话不同 key、不同会话并发、Redis 锁失效但 DB 仍正确。
- SSE：完整序列、零 delta、usage 缺失、timeout、部分失败、取消、客户端断线、幂等终态回放。
- 恢复：pending/streaming stale、刷新 GET、Redis miss、Chroma 不可用。
- Memory：敏感拒绝、用户编辑触发重嵌入、冲突、delete cleanup retry、强制 Chroma where user_id。
- 兼容：旧 endpoint 只经过新 service，Sunset 后 410；不存在双写。

## 17. 待确认事项与默认值

| 事项 | 默认值 |
|---|---|
| Conversation page size | 20，最大 100 |
| Message page size | 50，最大 100 |
| 消息正文长度 | 1–4000 字符 |
| SSE keepalive | 15 秒 |
| 断线生成策略 | 服务端继续，客户端 GET 恢复 |
| 旧接口兼容期 | 一个发布周期 |
| Memory API | V1 对本人开放 |

这些值应进入 Schema 或 `Settings`，不得散落硬编码在业务 Service。

