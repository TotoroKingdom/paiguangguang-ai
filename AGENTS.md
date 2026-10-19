# Repository Guidelines

## 项目结构与模块组织

- `frontend/src/app/`：Next.js App Router（应用路由）、布局及全局样式。
- `frontend/src/features/home/`：主页分区、内容数据和组件测试；文案集中在 `homepage-data.ts`。
- `frontend/src/components/`：共享组件；`three/` 管理 AI Core 的 Three.js 场景、构图与滚动逻辑。
- `frontend/public/`：静态图片；`frontend/tests/setup.ts`：测试初始化。
- `backend/app/main.py`：FastAPI 健康检查接口 `/api/v1/health`；`backend/tests/`：接口测试。
- `docs-codex/`：需求、任务与视觉验收记录；`.github/workflows/deploy.yml`：部署流程。

## 构建、测试与本地开发

前端命令均在 `frontend/` 下执行：

- `npm ci`：按锁文件安装依赖。
- `npm run dev`：启动本地开发服务，默认地址为 `http://localhost:3000`。
- `npm run build`：构建生产版本；`npm start`：运行已构建版本。
- `npm run lint`：执行 Next.js ESLint 检查。
- `npm test`：运行全部 Vitest 测试；`npm run test:watch`：监听变更。

后端命令在 `backend/` 下执行，使用独立 Python 虚拟环境：

- `python -m pip install -r requirements.txt`：安装运行依赖。
- `python -m pip install pytest httpx`：安装测试所需依赖，目前未单独声明测试依赖文件。
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

不要提交密钥、凭据、`.next/`、`node_modules/` 或本地诊断产物。DSH ACL 诊断的 `-Out` 应指向仓库外，例如 `$env:LOCALAPPDATA\DSH\acl-reports`。默认用中文沟通，英文技术名词附中文解释；未经用户明确许可，不使用插件及插件提供的技能。
