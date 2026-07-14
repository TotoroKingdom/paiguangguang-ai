# Chatbot 重构缺陷修复设计

> 日期：2026-07-14  
> 状态：已按 2026-07-14 代码审查结论确认，供后续实施计划使用  
> 范围：缺陷 1–10；不包含新的 Agent、RAG 或跨用户管理能力

## 1. 目标

修复重构后 Chatbot 的接口不可达、跨请求/跨会话流污染、流式完成链路缺少长期记忆、故障恢复未启动、删除不完整、Redis 运行期故障不可降级、前后端状态契约冲突、流式写库过密，以及自动标题、记忆 UI、功能开关、退出清理和滚动体验未完成的问题。

完成后必须满足：

- 前端所有 Chatbot 请求使用 `/api/v1/chatbot` 契约。
- 每条 SSE 事件只影响其 `conversation_id + request_id` 对应的当前流。
- 切换会话仅断开浏览器 reader，不隐式调用 stop；服务器继续生成并持久化。
- 消息终态事务提交后立即允许发送 terminal SSE；摘要、长期记忆、自动标题和清理任务不阻塞回复。
- PostgreSQL 是消息、记忆和后台任务的唯一业务事实源；Redis 与 Chroma 可以失败、重试或重建。
- deleted 会话对普通列表、详情和恢复接口不可见；只允许 archived 恢复。
- Redis 初始化或运行期失败不得破坏 PostgreSQL 保证的聊天正确性。
- 修复必须由失败测试驱动，并分别通过前端、后端和构建回归。

## 2. 方案比较与选择

### 方案 A：分阶段修复并引入 PostgreSQL durable job（采用）

先修复前端请求和流隔离，再增加 PostgreSQL durable job/outbox，最后统一产品契约和补齐功能。它把需要“提交后执行”的长期记忆、摘要、自动标题、Redis/Chroma 清理放到同一可靠边界，能重试且不会延长 SSE 尾延迟。

代价是增加一张任务表、一个 repository 和生命周期 worker，但这些组件可以独立测试，且不会引入新的外部队列依赖。

### 方案 B：只做局部补丁

在流式服务中直接调用长期记忆、在删除接口中同步清理、在 lifespan 中分别启动多个内存 task。改动较少，但进程崩溃会丢任务，外部系统变慢会阻塞 SSE/删除接口，重复请求也更难去重，因此不采用。

### 方案 C：一次性迁移到独立消息队列

引入 Celery、RQ 或其他 broker 可以提供成熟的调度能力，但当前仓库没有此基础设施，会扩大部署、监控和运维范围，超出本轮 YAGNI 边界，因此不采用。

## 3. 修复分组与依赖

### 阶段 A：前端契约与流隔离（缺陷 1–3）

本阶段不依赖数据库迁移，可以优先交付：

1. 导出唯一的 `CHATBOT_API_BASE = "/api/v1/chatbot"`，所有 Conversation、Message、Stop 和 Memory API 由该常量生成。
2. `ChatStreamState` 增加 `conversationId`，序号只在当前 `request_id` 内去重。新的 `message.created` 必须重置 `lastSequence`，旧 request 或旧 conversation 事件直接忽略。
3. `useChatStream` 捕获请求开始时的会话 ID；会话或 token 变化时 abort 当前 reader。Abort 是本地 detach，不调用 stop，也不报告生成失败。

### 阶段 B：持久完成链路与基础设施可靠性（缺陷 4–7）

新增 `chatbot_jobs` 表，任务类型固定为：

- `completed_turn_memory`
- `refresh_conversation_context`
- `auto_title`
- `cleanup_conversation`
- `cleanup_memory`

每个任务包含 `kind`、唯一 `dedup_key`、JSON `payload`、`status`、`attempt_count`、`available_at`、锁时间和最后错误。任务状态为 `pending | running | retry | completed | failed`。同一业务动作使用稳定的 dedup key，数据库唯一约束保证重放不会重复入队。

消息完成数据流为：

