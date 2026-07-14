# Chatbot 前端重构设计与实施计划

> 日期：2026-07-14
> 状态：设计已确认，等待实施
> 范围：仅限前端分析、设计与后续前端重构；本文档不修改后端 API、路由或业务语义

**目标：** 在保留现有 Chatbot 业务能力、SSE 契约和路由的前提下，将 `/chat-bot` 重构为简洁、克制、留白充足的全高聊天工作区，并补齐现有 FastAPI Chatbot 接口在前端的调用入口。

**架构：** 采用渐进式边界重构。保留 API 客户端、Conversation store、业务 hooks、SSE reader 和纯 reducer，先修复异步竞态及接口缺口，再替换页面骨架和展示组件。数据请求只发生在控制器 hook/组件中，拆出的展示组件只通过 props 接收数据和操作，避免组件拆分后出现重复请求。

**技术栈：** Next.js 14 App Router、React 18、TypeScript、Tailwind CSS、Framer Motion、react-markdown、remark-gfm、Vitest、Testing Library。

## 全局约束

- 不修改任何 FastAPI 路由、请求体、响应体、SSE 事件或后端业务逻辑。
- 不改变 `/chat-bot` 路由，也不创建替代路由。
- 不安装新依赖。
- 不复制 DeepSeek 的 Logo、品牌名称、专属图标或文案。
- 仅借鉴双栏布局、固定阅读宽度、正文式 AI 回复和底部 Composer 等通用交互原则。
- Chatbot 不需要文件上传；不显示上传按钮或占位入口。
- 当前模型仅在 Composer 内只读展示；不实现模型切换、深度思考、联网或其他模式。
- 不新增 citations、RAG 来源、附件或其他后端不存在的业务数据。
- 现有认证、feature flag、Conversation URL、用户级 sessionStorage、SSE 幂等键和生成控制行为必须保留。
- 本轮设计不修改源代码；后续实施必须按阶段先补测试，再修改实现。

---

## 一、现状分析

### 1. 页面入口、路由与外层布局

Chatbot 的页面入口是 `frontend/app/chat-bot/page.tsx`，公开 URL 为 `/chat-bot`。该 Server Component 先读取 `NEXT_PUBLIC_CHATBOT_ENABLED`：

- 开启时渲染 `ChatbotShell`。
- 关闭时调用 Next.js `notFound()`，同时 `frontend/components/site-nav.tsx` 隐藏 Chatbot 导航入口。
- 页面当前额外包裹 `max-w-7xl` 容器。

全站根布局位于 `frontend/app/layout.tsx`，层级为：

```text
RootLayout
└─ AuthProvider
   └─ Suspense
      └─ RouteGuard
         └─ AppShell
            └─ Page
```

`frontend/components/app-shell.tsx` 对所有非首页页面统一显示 `SiteNav`，并为 `main` 添加页面 padding。Chatbot 因此不是独立全高工作区，而是普通内容页中的一个模块。

### 2. 当前 Chatbot 页面结构

`frontend/features/chatbot/components/chatbot-shell.tsx` 当前结构为：

```text
ChatbotShell
└─ ChatbotStoreProvider
   └─ ChatbotShellContent
      ├─ Chat / Memories 原生按钮
      ├─ MemoryPanel
      └─ Chat 两栏 grid
         ├─ ConversationSidebar
         └─ ChatConversationPanel
            ├─ 会话信息卡片
            ├─ MessageList
            └─ ChatComposer
```

Chat 视图只有在 Tailwind `xl` 断点才变成 `340px + 主区` 两栏；更窄的桌面、平板和移动端都会纵向堆叠侧栏与消息区。

### 3. 主要组件及职责

| 文件 | 当前职责 | 结论 |
| --- | --- | --- |
| `components/chatbot-shell.tsx` | 获取认证信息、创建用户级 store、维护 Chat/Memories 视图、拼装工作区 | 职责偏多，应只保留工作区编排和纯 UI 状态 |
| `components/conversation-sidebar.tsx` | 状态筛选、Conversation 列表、创建、刷新、选择、重命名、归档、恢复、删除、分页及全部状态 UI | 211 行，数据列表、行操作和状态展示耦合，应拆分 |
| `components/chat-conversation-panel.tsx` | 调用 `useMessages`，渲染会话头部、错误、消息列表和 Composer | 可继续作为控制器，但头部和展示应拆出 |
| `components/message-list.tsx` | 消息滚动容器、向上分页、锚点保持、自动跟随、回到底部按钮、消息映射 | 滚动逻辑应保留在此边界，展示细节应下沉 |
| `components/message-item.tsx` | 用户/AI 消息布局、Markdown、安全链接、代码、生成操作 | Markdown 映射和消息外观耦合，应拆出 `MarkdownContent` |
| `components/chat-composer.tsx` | 草稿输入、4000 字限制、Enter/Shift+Enter、发送、停止、清空、错误 | 业务语义可复用，布局和键盘处理需重构 |
| `components/memory-panel.tsx` | Memory 筛选、列表、编辑、状态切换、删除、分页 | 数据控制、列表和表单混在一起，应拆分 |

### 4. Conversation 状态管理

`frontend/features/chatbot/stores/chatbot-store.tsx` 使用 Context + reducer 管理：

- `selectedStatus`：`active | archived`。
- `selectedConversationId`。
- Active 和 Archived 两套游标分页缓存。
- Conversation upsert、remove、replace page、append page。

Store 以 `paiguangguang.chatbot:{user_id}` 为 key 写入 `sessionStorage`，快照版本为 2。旧版本或无效快照会被拒绝。未完成 hydration 时 Provider 当前返回 `null`，避免服务端与客户端内容不一致，但会产生短暂空白。

`frontend/features/chatbot/hooks/use-conversations.ts` 负责：

- 从 URL `?conversation=...` 恢复选择。
- 首次加载当前状态页。
- 自动选择第一条 Conversation。
- 获取 Conversation 详情及 `active_generation`。
- 创建、重命名、归档、恢复、删除和加载更多。
- 在 API 结果返回后同步 store、URL 和本地 detail state。

当前 `detailLoading` 和 `detailError` 已存在于 hook 返回值中，但 `ChatbotShell` 没有把它们传给主面板，因此部分选择、创建或 mutation 错误对用户不可见。

### 5. 消息发送与数据流

当前发送流程为：

```text
ChatComposer
  -> useMessages.submitMessage()
  -> trim + crypto.randomUUID()
  -> 清空草稿
  -> useChatStream.sendMessage()
  -> openChatStream()
  -> POST /api/v1/chatbot/conversations/{id}/messages
     Authorization + Idempotency-Key
  -> readChatStreamEvents()
  -> mergeChatStreamEvent()
  -> MessageList 重新渲染
```

若发送请求在建立 SSE 前失败，`useMessages` 会恢复发送前的草稿。Conversation 为 Archived、token 缺失、内容为空或超出限制时不会发送。

Retry 和 Regenerate 分别调用：

- `POST /api/v1/chatbot/conversations/{conversation_id}/messages/{message_id}/retry`
- `POST /api/v1/chatbot/conversations/{conversation_id}/messages/{message_id}/regenerate`

Stop 调用：

- `POST /api/v1/chatbot/conversations/{conversation_id}/stop`

### 6. 流式响应处理

`frontend/features/chatbot/api/stream.ts`：

- 创建带 Bearer token、`Accept: text/event-stream` 和 `Idempotency-Key` 的请求。
- 支持跨网络 chunk 边界拼接 SSE block。
- 忽略 keepalive 注释。
- 读取 `event`、`data` 和 `id`。
- 将非 2xx JSON error envelope 转为 `ApiError`。

