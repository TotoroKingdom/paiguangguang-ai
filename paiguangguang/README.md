# Paiguangguang AI Agent Platform

一个面向个人作品集展示的 AI Agent 应用平台。
# 常用命令
npx chromadb-admin --port 3434 --chromadb-url http://your-chromadb:8000

chroma run --host localhost --port 8002 --path ./chroma

python chroma_view.py

# 本地测试命令
uv run python -m uvicorn app.main:app --reload --env-file dev.env    

npm run dev

# 清掉cdoex启动的进程
netstat -ano | findstr :3000
taskkill /PID 12345 /F
---

# 发版命令
git commit -m "ci: deploy images from Tencent TCR"
git pull --rebase origin dev
git push origin dev

git switch main
git pull --ff-only origin main
git merge --no-ff dev -m "merge: deploy via Tencent TCR"
git push origin main
git switch dev


## 1. 项目定位

本项目不是一个简单的聊天页面，而是一个用于展示 AI 工程能力的个人作品集项目。

项目计划围绕三个方向展开：

1. 企业知识库 Agent
2. 浏览器 Agent
3. Office 自动化 Agent

v1 阶段重点是先搭建一个清晰、可运行、可扩展的工程基础。
后续 v2 阶段会优先推进企业知识库 Agent-RAG 问答能力。

---

## 2. rag流程

当前版本：`v1`

1. 用户请求 POST /query

2. 路由层：
   - get_current_user
   - rate limit: rag:query:{user_id}
   - 调用 query_for_user

3. query_for_user：
   - 检查 knowledge.query 权限
   - 构造 access_context
   - 进入 query()

4. query rewrite：
   - 用 DeepSeek，temperature=0.0
   - 要求返回 JSON
   - 得到 rewritten_queries
   - rewrite 结果写入共享缓存

5. hybrid retrieval：
   - queries = 原始问题 + rewritten_queries
   - 每个 query 跑 vector search
   - 每个 query 跑 keyword/BM25 search
   - 每个 query 跑 direct match search

6. fusion：
   - 按 (doc_id, chunk_id) 去重
   - 用 RRF 加分
   - score += 1 / (60 + rank)
   - route_scores 保留各路线原始分数
   - 最终取 fusion top_k

7. rerank：
   - 对 fusion_hits 用 rerank provider 重排
   - 使用原始 question 和 hit.text
   - top_n = len(hits)
   - 不主动删除未返回的 hits，只追加到后面

8. context assembly：
   - 从 reranked hits 里选择最终上下文
   - 生成 context_text 和 selected_sources

9. answer cache：
   - 如果命中，跳过 DeepSeek 生成
   - 如果未命中，调用 DeepSeek 生成答案

10. 返回：
   - answer
   - sources
   - rewrite
   - debug
   - cache hit 信息

---

## 3. 技术栈

### Frontend

* Next.js
* TypeScript
* Tailwind CSS
* App Router

### Backend

* Python
* FastAPI
* Pydantic
* DeepSeek OpenAI-compatible API
* Chroma
* Redis

### DevOps

* Docker
* Docker Compose

---

## 4. 项目结构

项目整体结构如下：

```text
paiguangguang/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── ...
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── services/
│   │   ├── schemas/
│   │   └── main.py
│   ├── tests/
│   ├── chroma/
│   ├── Dockerfile
│   ├── dev.env
│   ├── .env.example
│   └── ...
│
├── docker-compose.yml
├── README.md
└── docs/
```

说明：

* `frontend/`：前端项目目录
* `backend/`：后端项目目录
* `backend/app/api/`：接口路由
* `backend/app/core/`：配置、启动参数、通用基础能力
* `backend/app/services/`：业务服务层
* `backend/app/schemas/`：请求和响应数据结构
* `backend/chroma/`：本地 Chroma 数据目录
* `docker-compose.yml`：本地 Docker 编排配置
* `docs/`：项目文档

---

## 5. 环境要求

本地开发建议环境：

* Node.js 20+
* Python 3.12+
* Docker Desktop
* Docker Compose
* Git

如果使用 Docker 启动，理论上不需要手动安装 Python 依赖，但前端本地开发仍建议安装 Node.js。

---

## 6. 环境变量配置

后端环境变量示例文件位于：

```text
backend/.env.example
```

开发环境可以复制一份为：

```text
backend/dev.env
```

前端环境变量示例：

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 7. 本地启动方式

### 方式一：使用 Docker Compose 启动

在项目根目录执行：

```bash
docker compose up --build
```

启动后访问：

```text
前端：http://localhost:3000
后端：http://localhost:8000
后端接口文档：http://localhost:8000/docs
```

停止服务：

```bash
docker compose down
```

重新构建：

```bash
docker compose up --build
```

查看容器状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f
```

---

## 8. 当前页面说明

v1 阶段前端主要页面包括：

```text
/
```

首页，用于展示项目整体定位和 Agent 平台入口。

```text
/agents/knowledge
```

企业知识库 Agent 页面。v1 阶段主要作为入口页面，v2 阶段会重点实现 RAG 检索问答能力。

```text
/agents/browser
```

浏览器 Agent 页面。v1 阶段主要作为功能入口和展示页面。

```text
/agents/office
```

Office 自动化 Agent 页面。v1 阶段主要作为功能入口和展示页面。

## 9. 当前 API 说明

v1 阶段后端主要提供基础 API 骨架。

常见接口示例：

```text
GET /health
```

健康检查接口，用于确认后端服务是否正常运行。

```text
GET /api/v1/health
```

API v1 健康检查接口。

```text
POST /api/v1/chat
```

基础聊天接口，用于验证前后端请求链路和 LLM 调用链路。

请求示例：

```json
{
  "message": "你好，介绍一下这个项目"
}
```

响应示例：

```json
{
  "answer": "这是一个 AI Agent 作品集项目。"
}
```

实际接口路径和字段请以后端 `/docs` 中展示的 OpenAPI 文档为准。

---

## 10. Docker 说明

v1 阶段 Docker 主要用于本地开发和部署验证。

通常包含以下服务：

```text
frontend
backend
redis
```

其中：

* `frontend`：Next.js 前端服务
* `backend`：FastAPI 后端服务
* `redis`：用于后续会话、缓存和任务状态存储
* `chroma`：当前可采用本地目录持久化，v2 阶段会进一步完善向量数据库使用方式

如果端口冲突，可以检查 `docker-compose.yml` 中的端口映射，例如：

```yaml
ports:
  - "3000:3000"
  - "8000:8000"
  - "6379:6379"
