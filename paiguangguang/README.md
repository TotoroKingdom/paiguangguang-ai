# Paiguangguang AI Agent Platform

一个面向个人作品集展示的 AI Agent 应用平台。

当前版本为 **v1 阶段**，主要目标是完成项目基础架构、前后端联通、基础 Agent 页面、后端 API 骨架、Docker 本地运行环境，
为后续 v2 阶段的企业知识库 Agent、RAG 检索问答、Redis 会话缓存等能力打基础。

---

## 1. 项目定位

本项目不是一个简单的聊天页面，而是一个用于展示 AI 工程能力的个人作品集项目。

项目计划围绕三个方向展开：

1. 企业知识库 Agent
2. 浏览器 Agent
3. Office 自动化 Agent

v1 阶段重点是先搭建一个清晰、可运行、可扩展的工程基础。
后续 v2 阶段会优先推进企业知识库 Agent-RAG 问答能力。

---

## 2. 当前版本状态

当前版本：`v1`

v1 阶段已完成的主要内容：

* 前端基础项目结构
* 后端 FastAPI 项目结构
* 前后端基础联通
* Agent 页面入口
* 后端 API 路由骨架
* DeepSeek API 配置预留
* Chroma 向量数据库目录预留
* Redis 配置预留
* Dockerfile 配置
* Docker Compose 本地启动配置
* 开发环境变量配置示例

v1 阶段的核心目标是：**确保项目可以稳定启动、可以展示基础页面、可以作为 v2 的开发基座。**

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
* `docs/`：项目文档和架构说明

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

示例配置：

