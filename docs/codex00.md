Part 0  Codex Architecture
  01 [Codex 是什么：整体架构与运行主线](./01-codex-architecture/README.zh.md)

Part 1  Runtime Model
  02 [ThreadManager 与 CodexThread](./02-thread-management/README.zh.md)
  03 [Session / Turn / Step](./03-session-turn-step/README.zh.md)

Part 2  Agent Core
  04 [run_turn：真正的 Agent Loop](./04-agent-loop/README.zh.md)
  05 [ModelClient：模型请求与流式响应](./05-model-client/README.zh.md)
  06 [Context：Prompt 到底怎么构建](./06-context-prompt/README.zh.md)
  07 [Tool System：Spec / Registry / Router / Handler](./07-tool-system/README.zh.md)
  08 [一次 Shell Tool 的完整执行链](./08-shell-execution/README.zh.md)

Part 3  Execution & Safety
  09 Permission / Approval / Sandbox / Exec

Part 4  State & Product Runtime
  10 Op / Event：UI 与 Core 的通信模型
  11 History / Rollout / Thread Store
  12 Token Budget / Compaction

Part 5  Capability Extensions
  A1 AGENTS.md / Skills
  A2 MCP / Plugins / Connectors
  A3 Hooks / Extension API

Part 6  Agent Systems
  A4 Multi-Agent
  A5 Memory
  A6 Guardian
  A7 Goal Runtime

Final
  一条真实 Codex 请求的完整源码追踪