`frontend/features/chatbot/hooks/use-chat-stream.ts`：

- 每次发送创建独立 `AbortController`。
- Conversation 或 token 变化时中断浏览器 reader。
- Conversation 切换只执行本地 detach，不调用后端 stop。
- 忽略不属于捕获时 Conversation 的事件。

`frontend/features/chatbot/utils/merge-stream-event.ts`：

- 处理 `message.created`、`message.delta`、`message.completed`、`message.failed`、`message.cancelled`、`usage.updated` 和 `stream.end`。
- 使用 `conversationId + activeRequestId + lastSequence` 隔离事件。
- 新的 `message.created` 会为新 request 重置 sequence 去重窗口。
- 合并用户消息、assistant 消息、delta、终态和 token usage。

该 reducer 是当前可靠性最高、测试覆盖最关键的业务边界，不应因视觉重构而重写。

### 7. 消息列表与自动滚动

`MessageList` 当前具有两类关键逻辑：

- 距底部不超过 120px 时，流式 delta 继续跟随底部。
- 用户上滚后停止自动跟随并显示 “Back to bottom”。
- 距顶部不超过 64px 时自动加载更早消息。
- 历史消息 prepend 后，通过新旧 `scrollHeight` 差值保持阅读锚点。

问题：

- `scroll-smooth` 作用于整个消息容器，持续流式更新时可能累计平滑滚动并产生抖动。
- 当前容器没有可靠的全高祖先，很多场景实际由 body 滚动，`min-h-0` 无法发挥作用。
- 初始 loading、分页 loading 和 history error 的视觉层级较弱。
- history error 没有明确重试操作。

### 8. Markdown、代码块与引用

AI 消息使用 `react-markdown` 和 `remark-gfm`：

- Markdown 原始 HTML 不会被启用。
- 链接只允许 `http:`、`https:` 和 `mailto:`，并添加 `noopener noreferrer`。
- 已支持 GFM 基础语法。
- 行内代码和 `pre` 有基础样式。

当前不足：

- 行内代码和块级代码共用同一个 `code` 映射，缺少明确区分。
- 无语言标签、复制反馈和统一代码块 header。
- 表格缺少窄屏横向滚动外壳。
- blockquote、列表、标题和段落间距没有 Chatbot 专用排版规范。
- `content_json` 没有用于 citations，后端 Chatbot 也没有 citations 契约，因此本次不能设计伪引用来源。

### 9. 文件上传

Chatbot 前后端均没有文件上传契约：

- `backend/app/chatbot/api` 下没有上传路由。
- Chatbot 请求体只有文本 `content` 和 `client_request_id`。
- 仓库中的上传接口是 Admin 文档管理的 `/api/v1/admin/documents/upload`，需要 `document.upload` 权限，业务域不同，不能复用。

已确认本次 Chatbot 不需要文件上传，目标 UI 不显示上传入口。

### 10. 登录状态与路由守卫

`AuthProvider`：

- 从 localStorage 读取 token。
- 请求 `/api/v1/auth/me` 恢复用户。
- 状态为 `loading | anonymous | authenticated | expired`。

`RouteGuard`：

- 只有首页和登录页是公开路由。
- 未认证访问 `/chat-bot` 会被替换到带 `next` 参数的登录页。
- 认证检查期间显示全局 loading panel。

Chatbot 本身继续依赖该全局守卫，不应新增第二套认证判断。Chatbot feature flag 和登录守卫属于必须保留的产品边界。

### 11. 响应式布局现状

- 页面只在 `xl` 断点形成双栏。
- 没有桌面折叠侧栏。
- 没有平板或移动端抽屉。
- Composer 在普通文档流底部，不固定在 Chat 主区底部。
- 没有 `100dvh`、safe-area 或软键盘策略。
- 全局 `SiteNav` 在移动端会占用多行高度。
- Chatbot 根节点没有明确的高度与 overflow 所有权。
- 主内容只通过 Message bubble 限宽，没有统一的中央阅读列。

### 12. 当前 loading、error、empty 与 disabled 状态

| 场景 | 当前实现 | 问题 |
| --- | --- | --- |
| 认证 loading | RouteGuard loading panel | 可保留 |
| Store hydration | 返回 `null` | 用户看到空白 |
| Conversation 初始 loading | 文本 “Loading conversations” | 无骨架，列表区域变化明显 |
| Conversation error | 错误卡片和 Retry | 基本可用 |
| Conversation empty | 空状态和 New chat | 基本可用 |
| Conversation detail loading/error | hook 已提供 | UI 未展示 |
| Conversation mutation pending | 无独立状态 | 可重复点击，操作结果无局部反馈 |
| 无选中 Conversation | Chat panel 空状态 | 可保留并简化 |
| Message history loading | header 文本 | 初始与分页状态区分不清 |
| Message history error | 文本 | 无重试按钮 |
| Message empty | dashed card | 与目标的克制风格不一致 |
| Stream pending/streaming | 消息状态文字、Stop | 功能存在，但元数据过多 |
| Stream error | header 与 Composer 可能重复显示 | 应收敛到一个就近错误区 |
| Archived Conversation | Composer disabled 并显示说明 | 必须保留 |
| Composer empty/overflow/sending | Send disabled | 必须保留 |
| Memory loading/error/empty | 基础文本 | action pending 和重试不足 |

### 13. FastAPI Chatbot 接口对接矩阵

后端 `/api/v1/chatbot` 共暴露 16 个路由。

| 后端路由 | 当前前端状态 | 本次设计结论 |
| --- | --- | --- |
| `POST /conversations` | 已封装并有 New chat 入口 | 保留 |
| `GET /conversations` | 已封装，支持 status/cursor/limit | 保留 |
| `GET /conversations/{id}` | 已封装并用于 URL 恢复和选择 | 保留并增加竞态保护 |
| `PATCH /conversations/{id}` | 已封装；UI 只用于 title | 保留 title；model 只读展示，不新增选择器 |
| `POST /conversations/{id}/archive` | 已封装并有 UI | 保留 |
| `POST /conversations/{id}/restore` | 已封装并有 UI | 保留 |
| `DELETE /conversations/{id}` | 已封装并有 UI | 保留 |
| `GET /conversations/{id}/messages` | 已封装并有分页 | 保留并增加跨 Conversation 竞态保护 |
| `POST /conversations/{id}/messages` | 已完成 SSE 对接 | 保留 |
| `POST /conversations/{id}/messages/{message_id}/retry` | 已完成 SSE 对接 | 保留 |
| `POST /conversations/{id}/messages/{message_id}/regenerate` | 已完成 SSE 对接 | 保留 |
| `POST /conversations/{id}/stop` | 已封装并有 UI | 保留 |
| `GET /memories` | 已封装 status/cursor/limit；缺 memory_type 和 conversation_id | 补齐参数和 UI 筛选 |
| `GET /memories/{memory_id}` | 未封装 | 新增客户端方法并用于详情编辑器 |
| `PATCH /memories/{memory_id}` | 已封装；UI 使用 content/status，未编辑 expires_at | 补齐 expires_at 编辑 |
| `DELETE /memories/{memory_id}` | 已封装并有 UI | 保留 |

Legacy `POST /api/v1/chat/chat` 固定返回 410，只用于迁移期兼容，不属于需要对接的 Chatbot 产品接口。

### 14. 已验证的当前基线

本次分析期间实际运行：