```env
APP_NAME=Paiguangguang Backend
API_V1_PREFIX=/api/v1

DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_CHAT_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=30

CHROMA_PATH=./chroma
RAG_COLLECTION_NAME=portfolio_knowledge

REDIS_URL=redis://redis:6379/0

CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

前端环境变量示例：

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

注意：

* 不要把真实的 `DEEPSEEK_API_KEY` 提交到 GitHub。
* `.env`、`dev.env`、`pro.env` 等真实配置文件应该加入 `.gitignore`。
* `.env.example` 只保留示例值，不要写真实密钥。

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

### 方式二：前后端分别启动

#### 启动后端

进入后端目录：

```bash
cd backend
```

安装依赖：

```bash
pip install -r requirements.txt
```

启动 FastAPI：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问后端接口文档：

```text
http://localhost:8000/docs
```

---

#### 启动前端

进入前端目录：

```bash
cd frontend
```

安装依赖：

```bash
npm install
```

启动开发服务：

```bash
npm run dev
```

访问前端页面：

```text
http://localhost:3000
```

---

## 8. 当前页面说明

v1 阶段前端主要页面包括：

```text
/
```

首页，用于展示项目整体定位、Agent 平台入口和架构说明入口。

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

```text
/architecture
```

架构说明页面，用于展示项目整体架构、前后端关系、Agent 调用流程和后续规划。

---

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
## 12. v1 已完成能力

当前 v1 阶段已经完成了项目的基础闭环,已经具备了一个可运行、可展示、可继续扩展的 AI Agent 作品集雏形。

v1 已完成的核心模块包括：

* Home 个人问答页面
* Knowledge 企业知识库 RAG 页面
* Browser Agent 页面
* Office Agent 页面
* Architecture 架构可视化页面
* FastAPI 后端 API 骨架
* DeepSeek API 调用封装
* Chroma 向量检索基础能力
* Redis 集成
* 前后端 API 联通
* Docker 本地开发环境
* 基础错误处理和加载状态
* 基础响应结构封装

v1 已经能“项目能演示”。可以通过前端页面体验不同 Agent 模块，也可以通过后端接口验证主要能力是否可用。

---

## 13. 当前模块说明

### 13.1 Home：个人问答

Home 页面用于展示个人作品集问答能力。

该模块的目标是让访问者可以通过对话方式了解项目作者的技术背景、项目经历、AI Agent 学习路线和作品集定位。

当前能力包括：

* 用户输入问题
* 前端调用 Portfolio Chat API
* 后端调用 DeepSeek 生成回答
* 支持基础会话能力
* 返回个人作品集相关回答

---

### 13.2 Knowledge：企业知识库 RAG

Knowledge 页面是当前项目最核心的 AI 工程能力展示模块。

该模块用于演示企业知识库 Agent 的基础 RAG 流程，包括文本录入、文档切分、向量存储、问题检索、上下文组装、LLM 回答和来源展示。

当前能力包括：

* 支持文本录入
* 支持文档 ingest
* 支持文本 chunk 切分
* 支持 Chroma 向量存储
* 支持基于问题的相似度检索
* 支持调用 DeepSeek 生成回答
* 支持展示 sources / citations
* 支持基础错误状态和加载状态

该模块展示的是一个最小可用 RAG 闭环。后续 v2 阶段会重点围绕该模块做工程化增强，例如更好的文档管理、引用展示、检索质量优化、会话记忆、权限隔离和评测能力。

---

### 13.3 Browser Agent

Browser Agent 页面用于展示浏览器研究型 Agent 的产品形态。

当前阶段该模块主要用于模拟浏览器研究工作流，不直接接入真实浏览器自动化，也不依赖外部搜索 API。

当前能力包括：

* 用户输入研究任务
* 后端生成执行计划
* 返回模拟搜索步骤
* 展示中间执行过程
* 展示最终总结结果

该模块的目标是展示 Agent 的任务拆解和工具调用思路，而不是在 v1 阶段实现真实浏览器控制。后续可以继续扩展为真实搜索、网页读取、信息抽取和报告生成能力。

---

### 13.4 Office Agent

Office Agent 页面用于展示办公自动化 Agent 的产品形态。

当前阶段该模块主要用于模拟 Office 工作流，例如生成报告、总结数据、撰写邮件等，不直接修改真实 Office 文件。

当前能力包括：

* 用户选择或输入办公任务
* 后端模拟工具调用流程
* 展示 step-by-step 执行步骤
* 返回结构化最终结果
* 支持基础错误处理

该模块的目标是展示 Office 自动化 Agent 的工作流设计能力。后续可以继续扩展为真实文档解析、Excel 数据分析、Word 报告生成、邮件草稿生成等能力。

---

### 13.5 Architecture：架构可视化

Architecture 页面用于展示当前项目的系统架构。

当前能力包括：

* 前端请求架构图数据
* 后端返回节点和边数据
* 前端渲染架构关系
* 支持节点信息展示
* 展示前端、后端、LLM、RAG、Redis、Agent 模块之间的关系

该页面的目标是让项目不仅能运行，还能被清楚地讲解。对于作品集项目来说，架构可视化可以帮助面试官快速理解系统设计，而不是只看到页面效果。

---

## 14. Redis 集成说明

当前项目已经集成 Redis。

Redis 在 v1 阶段主要作为后续 Agent 工程化能力的基础设施，适合用于以下场景：

* 会话状态存储
* Agent 任务状态存储
* 长任务执行进度记录
* 缓存 LLM 调用结果
* 缓存 RAG 查询结果
* SSE 事件流状态管理
* 后续任务队列或异步任务扩展

当前 v1 阶段不要求 Redis 承担完整生产级队列能力，但 Redis 的接入为后续 v2 做长任务、任务状态查询、事件流推送和缓存优化打下了基础。


## 15. v1 已知限制

虽然 v1 已经完成了基本功能闭环，但它仍然是一个作品集项目的早期版本，还不是生产级系统。

当前已知限制包括：

* RAG 检索策略仍然较基础
* 文档管理能力较弱
* 暂未支持复杂文件格式解析
* 暂未支持 PDF、Word、Excel 等真实文件的完整解析
* RAG 暂未加入 rerank
* RAG 暂未加入 query rewrite
* RAG 暂未加入混合检索
* RAG 暂未加入权限隔离
* Browser Agent 仍是 mock workflow
* Browser Agent 暂未接入真实搜索和网页读取
* Office Agent 仍是 mock workflow
* Office Agent 暂未接入真实 Office 文件操作
* Agent 执行流程暂未完全异步化
* SSE 事件流能力仍需进一步完善
* 暂未加入用户登录和权限系统
* 暂未加入完整生产部署方案
* 暂未加入系统级评测和监控

---

## 16. v2 规划方向

v2 阶段不建议继续盲目堆新页面，而应该围绕现有 v1 做工程化增强。

v2 的核心目标是：

**把当前可演示的 AI Agent 项目，升级为更接近真实业务场景的 AI 工程作品。**

v2 建议优先围绕 Knowledge RAG 模块推进，因为它最能体现 AI Agent 工程能力，也最适合作为求职作品讲解。

---

### 17.1 Knowledge RAG 增强

v2 阶段建议优先增强 Knowledge 模块。

重点方向包括：

* 支持真实文件上传
* 支持 PDF 文本解析
* 支持 Word 文档解析
* 支持 Markdown 文档解析
* 支持文档列表管理
* 支持删除文档
* 支持按 collection 管理知识库
* 支持 chunk metadata 展示
* 支持更清晰的引用来源展示
* 支持 top_k 参数调整
* 支持无检索结果时的友好提示
* 支持 RAG prompt 优化
* 支持 query rewrite
* 支持 rerank
* 支持混合检索
* 支持基础 RAG 评测样例

这一部分是 v2 最值得优先投入的方向。因为它能直接展示你对 RAG 系统的理解，而不仅仅是会调用 LLM API。

---

### 17.2 Redis 与任务状态增强

当前项目已经集成 Redis，v2 可以继续把 Redis 用得更真实。

重点方向包括：

* 使用 Redis 保存会话历史
* 使用 Redis 保存 Agent 任务状态
* 使用 Redis 保存任务执行事件
* 使用 Redis 缓存高频问答结果
* 使用 Redis 缓存 RAG 检索结果
* 为 Browser 和 Office Agent 增加 task_id
* 支持任务状态查询
* 支持长任务进度展示
* 支持 SSE 事件流推送

这一部分可以让项目从“同步请求响应”升级为“更像真实 Agent 应用”的任务执行模式。

---

### 17.3 Browser Agent 增强

Browser Agent 在 v1 阶段已经完成基础页面和 mock workflow。v2 可以逐步增强为更真实的研究型 Agent。

可选方向包括：

* 接入真实搜索 API
* 支持网页内容读取
* 支持网页摘要
* 支持多来源信息整理
* 支持生成研究报告
* 支持展示引用链接
* 支持任务执行步骤可视化
* 支持失败重试和错误提示

该模块不建议在 v2 初期做得过重。优先级应该低于 Knowledge RAG，除非项目目标转向浏览器自动化。

---

### 17.4 Office Agent 增强

Office Agent 在 v1 阶段已经完成基础页面和 mock workflow。v2 可以逐步增强为真实办公自动化能力。

可选方向包括：

* 支持上传文本或表格数据
* 支持生成邮件草稿
* 支持生成结构化报告
* 支持总结表格数据
* 支持导出 Markdown 报告
* 支持导出 Word 文档
* 支持更清晰的工具调用步骤
* 支持任务执行结果预览

该模块适合作为展示“Agent + 工具调用 + 办公场景”的辅助模块，但不建议优先级超过 Knowledge RAG。

---

### 17.5 Architecture 页面增强

Architecture 页面在 v1 阶段已经完成基础展示。v2 可以继续增强它的讲解能力。

可选方向包括：

* 展示 RAG 调用链路
* 展示 Agent 执行链路
* 展示 Redis 在任务状态中的作用
* 展示 Chroma 在知识库中的作用
* 展示 DeepSeek 调用链路
* 展示前后端 API 交互流程
* 为每个节点增加更详细说明
* 增加“当前已完成 / 后续规划”标记

这个页面对求职作品很重要。它可以帮助你在面试中讲清楚系统，而不是只展示页面效果。

---

## 18. v2 推荐优先级

v2 建议按照以下顺序推进：

第一优先级是 Knowledge RAG 工程化增强。这个模块最能体现 AI 工程能力，也最适合写进简历和面试项目介绍。

第二优先级是 Redis 任务状态和 SSE。这个能力可以让 Browser Agent、Office Agent 和后续长任务都具备更真实的工程形态。

第三优先级是 Architecture 页面增强。它可以让项目更容易被讲清楚，也能提升作品集展示效果。

第四优先级是 Browser Agent 接入真实搜索或网页读取。这个方向很有展示价值，但复杂度和不稳定性会更高。

第五优先级是 Office Agent 接入真实文件处理。这个方向适合后续扩展，但不适合作为 v2 的第一重点。

推荐 v2 路线如下：

```text
v2.1：Knowledge RAG 文件上传与文档管理
v2.2：RAG 引用来源、检索参数、Prompt 优化
v2.3：Redis 会话历史、任务状态、SSE 事件流
v2.4：Architecture 页面增强
v2.5：Browser Agent 真实搜索能力
v2.6：Office Agent 文件处理能力
```

---

## 19. 项目目标

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

## 20. 开发原则

本项目后续开发遵循以下原则：

1. 每次只推进一个明确任务。
2. 不随意重构整体架构。
3. 不为了炫技引入过重依赖。
4. 新增功能必须保持项目可启动。
5. 后端路由保持轻量，业务逻辑放在 services 中。
6. 所有 JSON API 统一使用 `/api/v1` 前缀。
7. 涉及后端行为变化时，需要补充或更新测试。
8. 不把 API Key、Token、数据库密码等密钥写入代码。
9. README、architecture、roadmap 需要随着功能变化同步更新。
10. 优先完成一个稳定闭环，再扩展更多能力。
11. 优先把 Knowledge RAG 做深，再横向扩展其他 Agent。
12. 所有功能都要服务于作品集展示和求职讲解。

---

## 21. License

This project is for personal portfolio and learning purposes.
