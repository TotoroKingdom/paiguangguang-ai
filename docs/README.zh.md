# s01：Codex 是怎样运行起来的？——从 `codex` 命令到 Agent Runtime

> **一句话**：Codex 不只是一次大模型 API 调用，而是一套把用户界面、会话管理、模型推理、工具执行和本地状态连接起来的软件系统。
>
> **本章只解决一个问题**：在终端输入 `codex` 后，究竟有哪些模块参与工作？

**源码基线**：[openai/codex @ `014489466a17`](https://github.com/openai/codex/tree/014489466a1739c2c563cdfe57880c2c7c8680e3)（2026-10-20 检查）。GitHub `main` 会持续变化，本教程后续以固定提交为准；不同版本可能存在实现差异。

## 你将学会什么

学完本章，你应当能回答三个问题：

1. `codex`、`codex exec` 和 Codex 的核心引擎是什么关系？
2. `cli`、`tui`、`app-server`、`core`、`exec-server` 各自负责什么？
3. 如果想追踪用户的一次提问，应该从哪个源码文件进入？

不要求提前会 Rust，也**不需要编译整个 Codex 仓库**。

---

## 1. 从一个真实场景开始

你在某个 Git 仓库打开终端，输入：

```bash
codex
```

进入交互界面，输入：

> 帮我看看这个项目是做什么的，不要修改任何文件。

表面看，它只是回答你的问题。实际上，要完成这样一件事，系统至少需要做几类工作：接收输入、找到或创建会话、组织模型上下文、请求模型、执行模型要求的只读操作、把结果反馈给模型、再把最终答复显示出来。

由此得到第一个结论：

**模型负责生成回答和提出操作请求；Codex Runtime 负责管理一次任务，并在权限边界内执行操作。**

请先不要急着阅读成百上千行 Rust。我们先认识这些职责分别放在什么地方。

## 2. 一张图看懂 Codex 的整体结构

下图是**便于理解的逻辑视图**，不是“每个方框对应一个独立操作系统进程”的进程图。

```text
               ┌──────────────────────────────┐
               │          用户入口              │
               │  交互终端 / 非交互命令 / IDE 等  │
               └──────────────┬───────────────┘
                              │
               ┌──────────────▼───────────────┐
               │      Client / App Server      │
               │     接收请求、返回事件、对外协议  │
               └──────────────┬───────────────┘
                              │
               ┌──────────────▼───────────────┐
               │           Core               │
               │  ThreadManager / CodexThread  │
               │     Session / Turn Runtime    │
               └──────┬──────────┬───────────┘
                      │          │
            ┌─────────▼────┐ ┌──▼────────────────┐
            │ Model Client │ │ Tool / Execution  │
            │ 请求模型与流式 │ │ 工具路由、命令、补丁 │
            │ 响应解析      │ │ 审批、Sandbox      │
            └──────────────┘ └───────────────────┘
                      │          │
                      └─────┬────┘
                            │
                     History / State
                     会话记录与持久化
```

阅读方向是：**用户入口 → 请求与通信 → 会话运行时 → 模型与执行能力 → 状态记录**。

注意两个重要边界：

- **App Server 是服务/通信边界，不等于一定启动了单独进程。** 当前 TUI 与 `codex exec` 均可使用进程内 App Server；也存在连接守护进程或远程服务的路径。
- **Core 不是大模型。** `codex-core` 是本地 Agent 的业务逻辑，真正推理由模型服务完成；Core 组织请求、处理结果并驱动工具执行。

## 3. 到真实源码里认领这些模块

Codex 的主体实现位于 `codex-rs/` Rust workspace。Rust 中的 **crate** 可以先理解为一个可编译的库或程序单元；不等同于 Java 的 package，也不保证每个 crate 都是单独进程。

| 目录（相对 `codex-rs/`） | 本章只需要记住的职责 |
|---|---|
| `cli/` | `codex` 命令的参数解析和子命令分发 |
| `tui/` | 交互式终端界面：输入、渲染、交互 |
| `exec/` | `codex exec` 非交互式使用入口 |
| `app-server/` | 应用服务运行时：请求处理、事件投递、客户端连接 |
| `app-server-client/` | TUI/Exec 复用的 App Server 客户端，支持进程内调用 |
| `app-server-protocol/` | 面向 App Server 客户端的请求与通知协议 |
| `core/` | Codex 核心业务逻辑与 Agent Runtime |
| `protocol/` | Core 运行时的内部操作、事件和数据类型 |
| `codex-client/`、`codex-api/`、`model-provider/` | 模型请求与提供方相关能力 |
| `exec-server/`、`sandboxing/` 等 | 环境中的命令执行与安全隔离基础设施 |
| `thread-store/`、`history/`、`state/` | 会话历史、持久化、状态支持 |

这些目录不是严格的“依赖层级”。例如，安全、配置、状态、扩展能力会被多个模块共同使用。今天只需要记住**主要职责**，不必研究所有依赖。

## 4. 从 `codex` 命令开始追踪

先打开第一个真实文件：

**[`codex-rs/cli/src/main.rs`](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/cli/src/main.rs)**

搜索关键词：

```text
Exec(ExecCli)
run_main
```

你会看到两件事：

- `codex exec` 是一个单独的非交互子命令；
- 不指定子命令时，会进入交互式 CLI/TUI 路径。

因此，`codex` 并不是“运行某个 Agent 函数”的命令，它先要**决定用户使用哪种产品入口**。

```text
codex
  └─ 交互入口 → TUI

codex exec "任务"
  └─ 非交互入口 → Exec
```

两条路径最终都可以复用 Codex 的核心业务能力。**不同入口可以有不同的交互体验，但不需要各自复制一套 Agent 核心。**

## 5. TUI 发出的请求去哪了？

打开：

**[`codex-rs/app-server-client/README.md`](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/app-server-client/README.md)**

其中明确说明，`codex-tui` 与 `codex-exec` 使用共享的进程内 App Server 客户端能力。进程内路径通过 **typed channels（类型化通道）** 传递请求与事件，而对外部 stdio/WebSocket 等传输仍可使用相应的协议序列化。

新会话典型地会发出类似：

```text
thread/start
```

已有会话则可能走：

```text
thread/resume
```

这只是一个逻辑示意：

```text
TUI / Exec
    │
    │ thread/start
    ▼
App Server 接口
    │
    ▼
Core 的 ThreadManager
```

**这里不要把 App Server 理解成“永远是单独的服务进程”。** 当前源码里存在 embedded / local daemon / remote 等接入方式；本章谈的是**服务职责边界**。

## 6. 真正管理 Agent 会话的是谁？

现在进入 Core。

第一份文件：**[`core/src/thread_manager.rs`](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/core/src/thread_manager.rs)**

搜索：

```rust
pub struct ThreadManager
```

源码注释给它的职责是：创建并在内存中维护 Thread。

第二份文件：**[`core/src/codex_thread.rs`](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/core/src/codex_thread.rs)**

搜索：

```rust
pub struct CodexThread
```

你会看到它持有 `Session`、`SessionIo` 等字段。我们先把它理解为：**一个会话的对外运行对象，负责连接输入输出与内部 Session**。

最简化关系如下：

```text
ThreadManager
    │
    ├─ CodexThread A ── Session A
    ├─ CodexThread B ── Session B
    └─ CodexThread C ── Session C
```

现在你已经找到“创建和持有会话”的位置。但会话里怎样连续请求模型和执行工具？请看下面这一行。

第三份文件：**[`core/src/session/turn.rs`](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/core/src/session/turn.rs)**

搜索：

```rust
pub(crate) async fn run_turn(
```

这是核心执行路径的重要入口。你目前**不需要读完它**，只要确认：真正处理一次任务的模型调用、工具结果和后续步骤，发生在这个 Runtime 里，而不是 TUI 组件里。

## 7. 把一次提问串起来

以“只读查看项目”为例，一条**简化的典型路径**如下：

```text
① 用户在 TUI 输入问题
        ↓
② TUI 通过 App Server 客户端提交请求
        ↓
③ ThreadManager 创建或取得会话
        ↓
④ CodexThread / Session 接收任务输入
        ↓
⑤ run_turn 组织一次模型执行
        ↓
⑥ Model Client 请求模型
        ↓
⑦ 模型可能要求执行只读工具
        ↓
⑧ Tool Runtime 在有效权限下执行并返回结果
        ↓
⑨ 模型继续处理，生成回答
        ↓
⑩ 事件传回界面，并按配置记录会话状态
```

这不是逐个 Rust 函数的精确调用栈；它刻意省略了配置加载、权限细节、流式事件、异常路径和持久化时机。**它是第一章用来建立全局认知的路线图。**

## 8. 动手实验：不改代码，验证架构

### 实验 A：认识不同入口

如果你已经安装 Codex，在终端执行：

```bash
codex --version
codex --help
codex exec --help
```

观察：`codex` 是命令入口，`exec` 是它提供的一种运行模式；这两者不是两个不同的 Agent 算法。

### 实验 B：只读追踪源码

在浏览器依次打开上述三个 Core 文件，以及 `cli/src/main.rs`。在 GitHub 页面使用搜索，依次找到：

```text
Exec(ExecCli)
ThreadManager
CodexThread
run_turn
```

把它们按顺序写成一句话：

> CLI 选择运行入口，服务层把请求交给 Core，ThreadManager 维护会话，CodexThread 连接会话，执行逻辑最终进入 run_turn。

如果你希望本地阅读，可选地浅克隆固定基线版本（不需要编译）：

```bash
git clone --filter=blob:none --no-checkout https://github.com/openai/codex.git
cd codex
git fetch --depth 1 origin 014489466a1739c2c563cdfe57880c2c7c8680e3
git checkout --detach FETCH_HEAD
```

注意：上述命令仅用于下载与阅读公开源码；**不要在原有业务项目目录直接执行**。如果克隆速度太慢，直接阅读 GitHub 文件即可。

## 9. 三个容易产生的误解

**误解一：“Codex = GPT + while True。”**

最小 Agent 可以这样实现，但 Codex 产品还必须处理客户端协议、运行状态、权限、执行环境、持久化等问题。

**误解二：“App Server 就是独立的后台进程。”**

错。它首先是职责和通信边界，当前也支持进程内运行方式。是否独立进程，要看具体入口与部署方式。

**误解三：“Thread 就是 messages 数组。”**

错。消息历史只是 Thread 相关状态的一部分；Thread 还有生命周期、配置、输入输出、关联 Session 与持久化行为。后续章节会专门拆解。

## 10. 本章验收与下一章

如果不看图，你可以用自己的话解释下面这条链，就算通过本章：

```text
CLI / TUI → App Server 接口 → ThreadManager
→ CodexThread / Session → run_turn → Model / Tools
```

**下一章：ThreadManager 与 CodexThread。** 我们从“为什么需要一个会话管理器”出发，追踪一条 `thread/start` 请求的创建路径，了解会话是怎样被创建、引用和关闭的。

---

## 本章源码索引

- [CLI 入口 `cli/src/main.rs`](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/cli/src/main.rs)
- [TUI `tui/src/lib.rs`](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/tui/src/lib.rs)
- [App Server Client 设计说明](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/app-server-client/README.md)
- [App Server `app-server/src/lib.rs`](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/app-server/src/lib.rs)
- [Core `core/src/lib.rs`](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/core/src/lib.rs)
- [ThreadManager](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/core/src/thread_manager.rs)
- [CodexThread](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/core/src/codex_thread.rs)
- [Turn Runtime](https://github.com/openai/codex/blob/014489466a1739c2c563cdfe57880c2c7c8680e3/codex-rs/core/src/session/turn.rs)