- `npm test`：16 个测试文件、36 个测试全部通过。
- `npm run lint`：无 warning 或 error。
- `npx tsc --noEmit --incremental false`：通过。
- FastAPI Conversation、Memory、Stream、Generation Controls 契约测试：10 个测试通过；仅出现测试 JWT key 长度 warning。
- 验证后 `git status --short` 为空，未修改源代码。

### 15. 当前 UI 与组件结构的核心问题

1. Chatbot 被当作普通内容页，无法建立稳定的全高聊天体验。
2. 全局渐变 paper 背景、多个 card、badge 和阴影使页面偏“后台面板”，不符合克制的正文式聊天。
3. AI 回复仍在带边框的 bubble/card 中，没有正文阅读感。
4. Sidebar 在 1280px 以下纵向堆叠，不是可持续使用的 Conversation 导航。
5. Composer 不固定在 Chat 主区底部，长会话中输入区域离开视口。
6. 中央消息与 Composer 没有统一的固定阅读宽度。
7. 快速切换 Conversation 时，detail 和 history 请求都缺少迟到响应保护，存在串会话风险。
8. `detailLoading/detailError` 存在但未展示。
9. Conversation 和 Memory mutation 没有局部 pending，容易重复请求。
10. Markdown 排版不完整，代码块和引用的可读性不足。
11. 深色模式完全缺失。
12. 没有移动端软键盘、安全区和 viewport 高度策略。
13. 当前 Chatbot 未使用 Framer Motion；后续若对流式消息使用 layout 动画，会造成明显抖动。

---

## 二、保留与重构范围

### 1. 必须保留的业务逻辑

- `/chat-bot` 路由、feature flag 和 `notFound()` 行为。
- AuthProvider、RouteGuard、Bearer token 和登录跳转。
- 用户级 `sessionStorage` key、版本 2 快照和 active/archived Conversation 缓存。
- URL `conversation` 查询参数、非法或不存在 Conversation 的 URL 清理。
- Conversation 创建、详情、重命名、归档、恢复、删除和游标分页。
- 消息历史游标分页。
- SSE 的 Idempotency-Key、事件解析、request/conversation/sequence 隔离。
- Conversation/token 变化时只 detach reader、不隐式调用 stop。
- Send、Retry、Regenerate 和 Stop。
- 发送前清空草稿、请求建立失败后恢复草稿。
- 4000 字限制、Enter 发送、Shift+Enter 换行。
- Archived Conversation 只读。
- 用户离开底部后停止自动跟随、回到底部、历史 prepend 保持锚点。
- Memory 状态筛选、编辑、candidate/active 切换、删除和分页。
- 安全链接协议白名单。

### 2. 可以直接复用或低风险复用的模块

| 模块 | 复用方式 |
| --- | --- |
| `api/client.ts` | 保留 Conversation 和 stop 方法及唯一 `CHATBOT_API_BASE` |
| `api/stream.ts` | 保留 SSE 请求与 parser；只允许非视觉性的契约修正 |
| `utils/merge-stream-event.ts` | 原样保留为纯 reducer，除非失败测试证明必须修改 |
| `types/conversation.ts`、`types/message.ts`、`types/stream.ts` | 保留并按后端真实契约微调 |
| `stores/chatbot-store.tsx` | 保留 reducer 和 snapshot v2；增加 hydration fallback 能力 |
| `hooks/use-chat-stream.ts` | 保留 reader 生命周期与 detach 语义 |
| `hooks/use-conversations.ts` | 保留业务 API 和 URL 语义，增加竞态及 mutation 状态 |
| `hooks/use-messages.ts` | 保留发送、分页、草稿和生成控制，增加 history 隔离 |
| `hooks/use-memories.ts` | 保留数据控制器角色，扩展现有后端筛选和详情 |
| `AuthProvider`、`RouteGuard`、`isChatbotEnabled` | 不改变行为 |

### 3. 应拆分的组件

- `chatbot-shell.tsx`：拆出 `ChatbotSidebar`、`ChatbotHeader` 和 hydration skeleton。
- `conversation-sidebar.tsx`：拆出 `ConversationList` 和 `ConversationItem`。
- `chat-conversation-panel.tsx`：保留 controller，拆出 header 和纯展示状态。
- `message-item.tsx`：拆出 `MarkdownContent` 和 `CodeBlock`。
- `memory-panel.tsx`：拆出 `MemoryFilters`、`MemoryList` 和 `MemoryDetailEditor`。

不把 `MessageList` 的滚动状态拆入全局 store，也不让 `ConversationItem`、`MessageItem` 或 `MemoryList` 自行调用数据 hooks。

### 4. 应替换的样式与布局

- 替换 Chatbot 页面的全局 max-width 内容页布局。
- 对 `/chat-bot` 取消全局 SiteNav 和 main padding，其他路由不变。
- 替换 `xl` 才双栏的 grid，改为全高 Sidebar + Main shell。
- 替换 AI bubble 为正文式排版。
- 替换密集 header card、状态 badge 和重复阴影。
- 替换固定 5 行 textarea 为 1–6 行自动扩展 Composer。
- 替换浏览器 `prompt/confirm` 为页面内可访问的 rename/delete 二次确认。
- 增加 Chatbot 局部浅色/深色 CSS 变量、焦点和 reduced-motion 规则。

### 5. 本次不应修改的模块

- `backend/**` 的任何文件、迁移、配置、测试或 API。
- `frontend/app/login/**`、`frontend/features/auth/**` 和登录加密流程。
- `frontend/app/admin/**`、`frontend/features/admin/**`。
- `frontend/app/agents/**` 及 Knowledge、Browser、Office Agent。
- 首页及 `frontend/features/home/**`。
- `frontend/components/site-nav.tsx` 的其他页面视觉与行为。
- Docker、数据库、Redis、Chroma 和任务 worker。
- `/api/v1/chat/chat` legacy 兼容路由。
- Chatbot 后端模型列表、模式、联网、上传或 citations。

允许对 `frontend/components/app-shell.tsx` 做唯一的路由级分支：`/chat-bot` 不渲染全局 SiteNav、不使用普通页面 padding；所有其他路径保持当前输出。

---

## 三、目标组件架构

### 1. 目标组件树

```text
/chat-bot
└─ ChatBotPage
   └─ ChatbotShell
      └─ ChatbotStoreProvider
         ├─ ChatbotWorkspaceSkeleton
         └─ ChatbotShellContent
            ├─ ChatbotSidebar
            │  ├─ SidebarHeader
            │  ├─ NewConversationButton
            │  ├─ ConversationStatusTabs
            │  ├─ ConversationList
            │  │  └─ ConversationItem
            │  └─ WorkspaceNavigation
            └─ ChatbotMain
               ├─ ChatWorkspace
               │  ├─ ChatbotHeader
               │  ├─ MessageViewport
               │  │  ├─ HistoryLoader
               │  │  ├─ ChatEmptyState
               │  │  ├─ MessageItem
               │  │  │  └─ MarkdownContent
               │  │  │     └─ CodeBlock
               │  │  └─ JumpToBottomButton
               │  └─ ChatComposer
               │     ├─ ComposerTextarea
               │     ├─ CurrentModelLabel
               │     └─ SendOrStopButton
               └─ MemoryWorkspace
                  ├─ MemoryFilters
                  ├─ MemoryList
                  └─ MemoryDetailEditor
```

### 2. 组件职责、props、状态与依赖

#### `ChatbotShell`

- 职责：读取认证用户，创建用户级 storage key，挂载 store。
- Props：无。
- 状态：无业务状态。
- 依赖：`useAuth`、`ChatbotStoreProvider`。
- 约束：不直接请求 Conversation 或 Message。

