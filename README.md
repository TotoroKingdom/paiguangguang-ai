````
<div align="center">

# ✦ Paiguangguang AI Platform

**面向真实业务场景的全栈 AI Agent 实践平台**

将知识检索、智能对话、工具调用与权限管理整合为可运行、可扩展的 AI 应用。

![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?style=flat-square&logo=fastapi)
![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-4D6BFE?style=flat-square)
![Docker](https://img.shields.io/badge/Deploy-Docker-2496ED?style=flat-square&logo=docker)

</div>

---

## 🌌 项目简介

Paiguangguang 是一个用于探索 **RAG 工程、Agent 工作流与全栈 AI 应用开发** 的个人项目。平台以知识库与智能对话为核心，同时提供浏览器 Agent、Office Agent、后台管理和 RBAC 权限体系，完整覆盖从模型接入到产品交付的实践链路。

## ✨ 核心能力

- **知识库 Agent**：文档入库、混合检索、重排、上下文组装与来源引用
- **智能 Chatbot**：流式对话、会话管理、长短期记忆与异常恢复
- **工具型 Agent**：浏览器搜索、信息整合与办公自动化工作流
- **平台化管理**：用户认证、角色权限、工作空间及文档生命周期管理

## 🧩 技术架构

```text
Next.js · TypeScript · Tailwind CSS
                 ↓
          FastAPI · DeepSeek
                 ↓
PostgreSQL · Redis · ChromaDB
```

## 🚀 快速启动

准备 `backend/dev.env` 与 `frontend/.env.local` 后，在项目根目录执行：

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| Web 应用 | http://localhost:3000 |
| API 服务 | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

## 📁 目录结构

```text
paiguangguang/
├─ frontend/   # Next.js 前端与交互界面
├─ backend/    # FastAPI、RAG、Agent 与权限服务
├─ deploy/     # 部署配置
└─ docs/       # 项目文档
```

---

<div align="center">

**让 AI 不只回答问题，更能理解上下文、调用工具并完成任务。**

</div>
````
