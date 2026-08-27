# Paiguangguang 发版操作

本项目发布个人作品集展示站与 health-only backend（仅健康检查后端）。

合并前执行：

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build

cd ..
uv run pytest backend/tests -q
docker compose -f deploy/docker-compose.yml config --quiet
```

发布后检查首页与健康接口：

```bash
curl -fsS https://www.paiguangguang.xyz/
curl -fsS https://www.paiguangguang.xyz/api/v1/health
```

第二个命令应返回 `{"status":"ok"}`。不再验收登录、管理端、RAG、Chatbot 或 Agent 页面。
