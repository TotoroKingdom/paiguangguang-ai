# ✦ Paiguangguang AI Platform

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

## 🚀 Todo

- [ ] 分布式系统的查询链路
- [ ] 分布式系统的更新链路
- [ ] 记忆系统链路
- [ ] Muti-Agent编排链路

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
