# 归档索引

本目录存放已完成、冻结或不再维护的需求、设计、验收记录与截图，**只读**：
不新增规划、不修改历史内容；如需勘误，另开说明文件并注明原因。

活跃的需求与任务请写入 `docs-work/`，长期稳定文档整理后放入 `docs/`。

## 目录

- `assistant-capability-console-v1/`：助手能力控制台需求、部署说明与验收截图。
- `assistant-session-v1/`：助手会话 SQLite 持久化需求、计划、任务与验收记录。
- `homepage-v2/`：主页第二版需求、任务与视觉验收截图。
- `feat02-platform-v1/`：平台化需求、实施报告、差距分析与验收截图。
- `legacy-homepage-v1/`：更早的首页改造资料（V1 PRD、第一轮任务、第二轮视觉验收）。

## 约定

- 自动化测试不得写入本目录；运行报告写入 `frontend/test-results/`、`frontend/playwright-report/`，需要留存的视觉证据写入 `docs-work/evidence/<feature>/screenshots/`。
- 归档迁移使用 `git mv` 保留历史，不用复制后删除的方式。