```text
完成 assistant/message/run/conversation
  -> 同一事务插入 completed_turn_memory、refresh_context、auto_title job
  -> commit
  -> message.completed -> usage.updated -> stream.end
  -> 生命周期 worker 认领并执行任务
```

同步 `ChatService.complete()` 与流式 `_finalize_completed()` 必须调用同一个 enqueue helper。幂等重放只读取既有终态，不再次入队。

删除数据流为：

```text
事务内锁 conversation
  -> conversation = deleted / cleanup_status = pending
  -> 相关 memory = deleted / embedding_status = deleted
  -> 插入 cleanup_conversation job
  -> commit并向用户返回 deleted
  -> worker 删除 Redis 三类键和 Chroma memory IDs
  -> 全部成功后 conversation.cleanup_status = completed
  -> 失败则 job/status = retry
```

Memory API 删除使用相同原则：数据库软删除和 `cleanup_memory` 入队同事务完成；Chroma 清理失败不能返回 5xx，也不能错误报告 `cleanup_status=completed`。

worker 在应用 lifespan 中启动。启动顺序为数据库初始化、执行一次 stale-run recovery、恢复过期 running job、启动周期循环。关闭时设置停止事件并等待当前批次结束。多实例通过 `SELECT ... FOR UPDATE SKIP LOCKED` 认领任务；SQLite 测试允许退化为普通行锁语义。

stale run recovery 使用 compare-and-set 更新，只能把“扫描时仍旧是 pending/streaming 且 updated_at 仍小于 cutoff”的行改为 failed，避免心跳竞态。

Redis 只提供优化能力：

- Cancellation 在 Redis 失败时使用进程内标记；跨实例取消在 Redis 恢复前不保证即时传播，但数据库终态和 stale recovery 保证不会永久卡住。
- Concurrency 在 Redis 失败时退化为进程内 lease；Conversation 行锁和数据库 active-run 检查始终是最终正确性边界。
- Short-term memory Redis 失败时从 PostgreSQL 重建；release/delete 失败只记录 `chatbot.redis.degraded`，不得覆盖成功业务结果。

### 阶段 C：产品契约与流性能（缺陷 8–9）

前端删除 `ConversationStatus = "deleted"`、Trash 页签以及 deleted restore。删除成功后从所有缓存页移除会话；如果删除的是当前会话，同时清空选中状态和 URL。旧 sessionStorage snapshot 升级到版本 2，hydrate 时只保留 active/archived，避免旧 `deleted` 数据重新出现。

流式 checkpoint 使用双阈值：

- 距上次写库至少 1.0 秒；或
- 自上次写库新增至少 512 个 Unicode 字符。

首次非空 delta 必须立即把 pending 转成 streaming；usage、终态、取消和失败必须强制 flush。最终 DB commit 后先发送 terminal SSE，再由 durable job 刷新摘要和短期缓存。

### 阶段 D：产品完整性（缺陷 10）

- 自动标题：第一条成功 user/assistant turn 入队 `auto_title:{conversation_id}`；标题由第一条用户消息去空白、截断为 60 字符生成。更新语句必须包含 `title_source='default'`，所以手工标题在竞态中永远获胜。
- Memory UI：在 `/chat-bot` 工作区增加 Chat/Memories 视图切换；支持 active/candidate/superseded 筛选、游标加载、编辑 content/status 和删除。
- 功能开关：增加 `CHATBOT_ENABLED` 与 `NEXT_PUBLIC_CHATBOT_ENABLED`。后端关闭时 Chatbot router 统一返回 503；前端不展示导航且 `/chat-bot` 返回 404。默认值保持 true 兼容当前开发环境，生产环境文件显式控制。
- Logout：token/user 变空时 abort 当前 reader、清空内存 store，并删除上一个用户的 `paiguangguang.chatbot:{user_id}` sessionStorage；匿名状态不持久化 Chatbot snapshot。
- 自动滚动：仅当用户在底部阈值内时跟随 delta；向上滚动后保持锚点并显示 Back to bottom。
- 文档：更新 README 的开关、任务 worker、删除和故障降级行为。