```

---

## 11. v1 验收标准

v1 阶段完成后，需要满足以下验收标准：

### 1. 启动验收

* 前端可以正常启动
* 后端可以正常启动
* Docker Compose 可以正常启动
* 访问前端首页不报错
* 访问后端 `/docs` 不报错

### 2. 配置验收

* 环境变量不硬编码在代码中
* DeepSeek API Key 不出现在 GitHub 代码中
* `.env.example` 提供必要配置说明
* 开发环境和生产环境配置有基本区分

### 3. 接口验收

* 前端请求地址和后端接口路径一致
* 后端接口返回格式稳定
* 健康检查接口可用
* 基础聊天接口可用

### 4. 结构验收

* 前端目录结构清晰
* 后端目录结构清晰
* API、Service、Schema、Config 分层明确
* 没有大量临时代码堆在入口文件中

### 5. 文档验收

* README 指导启动项目
* README 说明了项目定位和技术栈
* README 说明了环境变量配置
* README 说明了 v1 当前能力和 v2 后续方向
---

## 6. 项目目标

本项目最终目标是作为 AI Agent 工程方向的个人作品集项目，展示从前端页面、后端 API、LLM 调用、RAG 检索、Agent 工作流到 Docker 部署的完整工程能力。

项目希望体现的不只是“会调用大模型”，而是能够展示：

* 前后端工程能力
* FastAPI 后端开发能力
* Next.js 前端开发能力
* LLM API 接入能力
* RAG 系统设计能力
* Chroma 向量数据库使用能力
* Redis 状态管理和缓存能力
* Agent 工作流设计能力
* Docker 部署能力
* 工程文档编写能力
* 面向真实业务场景的系统拆解能力
---

## 7. 开发原则

本项目后续开发遵循以下原则：

1. 每次只推进一个明确任务。
2. 不随意重构整体项目结构。
3. 不为了炫技引入过重依赖。
4. 新增功能必须保持项目可启动。
5. 后端路由保持轻量，业务逻辑放在 services 中。
6. 所有 JSON API 统一使用 `/api/v1` 前缀。
7. 涉及后端行为变化时，需要补充或更新测试。
8. 不把 API Key、Token、数据库密码等密钥写入代码。
9. README 和 roadmap 需要随着功能变化同步更新。
10. 优先完成一个稳定闭环，再扩展更多能力。
11. 优先把 Knowledge RAG 做深，再横向扩展其他 Agent。
12. 所有功能都要服务于作品集展示和求职讲解。

---

## 8. Chatbot acceptance notes

- Frontend chatbot entry: `/chat-bot`
- Supported backend API: `/api/v1/chatbot`
- Legacy compatibility route: `/api/v1/chat/chat` is deprecation-only during the migration window
- Verified locally with:
  - `pytest backend/tests -q`
  - `npm test -- --run`
  - `npm run lint`
  - `npm run build`

## 9. License

This project is for personal portfolio and learning purposes.

## 10. Chatbot operations

The Chatbot workspace is available at `/chat-bot` and its API is mounted at
`/api/v1/chatbot`. Before deploying a backend revision, apply the database
migrations from the `backend` directory:

```bash
alembic upgrade head
```

The durable job worker starts with the FastAPI application. It recovers queued
or interrupted title, cleanup, and post-completion jobs after a restart. Redis
is used as an optimization for live coordination; transient Redis failures
degrade to the database-backed path instead of taking the Chatbot API offline.

Emergency feature flags:

```env
# Backend: returns 503 CHATBOT_DISABLED for all Chatbot API routes when false.
CHATBOT_ENABLED=true

# Frontend: hides the navigation entry and makes /chat-bot return not found when false.
NEXT_PUBLIC_CHATBOT_ENABLED=true
```

Set both flags to `false` for a complete rollback at the product boundary. The
frontend value is embedded at build time, so rebuild/redeploy the frontend after
changing it. The backend value requires an application restart.

Useful verification commands:

```bash
# backend (from the repository root)
pytest backend/tests/chatbot -q

# frontend
cd frontend
npm test
npm run lint
npm run build
```

## 11. Production deployment

The current production design uses GitHub Actions to publish immutable frontend
and backend images to GHCR. An existing Nginx container exposes the application
at `http://1.12.47.29:8080`, Neon provides PostgreSQL, and Redis plus Chroma use
persistent Docker volumes.

- Server setup and operations: [`deploy/README.md`](deploy/README.md)
- Architecture design: [`docs/superpowers/specs/2026-07-17-server-deployment-design.md`](archive/superpowers/specs/2026-07-17-server-deployment-design.md)
- Implementation plan: [`docs/superpowers/plans/2026-07-17-ghcr-single-server-deployment.md`](archive/superpowers/plans/2026-07-17-ghcr-single-server-deployment.md)
