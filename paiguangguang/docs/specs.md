# 首页 RAG 中保真重构 Spec

> 本文件为本次首页重构的执行基准。`docs/features/homepage-redesign/*` 中的旧草稿仅作历史参考；若内容冲突，以本文件为准。

## 目标

将 `/` 首页重构为一个暗色科幻风的 AI / RAG 能力展示页。页面中保真参考 `My_website-main.zip` 和用户提供的截图，保留主要区块、发光卡片、渐变标题、滚动动效，并在 `Contact` 区保留太阳 WebGL 视觉效果。

首页内容不再围绕通用个人介绍，而是围绕 RAG、Agent、AI 应用工程能力展开。第一屏直接展示 RAG 链路图，链路参考 `C:\Users\totoro\Downloads\rag-agent (1).excalidraw`。

## 当前项目上下文

- 前端在 `frontend/`，使用 Next.js 14 App Router、React 18、TypeScript、Tailwind CSS。
- 首页入口是 `frontend/app/page.tsx`。
- 全局布局在 `frontend/app/layout.tsx`，包含 `AuthProvider`、`RouteGuard`、`SiteNav`。
- 现有模块路由包括 `/agents/knowledge`、`/agents/browser`、`/agents/office`、`/architecture`、`/admin`、`/login`。
- 现有 `PortfolioChatPanel` 在 `frontend/features/portfolio-chat/portfolio-chat-panel.tsx`，本次只复用，不改 API 行为。
- 后端在 `backend/`，本次不改后端。

## 参考来源

视觉参考：

- `C:\Users\totoro\Downloads\My_website-main.zip`
- 用户提供的六张截图，重点参考能力卡、Tech Stack、Projects、Target、Contact 太阳效果。

链路参考：

- `C:\Users\totoro\Downloads\rag-agent (1).excalidraw`
- Hero 中的 RAG 链路采用该文件中的入库链路、问答链路、Hybrid Retrieval、RRF、rerank、Context Assembly、Citation 等节点。

不直接迁移：

- 不迁移 Vite。
- 不迁移 `react-router-dom`。
- 不迁移 EmailJS。
- 不迁移音乐播放器。
- 不迁移动漫图、原站项目图和未确认授权素材。
- 不迁移全站导航结构。

## 页面结构

### 1. Hero：RAG 链路图

Hero 不做传统个人介绍，首屏直接展示 RAG 工程链路。

入库链路：

```text
企业知识库
-> 数据清洗
-> 文件上传
-> 异步队列任务
-> 文件解析
-> Chunk 切分
-> Metadata 构建
-> Embedding 向量化
-> Milvus 向量数据库 / HNSW-IVF Index
```

问答链路：

```text
用户问题
-> 输入护栏
-> 重写用户问题 / 生成 N 个 rewrite
-> Hybrid Retrieval
   -> BM25 关键词检索
   -> Vector 向量检索
-> 权限过滤
-> RRF 融合
-> Top 50 粗筛
-> Rerank Top 5
-> Context Assembly 上下文组装
-> DeepSeek / LLM
-> 生成最终回复
-> Citation 引用
```

Hero 视觉要求：

- 暗色满宽区域，背景可使用局部网格、轻微噪点、紫粉蓝渐变光。
- 主链路用发光节点和连线展示。
- 入库链路作为辅助轨道，问答链路作为主轨道。
- `Hybrid Retrieval` 节点应显示 BM25 与 Vector 两条分支。
- `Milvus`、`Redis`、`DeepSeek`、`Guardrails`、`Trace` 作为能力徽标或旁路标签展示。
- 节点之间有轻微流光、脉冲或入场动画。
- 移动端改为纵向步骤流，避免横向压缩。

### 2. Overview：四张能力卡

中保真复刻截图中的四张能力卡，内容改为：

- `RAG Engineer`
- `Agent Workflow`
- `Full-stack AI`
- `VibeCoding`

视觉要求：

- 发光边框卡片。
- 暗色卡面。
- 简洁图形图标，可用 CSS / inline SVG 实现。
- Hover 时卡片边框、图标和标题出现紫粉渐变。
- 桌面四列，移动端单列或两列。

### 3. Tech Stack：漂浮图标墙

保留截图中的漂浮图标墙感觉，但使用本项目展示口径的技术栈：

- `Next.js`
- `Java`
- `FastAPI`
- `DeepSeek`
- `Milvus`
- `Redis`
- `MySQL`
- `RAG`
- `Agent`
- `VibeCoding`
- `Git`
- `Docker`
- `Jenkins`

说明：用户输入中的 `Genkins` 按行业标准拼写为 `Jenkins`。

视觉要求：

- 中央显示半透明标题 `Tech Stack`。
- 技术项以图标或文字徽章漂浮。
- 使用不同延迟的上下浮动动画。
- 不强制复制原站图片资源；优先使用文字徽章、简洁图形或可控 SVG。

### 4. Projects：四个模块卡片

替换为当前平台模块：

- `Portfolio Chat`
- `Knowledge Agent`
- `Browser Agent`
- `Office Agent`

视觉要求：