#### `ChatbotShellContent`

- 职责：调用一次 `useConversations`，编排 Sidebar/Main，维护纯 UI 状态。
- Props：无。
- 本地状态：
  - `activeView: "chat" | "memories"`。
  - `isSidebarOpen`：平板/移动端抽屉。
  - `isSidebarCollapsed`：桌面收起。
- 依赖：`useConversations`。
- 约束：切换 view 不重建 Conversation store；关闭抽屉不改变 selected Conversation。

#### `ChatbotSidebar`

- 职责：响应式侧栏外壳、首页返回、Conversation 工作区和 Memories 导航、退出操作。
- Props：
  - `collapsed`、`open`、`activeView`。
  - Conversation 列表状态与显式 callbacks。
  - `onToggleCollapsed`、`onClose`、`onChangeView`、`onLogout`。
- 本地状态：无数据状态。
- 依赖：Framer Motion 仅用于 drawer transform/opacity 和 desktop width。

#### `ConversationList`

- 职责：渲染 initial loading、refreshing、error、empty、rows 和 load more。
- Props：
  - `items`、`selectedConversationId`、`loading`、`refreshing`、`error`、`hasMore`。
  - `pendingActions`。
  - select、load more、retry 和 row mutation callbacks。
- 状态：无。
- 依赖：`ConversationItem`。

#### `ConversationItem`

- 职责：标题、更新时间、selected 状态、inline rename、归档/恢复、删除二次确认。
- Props：
  - `conversation`、`selected`、`pendingAction`。
  - `onSelect`、`onRename`、`onArchive`、`onRestore`、`onDelete`。
- 本地状态：
  - action menu open。
  - rename draft。
  - delete confirmation open。
- 依赖：无数据 hook。
- 约束：mutation pending 时禁用重复动作；行内交互不得触发 row select。

#### `ChatWorkspace` / `ChatConversationPanel`

- 职责：当前 Conversation 的唯一 Message controller；调用一次 `useMessages`。
- Props：
  - `token`。
  - `conversation`。
  - `activeGeneration`。
  - `detailLoading`、`detailError`、`onRetryDetail`。
- 状态：由 `useMessages` 持有，不复制 Message 数组。
- 依赖：`ChatbotHeader`、`MessageList`、`ChatComposer`。

#### `ChatbotHeader`

- 职责：移动端菜单按钮、Conversation 标题、Archived 状态和轻量状态说明。
- Props：`title`、`status`、`onOpenSidebar`。
- 状态：无。
- 约束：不重复展示消息数量、stream phase、token usage 等调试型 badge。

#### `MessageList` / `MessageViewport`

- 职责：消息区唯一滚动容器、向上分页、锚点保持、底部跟随和 Jump button。
- Props：
  - `messages`、`loadingHistory`、`historyError`、`hasMore`。
  - `streamPhase`、`streamingMessageId`、`stoppingMessageId`。
  - `onLoadMore`、`onRetryHistory`、`onStopGeneration`、`onRetryMessage`、`onRegenerateMessage`。
- 本地状态/ref：
  - stick-to-bottom。
  - preserve-anchor。
  - loading-more lock。
  - jump button visibility。
- 约束：不读取 Conversation store；流式跟随使用即时滚动，用户主动跳转才平滑滚动。

#### `MessageItem`

- 职责：区分用户轻量 bubble 与 AI 正文，展示终态动作。
- Props：`message`、`isStreaming`、`stopping`、操作 callbacks、`actionsDisabled`。
- 本地状态：只允许复制反馈等短时 UI 状态。
- 依赖：`MarkdownContent`。
- 约束：不使用 Framer Motion layout；不自行请求。

#### `MarkdownContent`

- 职责：集中维护 react-markdown 的元素映射和安全链接。
- Props：`content`。
- 状态：无。
- 依赖：`react-markdown`、`remark-gfm`、`CodeBlock`。
- 约束：不启用 raw HTML；无 citations 时不渲染来源区域。

#### `CodeBlock`

- 职责：区分 inline/block code，显示语言标签、横向滚动和复制反馈。
- Props：`children`、`className`。
- 本地状态：`copied`。
- 依赖：Clipboard API 只在点击事件中访问。
- 约束：不增加语法高亮依赖。

#### `ChatComposer`

- 职责：草稿、自动高度、键盘语义、当前模型、发送/停止和就近错误。
- Props：
  - `value`、`model`、`disabled`、`sending`、`stopping`、`maxLength`、`error`。
  - `onChange`、`onSubmit`、`onStop`。
- 本地状态/ref：
  - `isComposing`。
  - textarea ref 和自动高度。
- 依赖：无数据 hook。
- 约束：不显示上传、模式、联网或模型切换；中文 IME 组合期间 Enter 不发送。

#### `MemoryWorkspace` / `MemoryPanel`

- 职责：调用一次 `useMemories`，维护选择项并编排 Memory 子组件。
- Props：`token`、`currentConversationId`。
- 状态：selected memory ID；列表、detail 和 mutation 状态由 hook 提供。
- 依赖：`MemoryFilters`、`MemoryList`、`MemoryDetailEditor`。

#### `MemoryFilters`

- 职责：status、memory type、scope 筛选。
- Props：
  - `status`、`memoryType`、`scope`、`hasCurrentConversation`。
  - 对应 change callbacks。
- 状态：无。
- 规则：
  - Status：Active、Candidate、Superseded。
  - Type：All 加后端已有的六种 `memory_type`。
  - Scope：All conversations 或 Current conversation；没有当前 Conversation 时禁用后者。

#### `MemoryDetailEditor`

- 职责：通过 `GET /memories/{id}` 读取单条详情；编辑 content、status、expires_at；删除。
- Props：`memoryId`、`loading`、`error`、`memory`、`saving`、`deleting` 及 callbacks。
- 本地状态：表单 draft。
- 依赖：请求发生在 `useMemories`，组件本身不 fetch。
- 约束：`superseded` 只读展示；可写 status 仅为后端允许的 candidate/active。

### 3. 状态归属总表

| 状态 | 唯一归属 |
| --- | --- |
| token、user、认证状态 | `AuthProvider` |
| selected status、selected Conversation、Conversation pages | `ChatbotStoreProvider` |
| Conversation loading/error/detail/mutation | `useConversations` |
| 当前 Conversation 消息、history cursor、draft、stream state | `useMessages` |
| SSE reader、AbortController、active request | `useChatStream` |
| SSE event 合并 | `mergeChatStreamEvent` |
| 自动滚动与历史锚点 | `MessageList` |
| Sidebar 展开、抽屉、Chat/Memories | `ChatbotShellContent` |
| Memory 列表、detail、筛选、mutation | `useMemories` |
| 输入法组合与 textarea DOM 高度 | `ChatComposer` |

### 4. 关键数据流

#### Conversation 切换

```text
ConversationItem click
  -> useConversations.openConversation(id)
  -> 记录 detail request identity
  -> GET conversation detail
  -> 仅当前 request + 当前目标 id 可提交结果
  -> store selected id/status + URL
  -> useChatStream abort old reader（不调用 stop）
  -> useMessages reset current state
  -> GET new conversation history
  -> 仅当前 history request + 当前 conversation id 可提交结果
```

#### 流式发送

```text
ChatComposer
  -> useMessages
  -> useChatStream
  -> stream API
  -> SSE parser
  -> mergeChatStreamEvent
  -> MessageList
  -> near bottom ? follow : preserve user anchor
```

#### Memory 详情

```text
Memory row select
  -> useMemories.loadDetail(id)
  -> GET /memories/{id}
  -> MemoryDetailEditor
  -> PATCH content/status/expires_at
  -> 同步 detail 与当前筛选列表
```

