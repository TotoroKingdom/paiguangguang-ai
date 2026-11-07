# 验收记录

## 1. 访问地址

| 产品面 | 地址 |
| --- | --- |
| 个人网站 | `/`、`/rag`、`/lab/3d`、`/threejs` |
| 用户工作台 | `/assistant`、`/assistant/chat/:id`、`/assistant/tools`、`/assistant/skills`、`/assistant/mcp`、`/assistant/agents`、`/assistant/files` |
| 管理员登录 | `/assistant/admin/login` |
| 管理控制台 | `/assistant/admin`、`/assistant/admin/tools`、`/assistant/admin/skills`、`/assistant/admin/mcp`、`/assistant/admin/agents`、`/assistant/admin/releases`、`/assistant/admin/runs`、`/assistant/admin/settings` |
| 统一能力详情 | `/assistant/admin/capabilities/:id` |

## 2. 自动化验证

最终验证命令与结果记录在本节。自动测试不等同于人工验收。

### 后端

```text
python -m pytest backend/tests -q
20 passed
```

覆盖：

- 管理员登录、会话、退出、Cookie 属性与密码哈希。
- 管理员会话过期后返回 `401`。
- 无管理员权限、无 CSRF、错误 Origin 的拒绝。
- 登录失败限流。
- 能力草稿创建、发布、编辑隔离、二次发布、停用。
- 公开目录不暴露未发布草稿和管理端配置。
- 用户在聊天中使用未发布/停用/不存在能力时返回 `422`。
- 服务端真实记录能力准入运行。
- 既有会话创建、分页、搜索、重命名、删除、停止/重试与浏览器隔离。

### 数据库迁移

```text
alembic upgrade head
alembic downgrade base
```

升级后表：

```text
admin_sessions, admin_users, alembic_version, audit_events,
capability_definitions, capability_dependencies, capability_runs,
capability_versions, conversations, messages
```

降级后仅保留 `alembic_version`。

### 前端

```text
npm test
19 test files / 76 tests passed

npm run lint
No ESLint warnings or errors

npm run build
Compiled successfully; 24 routes generated
```

### Playwright

```text
npx playwright test
64 passed
```

覆盖桌面与移动端：

- 个人网站、RAG、3D、Three.js 与全部既有 Assistant URL 回归。
- 匿名访问管理页被重定向；匿名管理 API 返回 `401`。
- 管理员安全登录、账户头像菜单仅在管理员会话下显示「管理控制台」。
- 创建工具草稿、保存、发布 v1、用户目录可见。
- 编辑已发布能力生成 v2 草稿，用户目录仍显示 v1。
- 发布 v2 后用户目录切换为新版本。
- 停用后用户目录不再显示，新的服务端调用被拒绝。
- 既有聊天、停止/重试、附件、技能导入、MCP 模拟连接与移动端抽屉回归。

## 3. 视觉证据

截图由 Playwright 在真实服务端与浏览器中生成：

- [桌面管理员登录](screenshots/desktop-admin-login.png)
- [桌面总览仪表盘](screenshots/desktop-admin-dashboard.png)
- [桌面工具管理列表](screenshots/desktop-admin-tools-list.png)
- [桌面能力详情](screenshots/desktop-admin-capability-detail.png)
- [桌面用户目录中的已发布能力](screenshots/desktop-workspace-published-capability.png)
- [桌面用户工作台的管理员入口](screenshots/desktop-workspace-admin-menu.png)
- [移动管理员登录](screenshots/mobile-admin-login.png)
- [移动总览仪表盘](screenshots/mobile-admin-dashboard.png)
- [移动工具管理列表](screenshots/mobile-admin-tools-list.png)
- [移动能力详情](screenshots/mobile-admin-capability-detail.png)
- [移动用户目录中的已发布能力](screenshots/mobile-workspace-published-capability.png)
- [移动用户工作台的管理员入口](screenshots/mobile-workspace-admin-menu.png)

视觉检查结论：

- 桌面管理端保持完整 Sidebar、搜索/筛选、资源详情与管理操作层级。
- 移动端 Sidebar 收入抽屉，内容单列展示，无页面级横向滚动。
- 管理端视觉延续浅色拟态面板与蓝色强调色，但信息密度高于用户工作台。
- 用户工作台保留原有视觉与交互，不继承管理端导航。

## 4. 人工验收状态

**未完成人工验收。** 本次完成的是自动测试、构建与截图视觉检查；产品负责人对交互、文案与权限策略的最终接受仍需单独进行。

未覆盖：

- 真实 HTTPS 反向代理下的 Secure Cookie 与 Origin 行为。
- 生产 GitHub Actions 密钥、服务器部署与真实回滚演练。
- 人工跨设备、跨浏览器与可访问性工具审计。
- 真实 LLM、MCP 与 Agent Runtime 行为。
