# Repository Guidelines

## 项目结构与模块组织

- `frontend/src/app/`：Next.js App Router（应用路由）、布局及全局样式。
- `frontend/src/app/lab/3d/`：3D 交互实验室作品集、机器人实验与机械齿轮实验；旧 `/threejs` 路由保留为重定向。
- `frontend/src/features/home/`：主页分区、内容数据和组件测试；文案集中在 `homepage-data.ts`。
- `frontend/src/features/assistant/`：智能助手会话、消息、目录页、API 客户端与本地交互状态。
- `frontend/src/components/`：共享组件；`three/` 管理 AI Core、机器人预览与 Three.js 场景逻辑。
- `frontend/public/`：静态图片与独立的 Three.js 演示资源；`frontend/e2e/`：Playwright 端到端测试；`frontend/tests/setup.ts`：测试初始化。
- `backend/app/`：FastAPI 应用、配置、SQLite 数据访问、会话仓储、路由与业务服务；`backend/alembic/`：数据库迁移。
- `backend/tests/`：接口与会话持久化测试；健康检查为 `/api/v1/health`。
- `docker-compose.yml` 与 `.env.example`：前端、内部后端、SQLite 数据卷及生产环境变量约定。
- `docs-archive/`：已完成或冻结的归档资料；`docs-work/`：当前需求、设计、任务与验收工作区；`docs/`：整理后的长期文档与教程。`.github/workflows/assistant-session-ci.yml`：通用 CI；`.github/workflows/deploy.yml`：仅由 `main` 触发的生产发布。

## 目录边界与文档分层

- 工作区根目录固定为仓库根目录。所有由本仓库任务产生的临时文件、缓存、数据库、日志、截图、虚拟环境和诊断产物必须写入工作区内，不得写到 `C:\AI` 根目录、用户 `%TEMP%`、桌面、下载目录或其他工作区外路径。
- 需要临时产物时，统一使用仓库内已忽略目录：`.local-evidence/`、`frontend/test-results/`、`frontend/playwright-report/`；任务结束前清理，不提交。
- Codex 托管的 worktree 属于版本控制机制，不属于任务产物；使用后必须按 Git 工作树管理规则清理。禁止手工在仓库外创建仓库副本、数据库或日志目录。
- `docs-archive/`：归档区。存放已完成、冻结或不再维护的需求、设计、验收记录与截图；只读，不新增规划，不修改历史内容；勘误需单独说明。
- `docs-work/`：工作区。存放当前需求、设计、任务拆分、实施记录和验收草稿；活跃维护，是 `docs/` 整理发布时的事实来源。
- `docs/`：长期文档与教程区。用于整理后的稳定文档和对外教程；不直接堆放任务草稿，内容应从 `docs-work/` 提炼后发布。
- 目录边界变更必须同步更新 CI 路径过滤、E2E 截图路径、README 链接和本文件。
- 发现不符合上述目录规范的文件时，先输出清单、影响范围和删除/移动建议，经用户明确确认后才能清理；不得自行删除或覆盖。

## 前端目录规范（企业级）

- `frontend/src/app/` 只放 Next.js App Router 路由、布局、页面装配和路由级元数据；不得直接写业务规则、数据库访问或大段状态逻辑。
- `frontend/src/features/<domain>/` 按业务域组织组件、hooks、状态、API 客户端、类型和相邻测试；跨域复用前先确认是否应下沉到共享层。
- `frontend/src/components/` 只放跨业务域共享的展示组件；`ui/` 放通用基础组件，`three/` 放 Three.js 场景与渲染逻辑。
- `frontend/src/lib/` 放与 React 无关的工具函数；`frontend/src/types/` 放跨域共享类型。不要保留空目录占位。
- `frontend/public/` 只放运行时静态资源；`frontend/e2e/` 只放 Playwright 用例；运行报告写入已忽略的 `frontend/test-results/`、`frontend/playwright-report/`，需要留存的视觉证据写入 `docs-work/evidence/<feature>/screenshots/`，不得写入 `docs-archive/`。
- 测试与源码相邻，命名 `*.test.ts` 或 `*.test.tsx`；文件使用 kebab-case，组件使用 PascalCase；跨模块导入使用 `@/`。
- 禁止提交 `.next/`、`node_modules/`、`*.tsbuildinfo` 和 Playwright 报告；`next-env.d.ts` 由 Next.js 生成，不得手工修改业务内容。
- 单个组件/模块超过约 300 行，或同时承担数据获取、状态编排和复杂渲染时，应拆分；新增目录必须对应明确的业务域或技术职责。

## 后端目录规范（企业级）