---

## 四、视觉设计规范

### 1. 页面背景与主题边界

Chatbot 使用局部主题 class，不改变其他页面：

| Token | 浅色 | 深色 |
| --- | --- | --- |
| Page | `#ffffff` | `#171819` |
| Sidebar | `#f5f6f7` | `#111213` |
| Surface | `#ffffff` | `#212326` |
| Subtle | `#f4f5f6` | `#292b2f` |
| Text | `#24262a` | `#eceef1` |
| Muted | `#6b7280` | `#a5aab3` |
| Border | `#e4e6e9` | `#35383d` |
| Accent | 项目 `tide / #2d6f73` | `#73b6bb` |
| Danger | 项目 `clay / #b65f3b` | `#e58c68` |

深色模式跟随 `prefers-color-scheme: dark`，本次不新增全站主题切换器。所有 Chatbot token 必须限定在 Chatbot 根 class 下。

### 2. 页面高度与 overflow

- `/chat-bot` 根容器：`height: 100dvh`、`min-height: 0`、`overflow: hidden`。
- Chatbot Main：纵向 flex、`min-width: 0`、`min-height: 0`。
- 只允许两个独立垂直滚动容器：
  - Conversation/Sidebar 内容区。
  - Message viewport。
- Composer 位于 Main 的 flex 底部，不相对浏览器视口使用 `position: fixed`。
- 底部 padding 包含 `env(safe-area-inset-bottom)`。
- 不在初始方案中使用 VisualViewport JavaScript，避免 resize state、hydration 和键盘动画抖动；以现代浏览器 `100dvh` 为基线并进行真机验证。

### 3. 侧边栏宽度与状态

| Viewport | 规则 |
| --- | --- |
| Desktop ≥ 1024px | 展开 280px；收起 64px；占据布局列 |
| Tablet 768–1023px | 288px 覆盖式 drawer；默认关闭 |
| Mobile < 768px | `min(86vw, 320px)` 覆盖式 drawer；默认关闭 |

- Desktop collapsed 只显示通用、项目自有的几何图标和可访问 tooltip/label。
- 不复制任何产品专属图标。
- Drawer 打开后显示半透明 overlay，点击 overlay、Escape 或选择 Conversation 后关闭。
- Sidebar header 提供返回首页；底部提供 Memories 与退出。
- Conversation 行高约 44–48px，标题一行截断，时间只在展开态显示。
- 行操作默认隐藏于 More disclosure，hover、focus-within 或 selected 时可见。

### 4. 主内容最大宽度

- 消息正文与 Composer 共用 `max-width: 48rem / 768px`。
- Main 两侧 padding：
  - Desktop：32px。
  - Tablet：24px。
  - Mobile：16px。
- 空白区由 Main 自然分配，不使用大面积 card 包裹消息列表。

### 5. 消息排版

#### AI 回复

- 不使用 bubble、外框或 card shadow。
- 占据阅读列宽度。
- 正文 `15–16px`，line-height `1.75`。
- 段落间距 12–16px。
- 消息之间 28–32px；移动端 20–24px。
- Assistant 的身份提示使用普通文本或项目自有的简洁标记，不使用品牌 avatar。

#### 用户消息

- 右对齐。
- 最大宽度约 75%；移动端可到 86%。
- 使用 Subtle 背景、1px 弱边框、14px 圆角。
- padding：10px 14px。
- 保留用户输入中的换行。

#### 状态与操作

- Pending 显示克制的三点/文本状态，不让整个 MessageItem pulse。
- Failed/Cancelled 在正文下方显示小型状态与 Retry。
- Completed AI 消息可显示 Regenerate。
- Stop 统一以 Composer 为主要入口；消息项可保留针对 pending/streaming message 的辅助入口。
- token、sequence、内部 request ID 不出现在默认产品 UI。

### 6. Markdown 与代码

- `h1/h2/h3` 使用 1.35/1.2/1.1rem，不抢占页面主标题层级。
- 列表使用 1.5em 左缩进和 6px item 间距。
- blockquote 使用 3px Accent 左边框、Subtle 背景和 Muted 文本。
- 表格外层横向滚动；cell 使用 1px Border。
- 链接使用 Accent、下划线 offset，hover 提高对比度。
- inline code 使用 Subtle 背景、6px 圆角和 mono font。
- block code 使用独立 header、语言标签、复制按钮和横向滚动。
- 不安装 syntax-highlighting 依赖。
- 不启用 raw HTML。
- 无 citations 契约时不显示来源、脚注或伪引用卡片。

### 7. Composer 结构

```text
Composer surface
├─ Auto-growing textarea（1–6 行）
├─ Inline error / archived notice
└─ Footer
   ├─ Current model label（只读）
   ├─ Character count（接近限制时增强）
   └─ Send 或 Stop
```

- 最大宽度与消息正文同为 768px。
- 圆角 20px。
- 边框 1px Border。
- 默认无重阴影；使用 `0 12px 32px rgba(0,0,0,0.08)` 量级的克制悬浮阴影。
- textarea 默认 1 行，最大约 6 行，超过后内部滚动。
- Enter 发送；Shift+Enter 换行。
- compositionstart 到 compositionend 之间 Enter 不发送。
- 内容为空、超过 4000、Archived、无 token 或发送中时 Send disabled。
- Streaming 时 Send 替换为 Stop，避免两个主操作并列。
- 不显示 Clear 主按钮；需要清空时使用键盘选择或小型次要操作，避免操作区拥挤。
- 只显示当前模型，例如 `deepseek-chat`；不提供下拉框。
- 不显示上传、深度思考、联网或模式按钮。

### 8. 字体层级

| 元素 | 字号/行高 | 字重 |
| --- | --- | --- |
| Conversation/Chat 标题 | 18–20px / 1.35 | 600 |
| AI 正文 | 15–16px / 1.75 | 400 |
| 用户正文 | 15px / 1.65 | 400 |
| Sidebar row | 14px / 1.4 | 400–500 |
| Control | 13–14px / 1.3 | 500–600 |
| Metadata | 12px / 1.4 | 400–500 |
| Code | 13–14px / 1.6 | 400 |

继续使用项目的 sans token 和系统字体，不引入字体依赖。

### 9. 间距、圆角、边框与阴影

- 间距基线：4、8、12、16、24、32px。
- 小按钮圆角：8px。
- 用户 bubble：14px。
- Composer：20px。
- Drawer/Popover：12px。
- 边框统一 1px。
- Sidebar 与 Main 之间只使用边框或色差，不使用重阴影。
- 阴影只用于 Composer、drawer 和 popover。
- Hover 不使用 translate 位移。

### 10. Hover、Focus、Disabled 与 Loading

- Hover：Subtle 背景或 Border/Accent 变化。
- Focus-visible：2px Accent ring + 2px offset；不可移除键盘焦点。
- Disabled：降低对比度、`cursor: not-allowed`，同时通过真实 `disabled` 属性阻止操作。
- Loading：
  - Store hydration：稳定的 shell skeleton。
  - Conversation initial load：固定高度 row skeleton。
  - Refresh：保留现有列表并显示局部进度。
  - Message initial history：阅读列 skeleton。
  - History pagination：顶部小型 loader，不覆盖内容。
  - Mutation：只禁用相关 row/control。
- Error：
  - 列表错误保留 Retry。
  - detail error 在 Main 显示，并提供 Retry。
  - stream/control error 只在 Composer 上方显示一次。
  - refresh 失败时保留旧数据。

