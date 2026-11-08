# feat02 F16 生产发布安全预检

> 日期：2026-11-08
> 性质：**本地静态预检与发布门禁清单**；生产服务器、DNS、证书、GitHub secrets 和实际容器未核验。
> 结论：**F16 = BLOCKED**。代码与 Compose 已加入 fail-fast，但不能替代生产实测。

## 1. 已在代码/配置中完成的检查

| 项目 | 状态 | 证据 |
|---|---|---|
| 生产禁止 Demo 目录 | PASS（代码） | `demo_catalog_enabled=true` 时 `validate_runtime()` 抛错 |
| 生产禁止 fake LLM | PASS（代码） | `llm_provider=fake/test` 启动失败 |
| 生产必须配置 LLM Base/Model/Key | PASS（代码） | 缺失时启动失败 |
| 生产 Cookie Secure | PASS（代码） | owner/admin/user 三类 Cookie 均要求 Secure |
| 生产 Origin 必须 HTTPS | PASS（代码） | 非 `https://` 的 `ASSISTANT_ALLOWED_ORIGINS` 启动失败 |
| CSRF + Origin | PASS（代码 + L1） | 登录态写操作校验 `X-CSRF-Token` 与 Origin |
| 恢复码/密码/Token 摘要或密文 | PASS（代码 + L1） | PBKDF2、HMAC、Fernet；无明文响应 |
| 文件正文持久化路径 | PASS（Compose） | `ASSISTANT_FILE_STORAGE_DIR=/data/user-files`，位于 `assistant_data` 卷 |
| SQLite 备份 API | PASS（工作流代码） | `deploy.yml` 使用 `sqlite3.backup()` |
| 发布失败回滚旧镜像 | PASS（工作流代码） | 保存旧 Compose/镜像并回滚 |
| 依赖 critical/high | PASS（本地） | `npm audit --omit=dev` 0；`pip-audit` 无已知漏洞 |
| 本地迁移/恢复/回退 | PASS（本地副本） | F00 演练：9/4/1 计数不变，摘要逐字复制 |

新增 Compose 必需变量：

```text
ASSISTANT_LLM_PROVIDER
ASSISTANT_LLM_BASE_URL
ASSISTANT_LLM_MODEL
ASSISTANT_LLM_API_KEY
```

这意味着**缺少真实模型配置时生产容器会拒绝启动**，不会静默使用 Fake Provider。

## 2. 必须在生产环境核验

| ID | 项目 | 状态 | 备注 |
|---|---|---|---|
| P-01 | 公网 HTTPS/443 与证书链 | NOT_VERIFIED | PR #11 历史记录显示仅有 80/HTTP |
| P-02 | 反向代理 `X-Forwarded-Proto`、Host、Origin | NOT_VERIFIED | 需实际请求验证 |
| P-03 | GitHub `ASSISTANT_OWNER_COOKIE_SECRET` | NOT_VERIFIED | 只验证存在性与权限，不打印值 |
| P-04 | GitHub `ASSISTANT_ALLOWED_ORIGINS` | NOT_VERIFIED | 必须为正式 HTTPS 域名 |
| P-05 | LLM Base/Model/Key | NOT_VERIFIED | 需批准供应商、预算与只读测试调用 |
| P-06 | 部署账号非交互 sudo / 证书管理 | NOT_VERIFIED | PR #11 历史记录显示不可用 |
| P-07 | 生产 SQLite revision、表计数、Admin 数量 | NOT_VERIFIED | 需只读盘点 |
| P-08 | 生产备份恢复与旧管理员登录 | NOT_VERIFIED | 需独立副本演练 |
| P-09 | 容器内实际依赖树与镜像 SHA | NOT_VERIFIED | 需部署后 `npm list`/`pip freeze` |
| P-10 | 生产文件卷容量、权限、备份 | NOT_VERIFIED | `/data/user-files` 与 DB 同卷 |

## 3. 发布顺序（必须全部满足）

1. `dev` CI 全绿，PR 审核完成。
2. 生产只读预检：磁盘、容器、卷、revision、备份清单、TLS、Origin、镜像。
3. 生成 SQLite 一致快照，记录 SHA-256 与大小，复制到独立目录。
4. 在隔离副本执行 `alembic upgrade head`、旧管理员登录、旧匿名会话计数核对。
5. 配置真实 LLM Key/Base/Model 与 HTTPS Origin；禁止 Fake Provider。
6. 合并 `dev → main` 触发部署；观察双容器健康检查与公开 HTTPS 健康检查。
7. 生产烟测：同源 API、注册、Pending、管理员激活、登录、会话创建、消息持久化、刷新恢复、文件上传/下载、容器重启后数据保留。
8. 任一失败：停止新写入，恢复旧镜像与旧 Compose；schema 不兼容时恢复迁移前快照。

## 4. 回滚边界

- 代码：回退到上一稳定镜像与 Compose。
- 数据：先停写，确认目标卷，再恢复迁移前快照。
- 禁止：`docker compose down -v`、删除命名卷、删除生产用户数据、直接 `downgrade` 后继续写入。
- 已写入的新用户/消息不能通过删表“回滚”，只能恢复到一致快照并声明数据丢失窗口。

## 5. 未解决阻断

- 生产 HTTPS/TLS/443 与证书。
- GitHub secrets/variables 与部署账号权限。
- 真实 LLM 密钥与预算批准。
- 真实 MCP Server 与真实模型联调。
- 生产备份恢复演练、旧管理员真实登录、容器重启数据保留。
- 生产镜像内依赖树/漏洞扫描复核。

在上述证据齐备之前，F16/G4 与 `main` 发布保持 **BLOCKED**。
