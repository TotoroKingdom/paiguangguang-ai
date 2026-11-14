# feat02 F12 Creator MCP Server 提交

## 1. 交付内容

创作中心新增“提交 MCP Server”：

- Creator 可填写名称、说明、HTTPS 地址和传输方式。
- 服务端强制创建 `pending` 状态，Creator 不能自行批准。
- Admin 使用独立 MCP 治理页完成批准、停用和工具发现。
- 普通用户目录只返回 `approved` Server。
- 地址继续经过 DNS/IP 校验，拒绝内网、回环、保留地址与 URL 凭据。

## 2. 验证

- Playwright 新增 Creator UI 提交 → 服务端 `pending` → Admin API 批准 → 用户目录可见。
- 桌面与移动共 2 条通过。
- 前端 Vitest、TypeScript、ESLint 与生产构建通过。
- 后端仍为 `73 passed`。

## 3. 边界

真实外部 MCP Server 联调仍为 `NOT_RUN`；本轮只验证平台审批与可见性闭环，不访问未知外部服务。