### 11. Framer Motion

- 仅用于：
  - Drawer overlay opacity。
  - Drawer x transform。
  - Desktop sidebar width。
- 时长 160–200ms。
- 不对消息列表、流式正文、Markdown、Composer 高度或 history prepend 使用 `layout`。
- `prefers-reduced-motion` 时禁用非必要动画。
- Drawer 动画只使用 transform/opacity，避免触发布局重排。

---

## 五、实施计划

### 阶段 1：接口契约与跨 Conversation 正确性

**修改目标**

- 补齐 Memory detail、memory_type、conversation_id 和 expires_at 的前端契约。
- 修复 Conversation detail 和 Message history 迟到响应污染当前选择的风险。
- 保持 SSE reducer 和 reader 行为不变。

**涉及文件**

- 修改：`frontend/features/chatbot/api/memories.ts`
- 修改：`frontend/features/chatbot/types/memory.ts`
- 修改：`frontend/features/chatbot/hooks/use-memories.ts`
- 修改：`frontend/features/chatbot/hooks/use-conversations.ts`
- 修改：`frontend/features/chatbot/hooks/use-messages.ts`
- 新增：`frontend/features/chatbot/__tests__/memory-api.test.ts`
- 修改：`frontend/features/chatbot/__tests__/use-conversations.test.tsx`
- 新增：`frontend/features/chatbot/__tests__/use-messages.test.tsx`
- 修改：`frontend/features/chatbot/__tests__/use-memories.test.tsx`

**不能破坏的行为**

- Conversation/token 变化只 abort reader，不调用 stop。
- URL Conversation 恢复和 404 清理。
- active/archived 缓存。
- 历史分页顺序和去重。
- Send/Retry/Regenerate/Stop 的现有路径。

**验收标准**

- 先选择 A 再快速选择 B，即使 A 后返回，最终 selected detail 和 URL 仍为 B。
- A history 在切到 B 后返回时，不会写入 B 的 Message state。
- Memory 客户端覆盖所有四个后端路由。
- Memory 列表能发送 status、memory_type、conversation_id、cursor、limit。
- detail 和 mutation 只提交当前 request 的结果。

**测试方式**

- Vitest 使用延迟 Promise 明确模拟 A/B 反向返回。
- 更新 API mock 断言真实 `/api/v1/chatbot` 路径和 query。
- 运行：
  - `npm test -- features/chatbot/__tests__/use-conversations.test.tsx`
  - `npm test -- features/chatbot/__tests__/use-messages.test.tsx`
  - `npm test -- features/chatbot/__tests__/use-memories.test.tsx`
  - `npm test -- features/chatbot/__tests__/chat-stream.test.ts`
  - `npm test -- features/chatbot/__tests__/use-chat-stream.test.tsx`

### 阶段 2：全高 Chatbot Shell 与路由级布局

**修改目标**

- 让 `/chat-bot` 成为独立 `100dvh` 工作区。
- 保证其他路由继续使用当前 SiteNav 和页面 padding。
- 建立 Desktop sidebar + Main、Tablet/Mobile drawer 的结构边界。
- 为 store hydration 提供稳定 skeleton。

**涉及文件**

- 修改：`frontend/app/chat-bot/page.tsx`
- 修改：`frontend/components/app-shell.tsx`
- 修改：`frontend/app/globals.css`
- 修改：`frontend/features/chatbot/components/chatbot-shell.tsx`
- 修改：`frontend/features/chatbot/stores/chatbot-store.tsx`
- 新增：`frontend/features/chatbot/components/chatbot-sidebar.tsx`
- 新增：`frontend/features/chatbot/components/chatbot-header.tsx`
- 修改：`frontend/app/chat-bot/page.test.tsx`
- 修改：`frontend/features/chatbot/__tests__/chatbot-workspace.test.tsx`
- 修改：`frontend/features/chatbot/__tests__/chatbot-store.test.tsx`
- 新增：`frontend/components/app-shell.test.tsx`

**不能破坏的行为**

- `/chat-bot` 路由和 feature flag。
- RootLayout 的 AuthProvider、Suspense、RouteGuard、AppShell 顺序。
- 首页和所有 Agent/Admin 页的 SiteNav 与 padding。
- 用户级 sessionStorage key 和 snapshot v2。

**验收标准**

- Chatbot 页面没有全局 SiteNav，Sidebar 内提供 Home 和 Logout。
- 其他非首页页面继续显示 SiteNav。
- Chatbot root 占满 `100dvh`，body 不产生第二条纵向滚动条。
- Sidebar 与 Message viewport 各自拥有滚动边界。
- Store hydration 期间不出现空白或 hydration warning。

**测试方式**

- Testing Library 模拟 `usePathname` 分别为 `/chat-bot`、`/agents/knowledge` 和 `/admin`。
- 断言 Chatbot page 不再输出 `max-w-7xl` 外壳。
- 运行 Chatbot page、AppShell、store 和 workspace 测试。
- 手工在 1440×900、1024×768、820×1180、390×844、360×800 验证 overflow。

### 阶段 3：Conversation 侧栏与操作状态

**修改目标**

- 拆分 Sidebar、List 和 Item。
- 用行内 rename、More disclosure 和 delete 二次确认替换 `window.prompt/confirm`。
- 增加 per-conversation mutation pending 和 New chat pending。
- 完成桌面折叠、平板/移动抽屉和键盘交互。

**涉及文件**

- 修改：`frontend/features/chatbot/components/conversation-sidebar.tsx`
- 新增：`frontend/features/chatbot/components/conversation-list.tsx`
- 新增：`frontend/features/chatbot/components/conversation-item.tsx`
- 修改：`frontend/features/chatbot/components/chatbot-sidebar.tsx`
- 修改：`frontend/features/chatbot/hooks/use-conversations.ts`
- 修改：`frontend/features/chatbot/__tests__/conversation-sidebar.test.tsx`
- 修改：`frontend/features/chatbot/__tests__/use-conversations.test.tsx`
- 新增：`frontend/features/chatbot/__tests__/conversation-item.test.tsx`

**不能破坏的行为**

- status tab、分页、刷新、自动选择和 URL。
- Rename、Archive、Restore、Delete 的 API 与 store 更新。
- 删除当前 Conversation 后清空选择和 URL，并阻止自动重新选择。
- Archived Conversation 恢复后回到 active。

**验收标准**

- 重复点击不会产生重复 mutation。
- 操作失败保留原行和选择，并在就近位置显示错误。
- 行内按钮不会误触选择 Conversation。
- Drawer 支持 overlay、Escape 和选择后关闭。
- 所有控制可用键盘访问，并具有 focus-visible。

**测试方式**

- 更新现有 ConversationSidebar 测试覆盖 loading/error/empty/pagination。
- 新增 pending、rename、delete cancel/confirm、事件冒泡和 Escape 测试。
- 运行 `use-conversations` 和 Sidebar 相关测试。
- 手工验证 desktop expanded/collapsed、tablet/mobile drawer。

### 阶段 4：消息正文、Markdown 与自动滚动

**修改目标**

- 将 AI 回复改为正文式布局，用户消息保留轻量 bubble。
- 拆出 Markdown 和 CodeBlock。
- 保留并强化滚动锚点，不让 smooth scroll 干扰 streaming。
- 补齐 history retry、初始 empty/loading 和终态操作的视觉状态。

**涉及文件**

