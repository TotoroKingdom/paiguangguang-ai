# feat02 O-03 秘密泄漏与缓存审计

> 日期：2026-11-08
> 范围：本地开发环境、自动化 API 与桌面/移动浏览器。
> 生产日志、反向代理缓存与生产浏览器样本：**NOT_RUN**。

## 1. 结论

开发环境已证明密码、恢复码和认证会话不会通过 API 响应缓存、认证错误响应、Cookie、URL 或浏览器 LocalStorage/SessionStorage 泄漏。后端自动化同时检查运行日志中不出现测试秘密。

生产环境仍未取得日志、反向代理缓存配置和真实浏览器样本，因此 O-03 保持 **PARTIAL**，不能标记生产通过。

## 2. 本轮加固

- 所有 `/api/v1/` 响应统一增加：
  - `Cache-Control: no-store, max-age=0`
  - `Pragma: no-cache`
  - `Expires: 0`
- 覆盖注册、登录、会话、恢复、改密、个人资源、管理接口与 Runtime 等动态私有数据。
- 禁止浏览器、共享代理或中间缓存保存一次性恢复码和私有响应。

## 3. 自动化证据

后端新增 `backend/tests/test_secret_leakage.py`：

- 注册、登录、会话接口均验证禁止缓存响应头。
- 注册返回的恢复码不会出现在注册响应正文、错误响应正文、Cookie 或 `caplog` 日志中。
- 正确密码、错误密码和错误恢复码均不会进入日志。
- 失败登录与失败恢复只返回通用错误语义，不泄露输入秘密。

账号 E2E 扩展 `frontend/e2e/account-v1.spec.ts`：

- 浏览器实际收到注册响应的 `Cache-Control: no-store, max-age=0` 与 `Pragma: no-cache`。
- 注册成功页 URL 不包含数字账号或恢复码。
- 恢复码不在 LocalStorage、SessionStorage 或可读 Cookie 中。
- 桌面与移动项目均执行相同断言。

## 4. 静态审查

已检索后端与前端生产代码中的日志、浏览器持久化和敏感参数使用：

- 未发现 `logger.*`、`print()` 或前端 `console.*` 输出恢复码、密码、CSRF Token 或 MCP Token。
- 前端只在 React 内存状态中暂存一次性恢复码。
- MCP Token 仅提交到连接 API，服务端以 Fernet 密文保存，列表响应不回显。
- Admin Run 列表清空 `inputText` 与 `outputText`。
- 服务端密码使用 PBKDF2，恢复码与会话 Token 使用摘要；API Key 仅从服务端配置读取。

## 5. 未执行与边界

- 未读取生产容器日志、反向代理访问日志或 CDN/代理缓存配置。
- 未在生产浏览器执行 LocalStorage、SessionStorage、URL、Cookie 抽查。
- 未验证生产日志采集器、错误追踪平台和分析埋点的脱敏规则。
- 以上项目需要生产只读访问授权，归入 F16/O-01/O-03 生产门禁。

## 6. 判定

- 开发环境 O-03 秘密泄漏自动化：**PASS**。
- 生产环境 O-03：**NOT_RUN**。
- 38 场景矩阵中 O-03 保持 **PARTIAL**，直至生产样本完成。