- 参考截图中的 Projects 卡片布局。
- 每张卡片包含模块名、说明、技术标签、入口链接、当前状态。
- 卡片链接到现有路由。
- `Portfolio Chat` 链接到首页内的 live chat 区域或 `/`。
- `Knowledge Agent` 链接到 `/agents/knowledge`。
- `Browser Agent` 链接到 `/agents/browser`。
- `Office Agent` 链接到 `/agents/office`。

### 5. Roadmap：个人职业规划

替代目标站的 `Target` 区，展示三阶段规划：

```text
RAG System Builder
-> Agent Application Engineer
-> AI Application Architect
```

视觉要求：

- 采用三张阶段卡，贴近截图中的 Target 风格。
- 每张卡有标题、简短说明和阶段编号。
- 桌面三列，移动端纵向排列。
- 可使用轻微入场动画和发光 Hover。

### 6. Contact：静态联系说明 + 太阳效果

保留目标站 Contact 的太阳 WebGL 效果，但左侧不照搬 EmailJS 表单。

左侧内容：

- 静态联系说明卡。
- 表达关注方向：RAG、Agent、AI 应用架构。
- 可以放 GitHub、Email、模块入口等静态链接。
- 不接 EmailJS。
- 不暴露任何第三方 service key。

右侧内容：

- 太阳 WebGL 效果。
- 太阳组件必须是 client-only。
- 若 shader 迁移成本过高，可以用等效 Three.js shader 太阳实现，但视觉上应保留发光、表面流动和外圈光晕。

## 组件架构

建议新增目录：

```text
frontend/features/home/
  homepage.tsx
  homepage-data.ts
  section-title.tsx
  homepage-hero.tsx
  rag-flow-visual.tsx
  homepage-overview.tsx
  homepage-tech-stack.tsx
  homepage-projects.tsx
  homepage-roadmap.tsx
  homepage-contact.tsx
  sun-canvas.tsx
```

修改文件：

```text
frontend/app/page.tsx
frontend/package.json
frontend/package-lock.json
```

`frontend/app/page.tsx` 应保持为薄入口：

```tsx
import { Homepage } from "@/features/home/homepage";

export default function HomePage() {
  return <Homepage />;
}
```

## 依赖策略

允许新增依赖：

```text
framer-motion
three
@react-three/fiber
@react-three/postprocessing
```

不新增：

```text
react-router-dom
@emailjs/browser
react-tilt
vite-plugin-glsl
lygia
```

Tilt 效果用 CSS transform 和 mouse-independent hover 近似实现。GLSL shader 用 TypeScript 字符串常量或组件内字符串，不依赖 Vite 的 GLSL loader。

## 数据策略

首页静态内容集中在 `frontend/features/home/homepage-data.ts`。

需要包含：

- Overview 能力卡数据。
- Tech Stack 技术栈数据。
- Projects 模块卡片数据。
- Roadmap 阶段数据。
- Hero RAG 链路节点与连接数据。
- Contact 静态链接数据。

组件只负责展示，不在组件内散落大段文案。

## 响应式要求

- 390px 宽度下不出现横向滚动。
- Hero RAG 链路在移动端切换为纵向流程。
- 卡片文字不能溢出或互相遮挡。
- Contact 区在移动端先显示说明卡，再显示太阳效果。
- 太阳 canvas 在移动端有固定高度，不撑破页面。

## 验证要求

必须通过：

```bash
cd frontend
npm run build
```

建议验证：

```bash
cd frontend
npm run lint
```

手动检查：

- `/` 显示新首页。
- `/agents/knowledge`、`/agents/browser`、`/agents/office` 路由仍可打开或按现有 auth 逻辑跳转。
- `backend/` 没有 diff。
- 页面在 390x844、768x1024、1440x900 下可读。
- 太阳 canvas 非空白。
- 页面没有 React hydration error。

## 非目标

- 不改后端。
- 不改现有 Agent 页面业务逻辑。
- 不新增 Contact 后端接口。
- 不做完整目标站高保真复刻。
- 不接音乐播放。
- 不接 EmailJS。
- 不引入原站未授权图片或音乐。

## 风险与控制

| 风险 | 控制 |
| --- | --- |
| WebGL SSR 报错 | `sun-canvas.tsx` 使用 `"use client"`，并通过 `next/dynamic` 禁用 SSR。 |
| shader 构建失败 | 不使用 `.glsl` import，改用 TypeScript 字符串。 |
| 依赖膨胀 | 只安装太阳和动效必需依赖。 |
| 首页样式影响其他页面 | 不修改 `globals.css` 的全局背景，不改 `SiteNav`。 |
| RAG 链路过密 | 桌面分为入库轨道和问答轨道，移动端改成纵向步骤。 |
| 旧文档冲突 | 本文件和对应 plan 文件为准。 |

## 接受标准

- 首页结构符合本 Spec 的六个区块。
- Hero RAG 链路包含入库链路和问答链路核心节点。
- Overview 四张卡内容为 `RAG Engineer`、`Agent Workflow`、`Full-stack AI`、`VibeCoding`。
- Tech Stack 包含用户指定的 13 个技术项，并使用 `Jenkins` 标准拼写。
- Projects 只展示四个模块：`Portfolio Chat`、`Knowledge Agent`、`Browser Agent`、`Office Agent`。
- Roadmap 展示三阶段职业规划。
- Contact 保留太阳视觉效果，左侧为静态说明卡。
- 不修改 `backend/`。
- `npm run build` 成功。