- 修改：`frontend/features/chatbot/components/message-list.tsx`
- 修改：`frontend/features/chatbot/components/message-item.tsx`
- 新增：`frontend/features/chatbot/components/markdown-content.tsx`
- 新增：`frontend/features/chatbot/components/code-block.tsx`
- 修改：`frontend/features/chatbot/components/chat-conversation-panel.tsx`
- 修改：`frontend/features/chatbot/__tests__/message-list.test.tsx`
- 新增：`frontend/features/chatbot/__tests__/markdown-content.test.tsx`
- 修改：`frontend/features/chatbot/__tests__/generation-controls.test.tsx`

**不能破坏的行为**

- GFM、安全链接和 raw HTML 默认禁用。
- Message 顺序与 stream delta 实时显示。
- 近底跟随、上滚锁定、Jump button、历史 prepend 锚点。
- Failed/Cancelled Retry、Completed Regenerate、Pending/Streaming Stop。

**验收标准**

- AI 回复没有 bubble/card 外框。
- 用户消息右对齐且宽度受限。
- 标题、列表、表格、blockquote、inline code 和 block code 样式明确。
- `javascript:` 等协议不生成可点击链接。
- 流式期间用户上滚后 scrollTop 不被修改。
- 加载旧消息后原可见消息保持在相同视觉位置。
- Jump button 主动点击才使用 smooth behavior。

**测试方式**

- 扩展现有 `message-list.test.tsx`。
- 新增 Markdown 语义、安全链接、code 和 table wrapper 测试。
- 使用可配置 `scrollHeight/clientHeight/scrollTop` 的 JSDOM 测试锚点。
- 手工用长代码块、长表格、连续 delta 和 100+ messages 验证。

### 阶段 5：Composer、模型展示与生成控制

**修改目标**

- 将输入框重构为底部居中的 1–6 行自动扩展 Composer。
- 只读显示当前模型。
- Send 与 Stop 使用同一主操作位置。
- 增加中文 IME 保护和清晰的 disabled/loading/error 状态。

**涉及文件**

- 修改：`frontend/features/chatbot/components/chat-composer.tsx`
- 修改：`frontend/features/chatbot/components/chat-conversation-panel.tsx`
- 修改：`frontend/features/chatbot/hooks/use-messages.ts`
- 修改：`frontend/features/chatbot/__tests__/chat-composer.test.tsx`
- 修改：`frontend/features/chatbot/__tests__/generation-controls.test.tsx`

**不能破坏的行为**

- 4000 字前后端一致限制。
- Enter 发送、Shift+Enter 换行。
- Archived Conversation 禁止发送。
- 发送建立失败时恢复草稿。
- Stop 继续调用现有 endpoint，不把浏览器 abort 当作 stop。

**验收标准**

- composition 期间 Enter 不发送，compositionend 后可发送。
- textarea 在 1–6 行内增长，超过最大高度后内部滚动。
- Streaming 时主按钮显示 Stop，不能重复 Send。
- 当前模型显示在 Composer footer，页面 header 不重复显示调试信息。
- 不存在上传、模式、联网和深度思考入口。
- archived、overflow、empty、sending、stopping 状态均有正确 disabled 与文案。

**测试方式**

- 扩展 ChatComposer 测试覆盖 compositionStart/compositionEnd。
- 测试 Send/Stop 条件切换、model label、maxLength、archived。
- 测试发送失败恢复草稿和 stop request 参数。
- 手工验证中文、英文、多行粘贴和移动端软键盘。

### 阶段 6：Memory 工作区与接口完整性

**修改目标**

- 拆分 Memory Filters、List 和 Detail Editor。
- 接入 status、memory_type、current Conversation scope 和 detail endpoint。
- 支持 content、candidate/active 和 expires_at 编辑。
- 增加独立 loading/error/empty/mutation 状态。

**涉及文件**

- 修改：`frontend/features/chatbot/components/memory-panel.tsx`
- 新增：`frontend/features/chatbot/components/memory-filters.tsx`
- 新增：`frontend/features/chatbot/components/memory-list.tsx`
- 新增：`frontend/features/chatbot/components/memory-detail-editor.tsx`
- 修改：`frontend/features/chatbot/hooks/use-memories.ts`
- 修改：`frontend/features/chatbot/types/memory.ts`
- 修改：`frontend/features/chatbot/__tests__/memory-panel.test.tsx`
- 修改：`frontend/features/chatbot/__tests__/use-memories.test.tsx`

**不能破坏的行为**

- Active/Candidate/Superseded 列表。
- cursor pagination。
- content 编辑、candidate/active 切换和删除。
- 删除后从当前列表移除。
- 409 conflict 和其他 API error 不覆盖原数据。

**验收标准**

- 点击 Memory 后调用 `GET /memories/{id}`。
- Type filter 使用后端已有六种 memory_type。
- Current conversation scope 只在存在当前 Conversation 时可用。
- expires_at 能设置和清除。
- 保存/删除 pending 只锁定 detail editor。
- 所有 `/api/v1/chatbot/memories` 路由都有明确前端入口。

**测试方式**

- API mock 断言 detail path 和所有 list query。
- Hook 测试筛选变化、迟到 detail 响应、update 后跨筛选移除、delete。
- 组件测试 detail loading/error/save/delete/expiry。
- 运行 Memory 相关完整测试。

### 阶段 7：主题、动效、状态统一与完整回归

**修改目标**

- 完成 Chatbot 局部深色模式、focus-visible、reduced-motion 和 safe-area。
- 统一所有 loading/error/empty/disabled。
- 验证响应式、软键盘、overflow 和无障碍。
- 完成生产构建回归。

**涉及文件**

- 修改：`frontend/app/globals.css`
- 修改：`frontend/features/chatbot/components/chatbot-shell.tsx`
- 修改：`frontend/features/chatbot/components/chatbot-sidebar.tsx`
- 修改：所有本轮 Chatbot 展示组件的最终 class 与 aria 属性
- 修改：相关 Chatbot 测试

**不能破坏的行为**

- 其他页面的 paper/ink/moss/clay/tide 主题。
- RouteGuard、feature flag、URL、storage 和 API。
- reduced-motion 下的功能与可见性。
- 所有既有 Chatbot tests。

**验收标准**

- 浅色和系统深色模式均达到清晰对比度。
- focus order 为 Sidebar controls → Main header → messages/actions → Composer。
- reduced-motion 下 drawer 立即或近乎立即切换。
- 390×844 和 360×800 下 Composer 不被页面裁切。
- iOS Safari 与 Android Chrome 软键盘打开时，输入框仍在可见区域；关闭后高度恢复。
- 页面只有预期的 Sidebar 和 Message 两个垂直滚动区域。
- 无 hydration warning、重复请求或明显 layout shift。

**测试方式**

- `npm test`
- `npm run lint`
- `npx tsc --noEmit --incremental false`
- `npm run build`
- `uv run pytest tests/chatbot/test_conversation_api.py tests/chatbot/test_memory_api.py tests/chatbot/test_stream_api.py tests/chatbot/test_generation_controls.py -q`
- 手工 viewport：1440×900、1024×768、820×1180、390×844、360×800。
- 真机或系统模拟器：iOS Safari、Android Chrome，分别测试键盘打开、流式输出和 Conversation drawer。

---

## 六、风险与缓解措施

### 1. 流式输出被破坏

**风险来源**

- 视觉重构时把 stream state 移到新组件。
- Message 组件 key 改变导致流式节点反复卸载。
- 修改 reducer 以配合动画。
- 将 abort 误接成 stop。
- 使用 Framer Motion layout 包裹不断增长的 Markdown。

**缓解**

