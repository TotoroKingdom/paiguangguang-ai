# S1-02 本地模型文件上下文证据

执行日期：2026-11-13（Asia/Shanghai）
验证对象：包含本记录的 S1-02 代码提交（文件上传、`fileIds` 传递和 Runtime 文件上下文有界读取）。合并提交和 CI 结果以对应 PR 为准。

## 环境与隔离

- 模型：本机已有 Ollama `gemma3:4b`，未执行模型下载或外部供应商请求。
- Ollama：由验证脚本临时启动在 `127.0.0.1:11543`，验证结束后终止。
- 应用：FastAPI TestClient，指向同一回环 Ollama OpenAI-compatible 接口。
- 数据：临时 SQLite 数据库、临时文件存储目录；验证完成后清理。
- 凭据：仅使用测试用本地占位值；未读取或输出真实密钥。
- 网络：清空代理环境变量并设置 `NO_PROXY=*`，请求仅发送至回环地址。

## 实际执行（最新重跑）

可重放脚本：`backend/scripts/validate_file_context_local.py`。在仓库的 `backend` 下，使用已安装项目依赖的 Python 执行：

```powershell
python scripts/validate_file_context_local.py
```

脚本会动态选择回环端口，确认本机 Ollama 标签包含 `gemma3:4b`，并将应用指向该临时 Ollama OpenAI-compatible 接口；它不执行模型下载。

1. 本机已有 `gemma3:4b`，临时 Ollama `/api/tags` 检查通过。
2. 在临时数据库建立两个 ACTIVE 测试用户。
3. 用户 A 上传 `local-fact.txt`，内容为：`LOCAL_FILE_FACT_CODE: 73142. Use this exact code when answering.`
4. 用户 A 创建对话并提交：`fileIds=[上传文件 ID]`，请求模型读取文件并回答精确代码。
5. 用户 B 使用同一文件 ID 发起请求。

## 结果

- 用户 A：HTTP `200`，Run 状态 `completed`，模型真实输出为 `73142`。
- 用户 B：HTTP `404`，错误码 `NOT_FOUND`（文件不存在/不属于当前用户），未进入模型执行。
- 脚本输出 `result PASS`，并在结束时停止临时 Ollama 进程。
- 验证结论：`PASS`。最新有界文件读取代码仍能将文件内容送入真实本地 Runtime 模型上下文，且用户归属隔离生效。

## 可复核性与限制

脚本随代码保存，使用临时 SQLite、临时文件存储和本地占位令牌，结束后清理应用数据并停止临时 Ollama。Ollama 运行日志为临时文件，不作为证据依赖。该证据只覆盖本机 Ollama 隔离联调，不代表外部供应商、生产模型、生产凭据、生产网络或付费服务已验证。

## 续做验证（2026-11-13）

- 本次重跑真实本机模型：HTTP 200、completed、输出 `73142`；跨用户 HTTP 404；脚本 PASS。
- 前端 Vitest：20 个文件，82/82；ESLint 与生产构建通过。
- 后端最终全量 pytest：133/133 通过（47.04 秒）；包含续做新增回归测试。
- Playwright 个人资源及文件附件链路：desktop/mobile 2/2。首次启动因系统 Python 缺少 sqlalchemy 失败，显式使用现有项目虚拟环境后通过。
- 桌面和窄屏附件截图：`screenshots/desktop-personal-attachment-context.png`、`screenshots/mobile-personal-attachment-context.png`；代理视觉检查可见选中文件已出现在输入框。用户人工视觉验收未执行。
- 后端新增覆盖：附件正文进入模型且不进入运行审计记录、用户隔离、文本校验、上下文预算、重试恢复及已删除文件重校验、无/伪造 Content-Length、分块请求、SSE 不被虚假断连截断。
- 无数据库迁移；未发布 main 或访问生产服务。
