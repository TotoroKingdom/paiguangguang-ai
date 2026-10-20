Part 0  Codex Architecture
  01 Codex 是什么：整体进程与源码地图

Part 1  Runtime Model
  02 ThreadManager 与 CodexThread
  03 Session / Turn / Step

Part 2  Agent Core
  04 run_turn：真正的 Agent Loop
  05 ModelClient：模型请求与流式响应
  06 Context：Prompt 到底怎么构建
  07 Tool System：Spec / Registry / Router / Handler
  08 一次 Shell Tool 的完整执行链

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