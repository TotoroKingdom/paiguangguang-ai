# feat02 管理端 Runtime 真实性修复

## 1. 问题

管理端仍保留早期原型文案：

- 系统设置声称“未接入真实 LLM、MCP Runtime 或 Agent Loop”。
- 能力编辑器提供未接入的 HTTP/内置执行器选项，却不支持实际的 `system` 与 `mcp` 执行器。
- Agent 模型占位文案仍显示“尚未接入真实模型”。

这些文案会让管理员误判当前平台执行边界。

## 2. 修复

- 系统设置从服务端 `llm_provider` 读取实际执行模式：开发 Fake 显示 `fake`，真实适配器显示 Provider 名。
- 明确 Agent Runtime、Tool Gateway、MCP Client、Run/Step/Trace 已启用。
- 明确 Fake Provider 仅用于开发与自动化；生产必须使用真实服务端模型。
- 能力编辑器执行器改为实际支持的：
  - 内置只读 Tool
  - 已批准 MCP Tool
  - 演示执行器（仅开发）
- 内置 Tool 编辑 `tool` 标识；MCP Tool 编辑 `mcpServerId` 与 `mcpTool`。
- Agent 模型字段注明由服务端 Provider 配置决定，密钥不保存到能力配置。
- 系统设置响应不包含 Provider API Key。

## 3. 验证

- 后端新增设置真实性测试：Fake/真实 Provider 标识、Runtime 文案、API Key 不泄漏。
- 管理端 E2E 校验执行器选项与实际运行时一致，并验证系统设置不再显示“未接入”旧文案。
- 后端全量：`73 passed`。
- 前端 Vitest：`80 passed`。
- TypeScript、ESLint 与生产构建通过。

## 4. 边界

真实 Provider 调用仍为 `NOT_RUN`；本轮只修正管理端展示与管理契约，不调用收费模型。