- `backend/app/main.py` 只负责应用创建、路由注册、生命周期和中间件装配。
- `backend/app/modules/<domain>/` 按业务域组织 `router.py`、`service.py`、`models.py`、`schemas.py`、`dependencies.py`；路由层只做参数校验和调用服务，不直接写 SQL 或业务规则。
- `backend/app/core/` 放配置、安全、错误处理等跨域基础设施；`backend/app/db.py` 放连接和会话管理。
- `backend/app/routers/` 仅用于尚未迁入业务域的兼容路由；新增功能必须进入 `modules/`，不得继续扩展该目录。
- `backend/app/services.py`、`repositories.py`、`schemas.py`、`models.py` 是当前共享核心层，可继续被各业务域复用；新增业务规则应进入对应 `modules/<domain>/`，不得继续把新领域逻辑堆入这些聚合文件。
- `backend/alembic/versions/` 只放迁移脚本；禁止手改生产库结构或跳过迁移。`backend/tests/` 镜像 `app/` 的模块划分，测试不得依赖真实生产数据。
- 配置一律来自环境变量或 `.env`（不提交）；禁止硬编码密钥、令牌和数据库口令。
- Python 使用 4 空格缩进、snake_case 和类型注解；单文件超过约 500 行或单函数承担多个职责时应拆分。

## 构建、测试与本地开发

前端命令均在 `frontend/` 下执行：

- `npm ci`：按锁文件安装依赖。
- `npm run dev`：启动本地开发服务，默认地址为 `http://localhost:3000`。
- `npm run build`：构建生产版本；`npm start`：运行已构建版本。
- `npm run lint`：执行 Next.js ESLint 检查。
- `npm test`：运行全部 Vitest 测试；`npm run test:watch`：监听变更。
- `npm run test:e2e`：运行 Playwright 端到端测试；Playwright 会自动启动本地 FastAPI 与 Next.js。

后端命令在 `backend/` 下执行，使用独立 Python 虚拟环境：

- `python -m pip install -r requirements.txt`：安装运行依赖。
- `python -m alembic upgrade head`：升级本地 SQLite 数据库。
- `python -m uvicorn app.main:app --reload --port 8000`：启动接口服务。
- `python -m pytest tests`：运行后端测试。

## 编码风格与命名

TypeScript 启用严格类型检查；遵循现有两空格缩进、双引号及分号风格。组件使用 PascalCase（大驼峰命名），文件使用 kebab-case（短横线命名），例如 `homepage-hero.tsx`；跨模块导入可用 `@/` 指向 `frontend/src/`。Python 使用四空格缩进、snake_case（下划线命名）及类型注解。代码检查遵循 `next/core-web-vitals`，未配置独立格式化工具。

## 测试与验收

前端使用 Vitest、React Testing Library 与 jsdom；测试与源码相邻，命名为 `*.test.ts` 或 `*.test.tsx`。后端使用 pytest，命名为 `test_*.py`。目前未配置覆盖率门槛；行为变更应补充对应回归测试。

前端变更提交前运行测试、代码检查及生产构建。涉及 Three.js 或页面布局时，另行检查桌面与窄屏、双向滚动、导航锚点和减少动态效果设置，并提供截图。明确区分自动测试结果与人工视觉验收。

## 提交与拉取请求

近期提交常用 `feat:`、`docs:`、`chore:` 前缀；沿用此格式，简述具体变更。每次提交聚焦单一目的。拉取请求说明变更原因、影响范围、实际验证命令与结果；关联已有任务或问题，界面变更附前后截图，并列出未完成的验证。

## 配置与代理约定

不要提交密钥、凭据、`.next/`、`node_modules/` 或本地诊断产物。DSH ACL 等诊断输出统一写入仓库内已忽略的 `.local-evidence/`，不得写到工作区外。默认用中文沟通，英文技术名词附中文解释；未经用户明确许可，不使用插件及插件提供的技能。

## Git 分支、发布与工作树管理

- `dev` 是唯一长期开发集成分支。所有功能与修复原则上从最新 `origin/dev` 创建临时分支，不得长期直接在 `dev` 堆积未发布改动。
- 临时分支统一使用 `feat/`、`fix/`、`refactor/`、`chore/` 或 `codex/` 前缀；分支名应简短说明单一目的。
- 临时分支通过 PR 合入 `dev`。不得默认直接向 `main` 提交功能代码，也不得把 `main` 当作日常开发分支。
- `main` 是唯一线上发布分支。只有经过 CI、集成测试、迁移/备份/回滚与部署安全检查后，才能通过 `dev` → `main` 的 PR 发布。
- 生产发布必须同时验证 GitHub Actions 结果、容器健康检查、同源 API、会话创建、消息持久化、刷新恢复与容器重启后的数据保留。GitHub Actions 显示 Success 不等于业务验收完成。
- 发布后立即将最新 `main` 回同步到 `dev`，保持两个长期分支内容和功能一致；允许历史提交不同，但工作树代码不得再次分叉。
- 生产发布失败必须如实报告，并按部署备份与旧镜像执行回滚；不得删除数据卷、清理生产数据或把失败包装为成功。
- 并行 Codex 会话必须使用独立 worktree。禁止未经确认改写其他会话正在使用的分支、工作树或未提交文件。
- 临时分支合并成功、确认无独立有效功能和未保存改动后，删除对应本地分支、远程分支及 worktree。
- 不得删除 `main`、`dev`，不得删除未合并、存在开放 PR 或仍被其他会话使用的分支。
- 禁止默认 force push、重写共享历史、删除生产数据卷或执行覆盖式同步。需要历史修复时先创建可追溯备份引用并取得明确授权。
- 遵守本文件现有的测试、编码、安全与权限约定；分支或发布规则变更后，应同步到 `main` 与 `dev`。
