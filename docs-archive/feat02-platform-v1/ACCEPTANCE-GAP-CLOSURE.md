# feat02 非外部验收缺口收口

## 1. 范围

本轮只补本地可验证的失败路径和浏览器证据，不改变真实模型、外部 MCP 或生产门禁结论。

## 2. 新增证据

### 恢复码

- 注册成功页刷新后显示“恢复码已不可再次查看”，DOM 中不再存在恢复码。
- 个人中心轮换恢复码后检查 URL、Cookie、LocalStorage、SessionStorage 均无明文。
- 个人中心刷新后恢复码消失，页面不会从接口重新取回。

### 个人文件与匿名认领

- 独立浏览器上下文登录同一账号后，可列出并下载已持久化的文件正文。
- 同一匿名 Owner 重复认领返回 `claimed=0`，不重复导入或破坏归属。

### 能力治理

- 能力被驳回后可重新编辑、测试并提交审核。
- Agent 锁定依赖停用后，新 Run 返回 `AGENT_DEPENDENCY_UNAVAILABLE`；旧 Run 保持 `completed`。
- MCP 个人连接删除后，新 Run 返回 `MCP_CONNECTION_REQUIRED`；现有测试已覆盖，不属于外部联调。

## 3. 验证

- 后端：`73 passed`。
- 前端 Vitest：`80 passed`。
- 账号与个人资源 E2E：桌面/移动共 4 条通过。
- 全量 Playwright：`80 passed`。

## 4. 未关闭

- 真实模型和真实外部 MCP 仍 `BLOCKED / NOT_RUN`。
- 生产日志、TLS、备份恢复仍 `NOT_RUN`。
- 管理员辅助重置仍等待 Q-02 核验 SOP。
- 等待授权/审批 Run 状态仍等待产品与安全协议。
