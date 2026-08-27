# Pai Guangguang Portfolio

这是一个个人技术名片与作品集展示站。首页呈现 AI、RAG（检索增强生成）、Agent（智能体）和全栈工程经历；这些内容是案例说明，不提供在线登录、管理、聊天、知识库或 Agent 业务功能。

## 运行结构

- `frontend/`：Next.js 展示站。
- `backend/`：最小 FastAPI 健康检查服务，仅提供 `GET /api/v1/health`。
- `redis`：保留在 Docker Compose 拓扑中，当前不被应用业务消费。
- `archive/`：已完成的业务系统设计与实施资料，仅作历史工程证据，不代表线上能力。

## 本地开发

前端：

```bash
cd frontend
npm ci
npm run dev
```

后端：

```bash
uv sync --group dev
uv run pytest backend/tests -q
uv run uvicorn app.main:app --app-dir backend --reload
```

访问 `http://localhost:8000/api/v1/health` 应返回：

```json
{"status":"ok"}
```

## Docker Compose

```bash
docker compose up --build
```

- 前端：`http://localhost:3000`
- Health API：`http://localhost:8000/api/v1/health`
- Redis：`localhost:6379`

## 验证

```bash
cd frontend
npm test
npm run lint
npm run build

cd ..
uv run pytest backend/tests -q
docker compose config --quiet
```

生产发布和 Nginx 反向代理说明见 [deploy/README.md](deploy/README.md)。
