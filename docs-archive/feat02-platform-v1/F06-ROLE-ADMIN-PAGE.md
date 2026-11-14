# feat02 F06 角色管理页面

## 1. 交付内容

新增 `/assistant/admin/roles`：

- 展示 V1 固定的 USER、CREATOR、ADMIN 内置角色权限矩阵。
- 复用统一用户 API 查询账号并按服务端版本并发控制分配角色。
- 角色变更必须填写原因并写入服务端审计。
- Creator 不显示管理导航；非统一管理员会话不能调用角色 API。
- 最后一名有效管理员不能被降级，自降级同样被服务端拒绝。

管理控制台导航补齐：

- `/assistant/admin/users`：用户管理。
- `/assistant/admin/roles`：角色管理。

## 2. 权限边界

- 页面只是操作入口，最终权限由 `require_unified_admin` 与 `set_role()` 服务端校验。
- 旧管理员 Cookie 不自动获得统一用户管理权限；页面会要求使用统一数字账号登录。
- 不新增角色自定义能力，避免出现前端可编辑而后端无对应授权的假功能。

## 3. 验证

- 前端 Vitest：`79 passed`。
- TypeScript：`npx tsc --noEmit` 通过。
- ESLint：`npm run lint` 通过。
- Next.js 生产构建：通过，包含 `/assistant/admin/roles`。
- Playwright：桌面/移动各 1 条新增场景，覆盖权限矩阵、管理导航、查询账号和实际角色分配。
- 后端全量：`70 passed`。