## 4. 组件边界

### 前端

- `api/client.ts`：唯一 API base 与 Conversation/Control 请求。
- `api/stream.ts`：SSE 请求和解析，不保存 UI 状态。
- `utils/merge-stream-event.ts`：纯 reducer，执行 conversation/request/sequence 隔离。
- `hooks/use-chat-stream.ts`：reader 生命周期和本地 abort。
- `hooks/use-messages.ts`：当前会话消息状态，不接收旧会话事件。
- `api/memories.ts`、`hooks/use-memories.ts`、`components/memory-panel.tsx`：Memory UI 独立边界。
- `stores/chatbot-store.tsx`：只持久化当前已登录用户的 active/archived Conversation 缓存。

### 后端

- `models/job.py`：durable job ORM。
- `repositories/job_repository.py`：enqueue、claim、complete、retry、recover-stale。
- `services/completion_jobs.py`：在终态事务中生成稳定任务。
- `services/job_runner.py`：任务分派和退避，不包含 HTTP 逻辑。
- `services/cleanup_service.py`：Redis/Chroma 清理和 cleanup_status 更新。
- `services/recovery_service.py`：仅负责 stale LLM run compare-and-set。
- `services/runtime.py`：lifespan worker 的 start/stop/run-once。

Router 不直接调用 job repository；Service 管事务和状态机；外部 Redis/Chroma 操作不得发生在消息或删除主事务中。

## 5. 错误处理和重试

- durable job 默认最多 8 次，退避为 `min(300, 2 ** attempt_count)` 秒。
- 业务资源已经 deleted 时，cleanup job 仍可重放；Redis delete 和 Chroma delete 必须幂等。
- 超过最大次数的 job 标记 failed，保留 `last_error` 的异常类型和脱敏摘要，不保存消息正文、JWT、Redis URL 或 provider 密钥。
- 启动时把锁定时间超过 `CHATBOT_JOB_STALE_SECONDS` 的 running job 改为 retry。
- `stream.end` 只依赖 PostgreSQL 终态成功，不依赖 Redis、Chroma、摘要或标题。
- Redis 降级日志统一使用 `chatbot.redis.degraded`，字段包含 source、operation、异常类型和相关资源 ID，但不包含正文。

## 6. 测试策略

每一任务遵循 red-green-refactor：先提交最小失败测试，确认失败原因与缺陷一致，再写最小实现。

必须覆盖：

- API path 契约和 OpenAPI 路径。
- 两个连续 SSE 请求均从 sequence 1 开始。
- A 会话生成时切到 B，A 的迟到事件不进入 B，且未调用 stop。
- 同步和流式完成均只产生一组 durable jobs，replay 不重复。
- slow summary 不延迟 terminal SSE。
- stale recovery 与心跳 compare-and-set 竞态。
- 删除会话立即排除长期记忆；Redis/Chroma 失败进入 retry，重试后 completed。
- Redis 初始化故障、请求中断线、release 断线。
- 前端不再请求 deleted 列表，也不展示 Trash/Deleted restore。
- checkpoint 写库次数受双阈值限制，终态强制 flush。
- 手工标题与 auto title 竞态时手工标题获胜。
- logout 清除上一用户 storage，滚动离底后 delta 不拉回底部。

## 7. 发布与回滚

实施顺序固定为 A → B → C → D。每阶段必须独立通过测试并形成独立 commit；阶段 B 的 `0007` migration 先部署，再部署引用新表的应用代码。

回滚应用代码时保留 `chatbot_jobs` 表，不立即 downgrade，避免丢失待处理清理任务。关闭功能可使用前后端 feature flag；Redis/Chroma 故障时不回滚 PostgreSQL 已提交的消息或删除状态。

## 8. 非目标

- 不实现 deleted Conversation 回收站和恢复接口。
- 不保证 SSE token 断点续传。
- 不引入 Celery/RQ/Kafka。
- 不迁移所有现有 Chatbot 配置到新的配置子系统。
- 不增加跨用户 Memory 或 Conversation 管理能力。
