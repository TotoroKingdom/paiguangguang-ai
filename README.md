# Paiguangguang AI

> **AI Agent Engineer Portfolio**
>
> Building practical AI systems around **Agent · RAG · Knowledge Systems · Full-Stack Engineering**.

这是我的个人技术主页与工程作品集仓库。


---

## ✦ Focus

```text
LLM
│
├── RAG
│   ├── Retrieval
│   ├── Rerank
│   └── Knowledge System
│
├── Agent
│   ├── Context
│   ├── Tool Use
│   ├── Memory
│   └── Workflow
│
└── Engineering
    ├── Backend
    ├── Full Stack
    ├── Deployment
    └── Observability
```

当前主要关注：

- **AI Agent Engineering（AI 智能体工程）**：Agent Runtime、Tool、Memory、Context、Workflow
- **RAG Systems（检索增强生成系统）**：Retrieval、Rerank、Knowledge Pipeline
- **Knowledge Systems（知识系统）**：企业知识库、知识治理、Ontology（本体）
- **AI Application Architecture（AI 应用架构）**：从模型能力到实际业务系统
- **Full-Stack Engineering（全栈工程）**：AI 产品的前端、后端与部署工程

---

## ✦ About This Repository

这个仓库目前承担两个角色。

### 01 / Personal Portfolio

`frontend/` 是我的个人技术主页，主要展示：

- 技术方向
- 工程经历
- AI / RAG / Agent 项目案例
- 技术路线
- 架构与工程实践


页面中的 AI、RAG、Agent 内容主要用于展示真实工程方向和历史项目经验。

### 02 / Engineering Archive

`archive/` 保存了一部分已经完成或停止维护的工程设计与实施资料。

这些内容用于记录：

```text
Problem
   ↓
Architecture
   ↓
Implementation
   ↓
Evaluation
   ↓
Iteration
```


---

## ✦ Repository Structure

```text
paiguangguang-ai/
│
├── frontend/                 # Next.js Portfolio
├── backend/                  # Minimal FastAPI service
├── deploy/                   # Production deployment
├── docs/                     # Engineering documentation
├── archive/                  # Historical engineering materials
│
├── .github/
│   └── workflows/            # CI / Deployment
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## ✦ Tech Stack

### Frontend

- Next.js
- React
- TypeScript
- CSS

### Backend

- Python
- FastAPI
- uv
- pytest

### Infrastructure

- Docker
- Docker Compose
- Nginx
- GitHub Actions
- Redis

当前 Backend（后端）保持最小化，仅承担健康检查：

```http
GET /api/v1/health
```

Response：

```json
{
  "status": "ok"
}
```

Redis 当前保留在 Docker Compose 拓扑中，但没有被线上业务消费。

---

## ✦ Local Development

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

访问：

```text
http://localhost:3000
```

### Backend

```bash
uv sync --group dev
uv run uvicorn app.main:app --app-dir backend --reload
```

Health Check：

```text
http://localhost:8000/api/v1/health
```

预期返回：

```json
{
  "status": "ok"
}
```

---

## ✦ Docker Compose

```bash
docker compose up --build
```

默认服务：

| Service | Address |
| --- | --- |
| Frontend | `http://localhost:3000` |
| Health API | `http://localhost:8000/api/v1/health` |
| Redis | `localhost:6379` |

---

## ✦ Verification

### Frontend

```bash
cd frontend
npm test
npm run lint
npm run build
```

### Backend

```bash
uv run pytest backend/tests -q
```

### Docker Compose

```bash
docker compose config --quiet
```

---

## ✦ Deployment

当前采用 `dev → main → production` 的发布流程：

```text
dev
 │
 │ Development
 ▼
Pull Request / Merge
 │
 ▼
main
 │
 │ GitHub Actions
 ▼
Production Deployment
```

分支职责：

- `dev`：日常开发与集成
- `main`：生产分支
- 只有代码合入并 push 到 `main` 后，才进入 Production（生产）部署流程

具体生产发布与 Nginx 反向代理说明见：

[deploy/README.md](deploy/README.md)

---

## ✦ Engineering Philosophy

> **How the system works, not just whether the demo works.**

```text
Model
  +
Context
  +
Retrieval
  +
Tools
  +
Memory
  +
State
  +
Permission
  +
Evaluation
  +
Observability
  +
Infrastructure
```

这些部分共同决定了一个 AI 系统是否真正具备可用性、可维护性与可扩展性。

这个仓库会持续记录我在这些方向上的实践与演进。

---

<p align="center">
  <strong>Paiguangguang AI</strong>
  <br />
  AI Agent · RAG · Knowledge Systems · Engineering
</p>
