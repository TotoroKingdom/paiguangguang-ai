# feat02 依赖安全审计（2026-11-08）

## 1. 结论

| 范围 | 命令 | 结果 |
|---|---|---|
| 前端生产依赖 | `npm audit --omit=dev --registry=https://registry.npmjs.org` | **0 critical / 0 high / 0 moderate / 0 low** |
| 前端全部依赖 | `npm audit --registry=https://registry.npmjs.org` | **0 critical / 0 high**；10 moderate 集中在 ESLint/TypeScript ESLint 开发工具链 |
| 后端依赖 | `pip-audit -r requirements.txt` | **No known vulnerabilities found** |

生产依赖的 critical/high 阻断已解除。仍有开发工具链 moderate 告警，不进入生产镜像，但应在后续常规升级中继续收敛。

## 2. 版本变化

| 组件 | 原版本 | 新版本 |
|---|---|---|
| Next.js | 14.2.35 | 16.4.5 |
| ESLint | 8.57 | 10.14 |
| eslint-config-next | 14.2.35 | 16.4.5 |
| Vitest | 2.1.9 | 5.1.0 |
| Vite | 5.x | 7.3.7 |
| @vitejs/plugin-react | 4.3.3 | 5.2.0 |
| @types/node | 20.11 | 22.20 |
| FastAPI | 0.116 | 0.162.2 |
| Starlette | 0.48.0 | 1.10.0 |
| cryptography | 45.0.7 | 50.0.2 |
| pytest | 8.4.2 | 9.2.0 |

## 3. Next.js 16 迁移修复

- 动态路由 `params` 改为异步：能力详情页与聊天详情页 `await params`。
- `next lint` 已移除，脚本改为 `eslint . --ext .ts,.tsx`。
- 使用 ESLint 10 flat config：`eslint.config.mjs`，删除 `.eslintrc.json`。
- 忽略 `public/threejs-lab/vendor/**` 第三方 Three.js 构建文件。
- 对旧代码中大量存在的 `react-hooks/refs`、`react-hooks/immutability`、`react-hooks/set-state-in-effect` 暂设为关闭，避免在安全升级中混入大范围行为重构；后续应单独治理。
- 根布局增加 `data-scroll-behavior="smooth"`。
- 首页与 RAG 页内部绝对链接改为 `next/link`。

## 4. 验证

- 后端：`52 passed`
- 前端 Vitest：`76 passed`
- TypeScript check：通过
- ESLint：通过（0 error）
- Next production build：29 个静态/动态路由通过
- Playwright：68 passed（桌面 + 移动）
- Alembic 迁移链不受依赖升级影响

## 5. 仍未解决

- 生产 HTTPS/TLS、反向代理、Secure Cookie、GitHub secrets 与部署权限尚未核验。
- 生产镜像仍需在 CI 通过后重新构建，并核对实际容器内 `next --version`、依赖树与健康检查。
- 开发依赖的 10 个 moderate 告警未全部修复，未进入生产依赖。
- Node 最低版本变为 20.9；CI 使用 Node 20.20 满足要求，生产构建环境需确认。

## 6. 审计命令

```powershell
cd frontend
npm audit --omit=dev --registry=https://registry.npmjs.org
npm audit fix --registry=https://registry.npmjs.org
npm ci --registry=https://registry.npmjs.org

cd ../backend
..\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```
