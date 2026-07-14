# Chatbot 1–10 缺陷修复执行索引

> 设计依据：`docs/superpowers/specs/2026-07-14-chatbot-refactor-defect-remediation-design.md`  
> 执行方式：使用 `superpowers:executing-plans` 在当前任务分批执行，或使用 `superpowers:subagent-driven-development` 逐 Task 执行并在 Task 间复核。  
> 工作区要求：开始实施前使用 `superpowers:using-git-worktrees` 创建隔离 worktree；不要把当前用户的无关改动带入 commit。

## 固定执行顺序

1. `2026-07-14-chatbot-phase-a-frontend-stream-correctness.md`
   - 缺陷 1–3。
   - 不含数据库迁移。
   - Gate：前端完整 tests、lint、build 全部通过。
2. `2026-07-14-chatbot-phase-b-durable-reliability.md`
   - 缺陷 4–7，以及缺陷 10 的 durable auto-title 基础。
   - 新增 Alembic `0007_create_chatbot_jobs`。
   - Gate：`backend/tests/chatbot` 全部通过且 migration 只有一个 head。
3. `2026-07-14-chatbot-phase-c-contract-and-stream-performance.md`
   - 缺陷 8–9。
   - 依赖 Phase B durable job，不能提前执行 terminal-latency Task。
   - Gate：前端 Chatbot tests、后端 stream/API tests、lint、build 全部通过。
4. `2026-07-14-chatbot-phase-d-product-completeness.md`
   - 缺陷 10 的 UI、flag、logout、scroll 和文档。
   - Gate：完整前后端测试、lint、build、OpenAPI assertion 全部通过。

## Codex 每个 Task 的执行协议

1. 读取当前 Task 的 Files、Interfaces 和 Global Constraints。
2. 运行该 Task 的失败测试，保存失败原因；若测试意外通过，先确认缺陷是否已被其他提交修复，不盲目改代码。
3. 只实现该 Task 指定的最小改动。
4. 运行该 Task 的 targeted tests。
5. 运行 `git diff --check` 并确认没有无关文件。
6. 只有 targeted tests 通过后才创建该 Task 的 commit。
7. 阶段 Gate 失败时留在当前阶段修复，不进入下一份计划。

## 跨阶段不变量

- 不修改或提交真实 API key、JWT secret、数据库密码、Redis credential。
- 不创建 deleted Conversation Trash/restore API。
- 不把 Redis lease 当成唯一并发保障。
- 不在 terminal SSE 前同步执行摘要、长期记忆、Chroma 或清理。
- 不在 logout 后保留用户 Chatbot sessionStorage。
- 不使用 `git reset --hard`、`git checkout --` 或其他破坏用户工作区的命令。

## 最终完成条件

- 缺陷 1–10 在设计文档测试矩阵中均有自动化覆盖。
- 后端 `backend/tests/chatbot` 0 failed。
- 前端 `npm test`、`npm run lint`、`npm run build` 均退出码 0。
- OpenAPI 只暴露 `/api/v1/chatbot/conversations`，不暴露 `/api/v1/conversations`。
- `git diff --check` 退出码 0，git status 不包含意外生成的 Chroma、SQLite、`.next` 或环境秘密改动。