- `merge-stream-event.ts`、SSE event types 和 parser 默认不改。
- `useMessages` 仍是当前 Conversation 的唯一 Message owner。
- Message key 始终为后端 message ID。
- Conversation/token 变化只 abort reader；Stop 只能由显式用户操作触发。
- 不对 MessageList、MessageItem、Markdown 和 Composer 使用 layout animation。
- 阶段 1、4、5 每次变更后运行 stream reducer 和 useChatStream 测试。

### 2. 自动滚动异常

**风险来源**

- 全高布局改变滚动容器。
- smooth scroll 与高频 delta 竞争。
- 历史 prepend 后 DOM 高度变化。
- Markdown 图片或代码块后续改变高度。

**缓解**

- MessageList 是唯一消息滚动 owner。
- streaming follow 使用直接 scrollTop，不使用 smooth。
- 用户主动 Jump 才 smooth。
- prepend 前记录 scrollHeight，commit 后在 `useLayoutEffect` 恢复 delta。
- stick-to-bottom 由用户 scroll 实时更新，不从 stream phase 推断。
- 对底部跟随、上滚锁定和 prepend 分别保留自动化测试。

### 3. Conversation 切换状态错乱

**风险来源**

- A detail/history 在 B 之后返回。
- selected ID、detail、URL 和 store 更新不是同一目标。
- 旧 SSE 事件到达新 Conversation。
- status tab 切换仍展示旧 detail。

**缓解**

- detail/history 请求捕获 target Conversation ID 和 request identity。
- 结果提交前比较当前目标，不匹配即忽略。
- Conversation 变化立即 reset Message state 并 abort old reader。
- reducer 继续校验 conversationId 和 activeRequestId。
- Status tab 与 selected Conversation 的产品语义明确：切换筛选不隐式切换当前会话；若 UI 需要清空，只通过显式 action 完成。
- 测试 A/B 反向返回、URL 深链、404 和删除当前项。

### 4. Hydration 问题

**风险来源**

- sessionStorage/localStorage、window、crypto、Clipboard、matchMedia 在 render 阶段访问。
- 服务端与客户端根据 viewport 输出不同组件树。
- 深色模式使用 JS 初始 state。
- locale date 文本在 SSR/CSR 不一致。

**缓解**

- 继续通过 effect hydrate store，并显示稳定 fallback。
- 响应式用 CSS media query；Desktop/Drawer DOM 保持可预测。
- 深色模式用 CSS `prefers-color-scheme`，不在 render 读取 matchMedia。
- crypto 和 Clipboard 只在用户事件中调用。
- window/document 只在 effect、layout effect 或 handler 中访问。
- Sidebar 时间格式仅在认证后的 client workspace 中渲染；必要时使用固定格式而非环境差异较大的 `toLocaleString()`。

### 5. 移动端输入框被软键盘遮挡

**风险来源**

- `100vh` 包含浏览器 chrome。
- Composer 相对 viewport fixed。
- body 和 Main 双重滚动。
- safe-area 未计入。

**缓解**

- 使用 `100dvh`，不使用旧 `100vh` 作为主高度。
- Composer 位于 Main flex 流中，不使用 viewport fixed。
- Main `min-h-0`，Message viewport `flex: 1`。
- Composer padding 包含 `env(safe-area-inset-bottom)`。
- iOS/Android 真机分别测试键盘打开/关闭、textarea 增长和流式响应。
- 只有真机证明 CSS 方案不足时，后续才单独设计 VisualViewport fallback；本计划不预先引入该复杂度。

### 6. 页面高度与 overflow 冲突

**风险来源**

- Root body min-height、AppShell main padding、Chatbot `100dvh` 同时生效。
- Grid/flex 子节点缺少 `min-h-0`。
- Sidebar 或 MessageList 继续由 body 滚动。

**缓解**

- AppShell 对 `/chat-bot` 使用专门分支，移除普通页面 padding 和 SiteNav。
- Chatbot root、Main、Message panel 每层明确 `min-h-0`。
- body 在 Chatbot 页不承担聊天内容滚动。
- 以 DOM/CSS 检查和五种 viewport 手工验证双重确认。

### 7. 组件拆分导致重复请求

**风险来源**

- Sidebar、List、Item 各自调用 `useConversations`。
- MemoryList 和 DetailEditor 各自调用 `useMemories`。
- Chat header 和 MessageList 分别读取 Conversation detail。
- React Strict Mode 暴露非幂等 effect。

**缓解**

- `ChatbotShellContent` 只调用一次 `useConversations`。
- `ChatConversationPanel` 只调用一次 `useMessages`。
- `MemoryPanel` 只调用一次 `useMemories`。
- 所有下级组件只接收 props。
- effect 使用 request identity/AbortController，cleanup 后的请求不能提交 state。
- 测试断言一次用户动作对应一次 API 调用。

### 8. Framer Motion 导致布局抖动

**风险来源**

- 对 Sidebar width、Main width和 Message height 同时动画。
- 使用 `AnimatePresence` 卸载仍在流式更新的节点。
- 自动高度 textarea 与 layout animation 竞争。

**缓解**

- Motion 只覆盖 drawer transform/opacity 和 Desktop Sidebar width。
- Main 使用 CSS 布局自然响应，不对消息节点做 presence/layout。
- Composer 高度由 textarea DOM 直接测量，不交给 Motion。
- reduced-motion 禁用非必要 transition。
- 用连续流式响应、快速 drawer 开关和长 Markdown 做手工压力验证。

### 9. 错误和 pending 状态造成数据丢失

**风险来源**

- refresh 前清空列表。
- mutation 失败时乐观移除。
- stream error 重置整段消息。
- Memory 筛选切换期间迟到请求覆盖新筛选。

**缓解**

- refresh 保留 stale data。
- Conversation/Memory 删除在后端成功后再移除。
- stream failure 只更新当前 assistant message 和 error，不清空 history。
- Memory list/detail 同样使用 request identity。
- mutation pending 以资源 ID 为粒度，不全局锁定工作区。

---

## 七、完成定义

重构完成必须同时满足：

- `/chat-bot` 路由、feature flag、认证和 URL 行为不变。
- 16 个 `/api/v1/chatbot` 路由均有前端客户端覆盖；除只读模型字段外，现有可操作字段均有明确 UI。
- 不存在上传、联网、深度思考或模式选择入口。
- SSE request/conversation/sequence 隔离、detach 和 stop 语义不变。
- 快速切换 Conversation 不会发生 detail、history 或 stream 污染。
- AI 为正文式展示，用户为轻量 bubble，阅读列与 Composer 同宽。
- Desktop、Tablet、Mobile 均具备可用的 Sidebar。
- 自动滚动、向上分页和锚点保持通过测试。
- Markdown、代码块、引用、表格和安全链接符合规范。
- Composer 支持 IME、自动高度、发送/停止和当前模型展示。
- 系统深色模式、focus-visible、reduced-motion 和 safe-area 可用。
- `npm test`、`npm run lint`、TypeScript、`npm run build` 和相关 FastAPI 契约测试全部通过。
- 不修改后端、其他 Agent/Admin/Home 页面或全站业务逻辑。

## 八、设计决策摘要

- 采用渐进式边界重构，不重写状态层。
- 正确性修复先于视觉重构。
- Chatbot 使用独立全高工作区；其他页面不变。
- Sidebar Desktop 可折叠，Tablet/Mobile 为 drawer。
- AI 正文、用户轻量 bubble、Composer 固定在 Main flex 底部。
- 不设计上传。
- 当前模型只读展示，不设计模式、联网或模型选择。
- Memory 补齐后端已有 detail、type、conversation 和 expires_at 能力。
- Framer Motion 只用于 Sidebar/Drawer，不动画流式内容。
