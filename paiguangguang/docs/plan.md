# Homepage RAG Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `/` 首页重构为中保真暗色 AI / RAG 能力展示页，Hero 展示 Excalidraw 风格 RAG 链路，并在 Contact 区保留太阳 WebGL 效果。

**Architecture:** `frontend/app/page.tsx` 只作为路由入口，首页实现集中在 `frontend/features/home/`。静态内容由 `homepage-data.ts` 驱动，动效由 `framer-motion` 提供，太阳效果由 client-only 的 `@react-three/fiber` 组件提供。

**Tech Stack:** Next.js 14, React 18, TypeScript, Tailwind CSS, framer-motion, three, @react-three/fiber, @react-three/postprocessing.

## Global Constraints

- 非技术词汇使用中文，技术名词保留英文。
- 本计划以 `docs/superpowers/specs/2026-07-09-homepage-rag-redesign-design.md` 为准。
- 不修改 `backend/`。
- 不引入 `react-router-dom`、`EmailJS`、音乐播放器、Vite、GLSL loader。
- 不修改现有 `/agents/knowledge`、`/agents/browser`、`/agents/office` 页面业务逻辑。
- 不改 `frontend/app/layout.tsx`、`SiteNav`、`RouteGuard`。
- 首页新增文件集中在 `frontend/features/home/`。
- `frontend/app/page.tsx` 只渲染 `Homepage`。
- 太阳效果必须 client-only，不能触发 SSR 或 hydration error。
- `Genkins` 按标准技术名写为 `Jenkins`。

---

## File Structure

- Modify: `frontend/package.json`
  - 安装首页动效和太阳效果依赖。
- Modify: `frontend/package-lock.json`
  - 由 `npm install` 自动更新。
- Modify: `frontend/app/page.tsx`
  - 首页路由薄入口。
- Create: `frontend/features/home/homepage-data.ts`
  - 首页静态数据、RAG 链路节点、卡片内容、Roadmap 内容。
- Create: `frontend/features/home/section-title.tsx`
  - 统一章节标题。
- Create: `frontend/features/home/homepage.tsx`
  - 首页区块编排。
- Create: `frontend/features/home/homepage-hero.tsx`
  - 首屏容器和 RAG 链路说明。
- Create: `frontend/features/home/rag-flow-visual.tsx`
  - RAG 链路图。
- Create: `frontend/features/home/homepage-overview.tsx`
  - 四张能力卡。
- Create: `frontend/features/home/homepage-tech-stack.tsx`
  - 漂浮技术栈。
- Create: `frontend/features/home/homepage-projects.tsx`
  - 四个模块卡片。
- Create: `frontend/features/home/homepage-roadmap.tsx`
  - 职业规划阶段卡。
- Create: `frontend/features/home/homepage-contact.tsx`
  - 静态联系说明和太阳容器。
- Create: `frontend/features/home/sun-canvas.tsx`
  - 太阳 WebGL client component。

## Task 1: 安装依赖与新增数据模型

**Files:**

- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/features/home/homepage-data.ts`

**Interfaces:**

- Produces: `overviewCards: OverviewCard[]`
- Produces: `techStack: TechStackItem[]`
- Produces: `projectCards: ProjectCard[]`
- Produces: `roadmapStages: RoadmapStage[]`
- Produces: `ragIngestionSteps: RagFlowStep[]`
- Produces: `ragQuerySteps: RagFlowStep[]`
- Produces: `contactLinks: ContactLink[]`

- [ ] **Step 1: 安装依赖**

Run:

```powershell
cd frontend
npm install framer-motion three @react-three/fiber @react-three/postprocessing
```

Expected:

```text
package.json 和 package-lock.json 更新成功
npm 没有 dependency resolution error
```

- [ ] **Step 2: 创建首页数据文件**

Create `frontend/features/home/homepage-data.ts`:

```ts
export type RagFlowStep = {
  id: string;
  title: string;
  description: string;
  kind: "ingestion" | "query" | "branch" | "system";
};

export type OverviewCard = {
  title: string;
  description: string;
  accent: "green" | "purple" | "blue" | "pink";
};

export type TechStackItem = {
  name: string;
  category: "frontend" | "backend" | "ai" | "storage" | "workflow" | "delivery";
};

export type ProjectCard = {
  name: string;
  href: string;
  status: string;
  description: string;
  tags: string[];
};

export type RoadmapStage = {
  stage: string;
  title: string;
  description: string;
};

export type ContactLink = {
  label: string;
  value: string;
  href: string;
};

export const ragIngestionSteps: RagFlowStep[] = [
  {
    id: "knowledge-base",
    title: "企业知识库",
    description: "业务文档进入 RAG 入库链路。",
    kind: "ingestion"
  },
  {
    id: "cleaning",
    title: "数据清洗",
    description: "整理格式、去除噪声、保留可追踪信息。",
    kind: "ingestion"
  },
  {
    id: "upload",
    title: "文件上传",
    description: "接收文档并创建处理任务。",
    kind: "ingestion"
  },
  {
    id: "async-queue",
    title: "异步队列任务",
    description: "解析和索引进入后台任务。",
    kind: "system"
  },
  {
    id: "parse",
    title: "文件解析",
    description: "提取文本、页码、标题和基础 metadata。",
    kind: "ingestion"
  },
  {
    id: "chunk",
    title: "Chunk 切分",
    description: "使用 overlap 和语义边界控制上下文粒度。",
    kind: "ingestion"
  },
  {
    id: "metadata",
    title: "Metadata 构建",
    description: "记录 workspace、权限、文件和 chunk 信息。",
    kind: "ingestion"
  },
  {
    id: "embedding",
    title: "Embedding 向量化",
    description: "用嵌入模型生成可检索向量。",
    kind: "ai"
  },
  {
    id: "milvus-index",
    title: "Milvus / HNSW-IVF",
    description: "向量入库并建立索引加速检索。",
    kind: "storage"
  }
];

export const ragQuerySteps: RagFlowStep[] = [
  {
    id: "user-question",
    title: "用户问题",
    description: "用户输入需要被回答的问题。",
    kind: "query"
  },
  {
    id: "input-guardrails",
    title: "输入护栏",
    description: "检测 Prompt Injection、PII 和敏感输入。",
    kind: "system"
  },
  {
    id: "rewrite",
    title: "Rewrite",
    description: "生成 N 个 rewrite，与原始问题一起检索。",
    kind: "ai"
  },
  {
    id: "hybrid-retrieval",
    title: "Hybrid Retrieval",
    description: "同时走 BM25 关键词检索和 Vector 向量检索。",
    kind: "branch"
  },
  {
    id: "permission-filter",
    title: "权限过滤",
    description: "使用 RBAC、workspace 和 metadata filter 过滤结果。",
    kind: "system"
  },
  {
    id: "rrf",
    title: "RRF 融合",
    description: "融合多路召回结果并排序。",
    kind: "query"
  },
  {
    id: "top50",
    title: "Top 50 粗筛",
    description: "保留候选上下文集合。",
    kind: "query"
  },
  {
    id: "rerank",
    title: "Rerank Top 5",
    description: "重排序后选择最相关的上下文。",
    kind: "ai"
  },
  {
    id: "context",
    title: "Context Assembly",
    description: "去重、压缩、补全相邻 chunk 并生成引用编号。",
    kind: "query"
  },
  {
    id: "llm",
    title: "DeepSeek / LLM",
    description: "基于上下文生成最终回复。",
    kind: "ai"
  },
  {
    id: "citation",
    title: "Citation",
    description: "输出答案、来源和可检查引用。",
    kind: "query"
  }
];

export const overviewCards: OverviewCard[] = [
  {
    title: "RAG Engineer",
    description: "设计入库、检索、rerank、上下文组装和引用链路。",
    accent: "green"
  },
  {
    title: "Agent Workflow",
    description: "把计划、工具调用、状态和结果拆成可观察流程。",
    accent: "purple"
  },
  {
    title: "Full-stack AI",
    description: "连接前端体验、API、权限、存储和模型服务。",
    accent: "blue"
  },
  {
    title: "VibeCoding",
    description: "用 AI 协作快速交付，同时保持工程边界和验证。",
    accent: "pink"
  }
];

export const techStack: TechStackItem[] = [
  { name: "Next.js", category: "frontend" },
  { name: "Java", category: "backend" },
  { name: "FastAPI", category: "backend" },
  { name: "DeepSeek", category: "ai" },
  { name: "Milvus", category: "storage" },
  { name: "Redis", category: "storage" },
  { name: "MySQL", category: "storage" },
  { name: "RAG", category: "ai" },
  { name: "Agent", category: "workflow" },
  { name: "VibeCoding", category: "workflow" },
  { name: "Git", category: "delivery" },
  { name: "Docker", category: "delivery" },
  { name: "Jenkins", category: "delivery" }
];

export const projectCards: ProjectCard[] = [
  {
    name: "Portfolio Chat",
    href: "/",
    status: "V1 Live",
    description: "用于解释作品集、项目阶段和系统设计的对话入口。",
    tags: ["Chat", "DeepSeek", "Session"]
  },
  {
    name: "Knowledge Agent",
    href: "/agents/knowledge",
    status: "RAG Core",
    description: "企业知识库问答、文档管理、引用和检索调试工作台。",
    tags: ["RAG", "Retrieval", "Citation"]
  },
  {
    name: "Browser Agent",
    href: "/agents/browser",
    status: "Agent Demo",
    description: "展示研究任务中的计划、搜索步骤和综合输出。",
    tags: ["Planning", "Search", "Synthesis"]
  },
  {
    name: "Office Agent",
    href: "/agents/office",
    status: "Agent Demo",
    description: "展示报告、摘要和结构化输出的工具调用流程。",
    tags: ["Tools", "Report", "Workflow"]
  }
];

export const roadmapStages: RoadmapStage[] = [
  {
    stage: "01",
    title: "RAG System Builder",
    description: "持续打磨检索质量、权限过滤、上下文工程和评估闭环。"
  },
  {
    stage: "02",
    title: "Agent Application Engineer",
    description: "把 Agent 计划、工具、状态和人机协作做成可交付应用。"
  },
  {
    stage: "03",
    title: "AI Application Architect",
    description: "从业务目标出发设计 AI 应用架构、治理边界和交付体系。"
  }
];

export const contactLinks: ContactLink[] = [
  {
    label: "方向",
    value: "RAG / Agent / AI Application Architecture",
    href: "#hero"
  },
  {
    label: "入口",
    value: "Knowledge Agent",
    href: "/agents/knowledge"
  },
  {
    label: "协作",
    value: "用可运行系统说明工程能力",
    href: "#projects"
  }
];
```

- [ ] **Step 3: 验证安装和数据文件**

Run:

```powershell
npm run build
```

Expected:

```text
Compiled successfully
```

- [ ] **Step 4: 提交**

Run:

```powershell
git add frontend/package.json frontend/package-lock.json frontend/features/home/homepage-data.ts
git commit -m "feat: add homepage rag data"
```

Expected:

```text
[current-branch <hash>] feat: add homepage rag data
```

## Task 2: 建立首页骨架和路由入口

**Files:**

- Create: `frontend/features/home/section-title.tsx`
- Create: `frontend/features/home/homepage.tsx`
- Modify: `frontend/app/page.tsx`

**Interfaces:**

- Consumes: no previous UI components.
- Produces: `Homepage` React component.
- Produces: `SectionTitle` React component.

- [ ] **Step 1: 创建章节标题组件**

Create `frontend/features/home/section-title.tsx`:

```tsx
type SectionTitleProps = {
  eyebrow: string;
  title: string;
  description?: string;
};

export function SectionTitle({ eyebrow, title, description }: SectionTitleProps) {
  return (
    <div className="space-y-4">
      <p className="text-sm font-semibold uppercase tracking-wider text-purple-300">{eyebrow}</p>
      <h2 className="bg-gradient-to-r from-purple-300 via-pink-300 to-sky-300 bg-clip-text text-4xl font-black text-transparent sm:text-5xl">
        {title}
      </h2>
      <div className="h-1 w-32 rounded-full bg-gradient-to-r from-purple-500 to-pink-500" />
      {description ? <p className="max-w-3xl text-base leading-8 text-slate-300">{description}</p> : null}
    </div>
  );
}
```

- [ ] **Step 2: 创建首页编排组件**

Create `frontend/features/home/homepage.tsx`:

```tsx
import { SectionTitle } from "@/features/home/section-title";

export function Homepage() {
  return (
    <div className="min-h-screen bg-[#050816] text-white">
      <section id="hero" className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-7xl flex-col justify-center px-4 py-16 sm:px-6 lg:px-8">
        <div className="space-y-6">
          <p className="text-sm font-semibold uppercase tracking-wider text-purple-300">RAG Control Plane</p>
          <h1 className="max-w-5xl bg-gradient-to-r from-white via-purple-100 to-sky-200 bg-clip-text text-4xl font-black leading-tight text-transparent sm:text-6xl">
            用可见链路展示 RAG 与 Agent 工程能力
          </h1>
          <p className="max-w-3xl text-lg leading-8 text-slate-300">
            首页将展示入库、检索、rerank、上下文组装、LLM 回复和 citation 的完整链路。
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <SectionTitle eyebrow="Overview" title="能力概览." description="四张能力卡展示 RAG、Agent、Full-stack AI 和 VibeCoding。" />
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <SectionTitle eyebrow="Tech Stack" title="技术栈." description="展示本项目使用和规划中的核心技术。" />
      </section>

      <section id="projects" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <SectionTitle eyebrow="Projects" title="模块项目." description="四个模块卡片链接到已有产品界面。" />
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <SectionTitle eyebrow="Roadmap" title="职业规划." description="从 RAG System Builder 到 AI Application Architect。" />
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <SectionTitle eyebrow="Contact" title="联系说明." description="左侧静态说明，右侧保留太阳效果。" />
      </section>
    </div>
  );
}
```

- [ ] **Step 3: 修改首页路由**

Replace `frontend/app/page.tsx` with:

```tsx
import { Homepage } from "@/features/home/homepage";

export default function HomePage() {
  return <Homepage />;
}
```

- [ ] **Step 4: 验证首页骨架**

Run:

```powershell
cd frontend
npm run build
```

Expected:

```text
Compiled successfully
```

- [ ] **Step 5: 提交**

Run:

```powershell
git add frontend/app/page.tsx frontend/features/home/section-title.tsx frontend/features/home/homepage.tsx
git commit -m "feat: add homepage shell"
```

Expected:

```text
[current-branch <hash>] feat: add homepage shell
```

## Task 3: 实现 Hero RAG 链路图

**Files:**

- Create: `frontend/features/home/rag-flow-visual.tsx`
- Create: `frontend/features/home/homepage-hero.tsx`
- Modify: `frontend/features/home/homepage.tsx`

**Interfaces:**

- Consumes: `ragIngestionSteps`, `ragQuerySteps` from `homepage-data.ts`.
- Produces: `HomepageHero` React component.
- Produces: `RagFlowVisual` React component.

- [ ] **Step 1: 创建 RAG 链路图组件**

Create `frontend/features/home/rag-flow-visual.tsx`:

```tsx
import type { RagFlowStep } from "@/features/home/homepage-data";

type RagFlowVisualProps = {
  ingestionSteps: RagFlowStep[];
  querySteps: RagFlowStep[];
};

const kindClass: Record<RagFlowStep["kind"], string> = {
  ingestion: "border-emerald-400/40 bg-emerald-400/10 text-emerald-100",
  query: "border-sky-400/40 bg-sky-400/10 text-sky-100",
  branch: "border-purple-400/50 bg-purple-400/10 text-purple-100",
  system: "border-pink-400/40 bg-pink-400/10 text-pink-100"
};

function FlowNode({ step, index }: { step: RagFlowStep; index: number }) {
  return (
    <div className={["group relative min-h-[8rem] rounded-2xl border p-4 shadow-2xl shadow-black/30 backdrop-blur", kindClass[step.kind]].join(" ")}>
      <div className="absolute -inset-px rounded-2xl bg-gradient-to-br from-white/10 to-transparent opacity-0 transition group-hover:opacity-100" />
      <div className="relative space-y-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-white/50">{String(index + 1).padStart(2, "0")}</span>
          <span className="h-2 w-2 rounded-full bg-current shadow-[0_0_16px_currentColor]" />
        </div>
        <h3 className="text-base font-bold text-white">{step.title}</h3>
        <p className="text-sm leading-6 text-slate-300">{step.description}</p>
      </div>
    </div>
  );
}

export function RagFlowVisual({ ingestionSteps, querySteps }: RagFlowVisualProps) {
  return (
    <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-[#090d1f]/90 p-4 shadow-2xl shadow-purple-950/30 sm:p-6">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff0d_1px,transparent_1px),linear-gradient(to_bottom,#ffffff0d_1px,transparent_1px)] bg-[size:28px_28px]" />
      <div className="absolute left-0 top-0 h-px w-full bg-gradient-to-r from-transparent via-purple-400 to-transparent" />
      <div className="relative space-y-8">
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-wider text-emerald-300">Indexing Pipeline</p>
            <span className="rounded-full border border-emerald-300/30 px-3 py-1 text-xs font-semibold text-emerald-200">Milvus Ready</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {ingestionSteps.map((step, index) => (
              <FlowNode key={step.id} step={step} index={index} />
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-wider text-purple-300">Query Pipeline</p>
            <div className="flex flex-wrap gap-2">
              {["Guardrails", "BM25", "Vector", "RRF", "Rerank", "Citation"].map((label) => (
                <span key={label} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-200">
                  {label}
                </span>
              ))}
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {querySteps.map((step, index) => (
              <FlowNode key={step.id} step={step} index={index} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 Hero 组件**

Create `frontend/features/home/homepage-hero.tsx`:

```tsx
"use client";

import { motion } from "framer-motion";

import { ragIngestionSteps, ragQuerySteps } from "@/features/home/homepage-data";
import { RagFlowVisual } from "@/features/home/rag-flow-visual";

export function HomepageHero() {
  return (
    <section id="hero" className="relative min-h-[calc(100vh-5rem)] overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(168,85,247,0.22),transparent_32%),radial-gradient(circle_at_80%_10%,rgba(56,189,248,0.16),transparent_30%),#050816]" />
      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 py-16 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="max-w-5xl space-y-6"
        >
          <p className="text-sm font-semibold uppercase tracking-wider text-purple-300">RAG Control Plane</p>
          <h1 className="bg-gradient-to-r from-white via-purple-100 to-sky-200 bg-clip-text text-4xl font-black leading-tight text-transparent sm:text-6xl lg:text-7xl">
            用可见链路展示 RAG 与 Agent 工程能力
          </h1>
          <p className="max-w-3xl text-lg leading-8 text-slate-300">
            从文档入库、Hybrid Retrieval、RRF、rerank、Context Assembly 到 DeepSeek 回复和 Citation，首页第一屏直接展示完整工程路径。
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.15, ease: "easeOut" }}
        >
          <RagFlowVisual ingestionSteps={ragIngestionSteps} querySteps={ragQuerySteps} />
        </motion.div>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: 接入首页编排**

Modify `frontend/features/home/homepage.tsx` so the first section uses `HomepageHero`:

```tsx
import { HomepageHero } from "@/features/home/homepage-hero";
import { SectionTitle } from "@/features/home/section-title";

export function Homepage() {
  return (
    <div className="min-h-screen bg-[#050816] text-white">
      <HomepageHero />

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <SectionTitle eyebrow="Overview" title="能力概览." description="四张能力卡展示 RAG、Agent、Full-stack AI 和 VibeCoding。" />
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <SectionTitle eyebrow="Tech Stack" title="技术栈." description="展示本项目使用和规划中的核心技术。" />
      </section>

      <section id="projects" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <SectionTitle eyebrow="Projects" title="模块项目." description="四个模块卡片链接到已有产品界面。" />
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <SectionTitle eyebrow="Roadmap" title="职业规划." description="从 RAG System Builder 到 AI Application Architect。" />
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <SectionTitle eyebrow="Contact" title="联系说明." description="左侧静态说明，右侧保留太阳效果。" />
      </section>
    </div>
  );
}
```

- [ ] **Step 4: 验证 Hero**

Run:

```powershell
cd frontend
npm run build
```

Expected:

```text
Compiled successfully
```

- [ ] **Step 5: 提交**

Run:

```powershell
git add frontend/features/home/rag-flow-visual.tsx frontend/features/home/homepage-hero.tsx frontend/features/home/homepage.tsx
git commit -m "feat: add rag hero flow"
```

Expected:

```text
[current-branch <hash>] feat: add rag hero flow
```

## Task 4: 实现 Overview、Tech Stack、Projects、Roadmap

**Files:**

- Create: `frontend/features/home/homepage-overview.tsx`
- Create: `frontend/features/home/homepage-tech-stack.tsx`
- Create: `frontend/features/home/homepage-projects.tsx`
- Create: `frontend/features/home/homepage-roadmap.tsx`
- Modify: `frontend/features/home/homepage.tsx`

**Interfaces:**

- Consumes: `overviewCards`, `techStack`, `projectCards`, `roadmapStages`.
- Produces: `HomepageOverview`, `HomepageTechStack`, `HomepageProjects`, `HomepageRoadmap`.

- [ ] **Step 1: 创建 Overview 组件**

Create `frontend/features/home/homepage-overview.tsx`:

```tsx
"use client";

import { motion } from "framer-motion";

import { overviewCards } from "@/features/home/homepage-data";
import { SectionTitle } from "@/features/home/section-title";

const accentClass = {
  green: "from-emerald-400 to-teal-500",
  purple: "from-purple-400 to-fuchsia-500",
  blue: "from-sky-400 to-blue-500",
  pink: "from-pink-400 to-purple-500"
};

export function HomepageOverview() {
  return (
    <section className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff0a_1px,transparent_1px),linear-gradient(to_bottom,#ffffff0a_1px,transparent_1px)] bg-[size:24px_24px]" />
      <div className="relative space-y-10">
        <SectionTitle eyebrow="Overview" title="能力概览." description="四个方向说明首页背后的 AI 工程能力。" />
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {overviewCards.map((card, index) => (
            <motion.article
              key={card.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.25 }}
              transition={{ duration: 0.45, delay: index * 0.08 }}
              className="group relative min-h-[17rem] overflow-hidden rounded-2xl border border-white/10 bg-[#151525] p-6 shadow-2xl shadow-black/30 transition hover:border-purple-400/40"
            >
              <div className={`absolute -inset-1 bg-gradient-to-br ${accentClass[card.accent]} opacity-0 blur-2xl transition group-hover:opacity-20`} />
              <div className="relative flex h-full flex-col items-center justify-center gap-6 text-center">
                <div className={`h-16 w-16 rounded-2xl bg-gradient-to-br ${accentClass[card.accent]} p-px shadow-[0_0_32px_rgba(168,85,247,0.22)]`}>
                  <div className="flex h-full w-full items-center justify-center rounded-2xl bg-[#151525] text-xl font-black text-white">
                    {card.title.slice(0, 2)}
                  </div>
                </div>
                <h3 className="text-xl font-bold text-white transition group-hover:bg-gradient-to-r group-hover:from-purple-300 group-hover:to-pink-300 group-hover:bg-clip-text group-hover:text-transparent">
                  {card.title}
                </h3>
                <p className="text-sm leading-7 text-slate-300">{card.description}</p>
              </div>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: 创建 Tech Stack 组件**

Create `frontend/features/home/homepage-tech-stack.tsx`:

```tsx
"use client";

import { motion } from "framer-motion";

import { techStack } from "@/features/home/homepage-data";

export function HomepageTechStack() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-slate-950 via-black to-slate-950 py-20">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:50px_50px]" />
      <div className="relative mx-auto min-h-[36rem] max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="absolute inset-0 flex items-center justify-center">
          <h2 className="select-none bg-gradient-to-r from-slate-700 via-slate-500 to-slate-700 bg-clip-text text-5xl font-black text-transparent opacity-60 sm:text-7xl">
            Tech Stack
          </h2>
        </div>
        <div className="relative grid min-h-[36rem] grid-cols-2 place-items-center gap-8 sm:grid-cols-3 lg:grid-cols-5">
          {techStack.map((tech, index) => (
            <motion.div
              key={tech.name}
              initial={{ opacity: 0, scale: 0.85 }}
              whileInView={{ opacity: 1, scale: 1 }}
              animate={{ y: [0, -14, 0] }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{
                opacity: { duration: 0.4, delay: index * 0.04 },
                scale: { duration: 0.4, delay: index * 0.04 },
                y: { duration: 3 + index * 0.15, repeat: Infinity, ease: "easeInOut" }
              }}
              className="group flex h-24 w-24 items-center justify-center rounded-3xl border border-white/10 bg-white/[0.04] p-3 text-center shadow-2xl shadow-black/30 backdrop-blur transition hover:border-purple-400/40 hover:bg-purple-400/10 sm:h-28 sm:w-28"
            >
              <span className="text-sm font-black text-slate-100 transition group-hover:text-purple-200">{tech.name}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: 创建 Projects 组件**

Create `frontend/features/home/homepage-projects.tsx`:

```tsx
"use client";

import Link from "next/link";
import { motion } from "framer-motion";

import { projectCards } from "@/features/home/homepage-data";
import { SectionTitle } from "@/features/home/section-title";

export function HomepageProjects() {
  return (
    <section id="projects" className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="space-y-10">
        <SectionTitle eyebrow="Projects" title="模块项目." description="四个模块卡片展示当前 AI 平台的能力边界。" />
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {projectCards.map((project, index) => (
            <motion.article
              key={project.name}
              initial={{ opacity: 0, y: 28 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.45, delay: index * 0.08 }}
              className="group relative overflow-hidden rounded-2xl border border-white/10 bg-[#151525] p-6 shadow-2xl shadow-black/30 transition hover:border-purple-400/40"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-purple-900/10 to-pink-900/10 opacity-0 transition group-hover:opacity-100" />
              <div className="relative flex min-h-[22rem] flex-col gap-5">
                <div className="flex items-center justify-between gap-3">
                  <span className="rounded-full border border-purple-300/30 bg-purple-300/10 px-3 py-1 text-xs font-semibold text-purple-200">
                    {project.status}
                  </span>
                </div>
                <h3 className="text-2xl font-bold text-white transition group-hover:bg-gradient-to-r group-hover:from-purple-300 group-hover:to-pink-300 group-hover:bg-clip-text group-hover:text-transparent">
                  {project.name}
                </h3>
                <p className="text-sm leading-7 text-slate-300">{project.description}</p>
                <div className="mt-auto flex flex-wrap gap-2 border-t border-white/10 pt-4">
                  {project.tags.map((tag) => (
                    <span key={tag} className="rounded-full bg-slate-800/80 px-2.5 py-1 text-xs font-semibold text-slate-300">
                      #{tag}
                    </span>
                  ))}
                </div>
                <Link href={project.href} className="text-sm font-semibold text-purple-300 transition hover:text-pink-300">
                  打开模块 →
                </Link>
              </div>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: 创建 Roadmap 组件**

Create `frontend/features/home/homepage-roadmap.tsx`:

```tsx
"use client";

import { motion } from "framer-motion";

import { roadmapStages } from "@/features/home/homepage-data";
import { SectionTitle } from "@/features/home/section-title";

export function HomepageRoadmap() {
  return (
    <section className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="space-y-10">
        <SectionTitle eyebrow="Roadmap" title="职业规划." description="从 RAG 系统建设，到 Agent 应用工程，再到 AI 应用架构。" />
        <div className="grid gap-6 lg:grid-cols-3">
          {roadmapStages.map((stage, index) => (
            <motion.article
              key={stage.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.25 }}
              transition={{ duration: 0.45, delay: index * 0.1 }}
              className="group relative min-h-[17rem] overflow-hidden rounded-2xl border border-white/10 bg-[#151525] p-8 shadow-2xl shadow-black/30 transition hover:border-purple-400/40"
            >
              <div className="absolute -inset-1 bg-gradient-to-br from-purple-600/10 to-pink-600/10 opacity-0 blur-2xl transition group-hover:opacity-100" />
              <div className="relative flex h-full flex-col justify-center gap-6">
                <span className="text-sm font-black tracking-wider text-purple-300">{stage.stage}</span>
                <h3 className="text-2xl font-bold text-white">{stage.title}</h3>
                <p className="text-sm leading-7 text-slate-300">{stage.description}</p>
              </div>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: 接入首页编排**

Modify `frontend/features/home/homepage.tsx`:

```tsx
import { HomepageContact } from "@/features/home/homepage-contact";
import { HomepageHero } from "@/features/home/homepage-hero";
import { HomepageOverview } from "@/features/home/homepage-overview";
import { HomepageProjects } from "@/features/home/homepage-projects";
import { HomepageRoadmap } from "@/features/home/homepage-roadmap";
import { HomepageTechStack } from "@/features/home/homepage-tech-stack";

export function Homepage() {
  return (
    <div className="min-h-screen bg-[#050816] text-white">
      <HomepageHero />
      <HomepageOverview />
      <HomepageTechStack />
      <HomepageProjects />
      <HomepageRoadmap />
      <HomepageContact />
    </div>
  );
}
```

这里会引用 `HomepageContact`。如果按任务逐个提交，先在 Task 4 创建 `frontend/features/home/homepage-contact.tsx`，使用下面这份可构建内容；Task 5 再替换为带太阳效果的最终实现：

```tsx
import { SectionTitle } from "@/features/home/section-title";

export function HomepageContact() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <SectionTitle eyebrow="Contact" title="联系说明." description="左侧静态说明，右侧太阳效果在下一任务接入。" />
    </section>
  );
}
```

- [ ] **Step 6: 验证区块**

Run:

```powershell
cd frontend
npm run build
```

Expected:

```text
Compiled successfully
```

- [ ] **Step 7: 提交**

Run:

```powershell
git add frontend/features/home/homepage-overview.tsx frontend/features/home/homepage-tech-stack.tsx frontend/features/home/homepage-projects.tsx frontend/features/home/homepage-roadmap.tsx frontend/features/home/homepage-contact.tsx frontend/features/home/homepage.tsx
git commit -m "feat: add homepage content sections"
```

Expected:

```text
[current-branch <hash>] feat: add homepage content sections
```

## Task 5: 实现 Contact 静态说明和太阳 WebGL

**Files:**

- Create: `frontend/features/home/sun-canvas.tsx`
- Modify: `frontend/features/home/homepage-contact.tsx`

**Interfaces:**

- Consumes: `contactLinks` from `homepage-data.ts`.
- Produces: `SunCanvas` client component.
- Produces: `HomepageContact` with dynamic import.

- [ ] **Step 1: 创建太阳 canvas**

Create `frontend/features/home/sun-canvas.tsx`:

```tsx
"use client";

import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import type { Mesh, ShaderMaterial } from "three";
import * as THREE from "three";

const sunVertexShader = `
  varying vec3 vNormal;
  varying vec3 vPosition;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vPosition = worldPosition.xyz;
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`;

const sunFragmentShader = `
  uniform float uTime;
  varying vec3 vNormal;
  varying vec3 vPosition;

  float hash(vec3 p) {
    p = fract(p * 0.3183099 + vec3(0.1, 0.2, 0.3));
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
  }

  float noise(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float n = mix(
      mix(mix(hash(i + vec3(0,0,0)), hash(i + vec3(1,0,0)), f.x),
          mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),
      mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x),
          mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y),
      f.z
    );
    return n;
  }

  void main() {
    vec3 p = normalize(vPosition) * 4.0;
    float n = noise(p + vec3(uTime * 0.12, uTime * 0.07, 0.0));
    float bands = noise(p * 1.8 + vec3(0.0, uTime * 0.18, uTime * 0.08));
    float fresnel = pow(1.0 - max(dot(normalize(vNormal), vec3(0.0, 0.0, 1.0)), 0.0), 2.0);
    vec3 color = mix(vec3(1.0, 0.42, 0.04), vec3(1.0, 0.95, 0.34), n);
    color += vec3(1.0, 0.35, 0.05) * bands * 0.55;
    color += vec3(1.0, 0.9, 0.32) * fresnel * 1.5;
    gl_FragColor = vec4(color, 1.0);
  }
`;

function SunSphere() {
  const materialRef = useRef<ShaderMaterial | null>(null);
  const meshRef = useRef<Mesh | null>(null);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 }
    }),
    []
  );

  useFrame((_, delta) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value += delta;
    }
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.08;
    }
  });

  return (
    <group>
      <mesh ref={meshRef} scale={1.65}>
        <sphereGeometry args={[1, 96, 96]} />
        <shaderMaterial ref={materialRef} vertexShader={sunVertexShader} fragmentShader={sunFragmentShader} uniforms={uniforms} />
      </mesh>
      <mesh scale={1.78}>
        <sphereGeometry args={[1, 96, 96]} />
        <meshBasicMaterial color="#ffb13b" transparent opacity={0.16} side={THREE.BackSide} />
      </mesh>
    </group>
  );
}

export function SunCanvas() {
  return (
    <Canvas camera={{ fov: 45, near: 0.1, far: 100, position: [-3.8, 2.8, 6.5] }} dpr={[1, 1.5]} gl={{ toneMapping: THREE.NoToneMapping }}>
      <ambientLight intensity={0.45} />
      <SunSphere />
      <EffectComposer disableNormalPass>
        <Bloom intensity={1.2} luminanceThreshold={0.15} luminanceSmoothing={0.25} mipmapBlur />
      </EffectComposer>
    </Canvas>
  );
}
```

- [ ] **Step 2: 创建 Contact 组件**

Replace `frontend/features/home/homepage-contact.tsx`:

```tsx
"use client";

import dynamic from "next/dynamic";
import Link from "next/link";

import { contactLinks } from "@/features/home/homepage-data";
import { SectionTitle } from "@/features/home/section-title";

const SunCanvas = dynamic(() => import("@/features/home/sun-canvas").then((mod) => mod.SunCanvas), {
  ssr: false,
  loading: () => <div className="h-full min-h-[22rem] rounded-3xl bg-orange-400/10" />
});

export function HomepageContact() {
  return (
    <section className="relative overflow-hidden py-16">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_40%,rgba(251,146,60,0.18),transparent_28%),#050816]" />
      <div className="relative mx-auto grid max-w-7xl gap-8 px-4 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:px-8">
        <div className="rounded-3xl border border-white/10 bg-[#151525]/80 p-6 shadow-2xl shadow-black/30 backdrop-blur sm:p-8">
          <SectionTitle eyebrow="Contact" title="联系说明." description="这里不接 EmailJS，只展示清晰的协作方向和入口。" />
          <div className="mt-8 space-y-4">
            {contactLinks.map((link) => (
              <Link key={link.label} href={link.href} className="block rounded-2xl border border-white/10 bg-white/[0.04] p-4 transition hover:border-purple-400/40 hover:bg-purple-400/10">
                <span className="text-xs font-semibold uppercase tracking-wider text-purple-300">{link.label}</span>
                <p className="mt-2 text-sm leading-7 text-slate-200">{link.value}</p>
              </Link>
            ))}
          </div>
        </div>
        <div className="min-h-[24rem] overflow-hidden rounded-3xl border border-white/10 bg-black/40 shadow-2xl shadow-orange-950/30 lg:min-h-[34rem]">
          <SunCanvas />
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: 验证太阳构建**

Run:

```powershell
cd frontend
npm run build
```

Expected:

```text
Compiled successfully
```

- [ ] **Step 4: 手动验证太阳非空白**

Run:

```powershell
npm run dev
```

Open:

```text
http://localhost:3000/
```

Expected:

```text
Contact 区右侧出现发光太阳，页面没有 hydration error
```

- [ ] **Step 5: 提交**

Run:

```powershell
git add frontend/features/home/sun-canvas.tsx frontend/features/home/homepage-contact.tsx
git commit -m "feat: add homepage contact sun"
```

Expected:

```text
[current-branch <hash>] feat: add homepage contact sun
```

## Task 6: 最终验证与小幅视觉收口

**Files:**

- Modify only if verification exposes layout issues:
  - `frontend/features/home/homepage.tsx`
  - `frontend/features/home/homepage-hero.tsx`
  - `frontend/features/home/rag-flow-visual.tsx`
  - `frontend/features/home/homepage-overview.tsx`
  - `frontend/features/home/homepage-tech-stack.tsx`
  - `frontend/features/home/homepage-projects.tsx`
  - `frontend/features/home/homepage-roadmap.tsx`
  - `frontend/features/home/homepage-contact.tsx`
  - `frontend/features/home/sun-canvas.tsx`

**Interfaces:**

- Consumes: all homepage components.
- Produces: verified homepage.

- [ ] **Step 1: 全量构建**

Run:

```powershell
cd frontend
npm run build
```

Expected:

```text
Compiled successfully
```

- [ ] **Step 2: Lint 验证**

Run:

```powershell
npm run lint
```

Expected:

```text
No ESLint warnings or errors
```

If the project prompts to configure ESLint, keep the existing project behavior and record that lint was not runnable without configuration.

- [ ] **Step 3: 边界 diff 检查**

Run from repository root:

```powershell
git diff -- backend
git diff -- frontend/app/agents frontend/features/knowledge-agent frontend/features/browser-agent frontend/features/office-agent
```

Expected:

```text
两个命令都没有输出
```

- [ ] **Step 4: 路由 smoke test**

Run:

```powershell
cd frontend
npm run dev
```

Open these URLs:

```text
http://localhost:3000/
http://localhost:3000/agents/knowledge
http://localhost:3000/agents/browser
http://localhost:3000/agents/office
http://localhost:3000/architecture
http://localhost:3000/admin
```

Expected:

```text
/ 显示新首页
其他路由继续按现有 auth 逻辑展示或跳转
页面没有 runtime error overlay
```

- [ ] **Step 5: 响应式检查**

Check `/` at:

```text
390 x 844
768 x 1024
1440 x 900
```

Expected:

```text
没有横向滚动
Hero 链路可读
卡片文字不溢出
Contact 区太阳有稳定高度
```

- [ ] **Step 6: 提交最终收口**

If files changed during this task:

```powershell
git add frontend/features/home frontend/app/page.tsx frontend/package.json frontend/package-lock.json
git commit -m "chore: polish homepage rag redesign"
```

Expected:

```text
[current-branch <hash>] chore: polish homepage rag redesign
```

If no files changed during this task:

```powershell
git status --short
```

Expected:

```text
没有未提交的首页实现改动
```

## Self-Review

Spec coverage:

- Hero RAG 链路：Task 3。
- Overview 四张能力卡：Task 4。
- Tech Stack 十三个技术项：Task 1 和 Task 4。
- Projects 四个模块卡片：Task 1 和 Task 4。
- Roadmap 三阶段规划：Task 1 和 Task 4。
- Contact 静态说明和太阳效果：Task 5。
- 不改后端与路由边界：Task 6。

Placeholder scan:

- 本计划未发现占位标记。
- 本计划未发现空泛实施步骤。
- 本计划没有未定义接口名。

Type consistency:

- `RagFlowStep`、`OverviewCard`、`TechStackItem`、`ProjectCard`、`RoadmapStage`、`ContactLink` 均在 Task 1 定义。
- 后续任务只消费 Task 1 中定义的导出名称。
- `Homepage`、`HomepageHero`、`RagFlowVisual`、`HomepageOverview`、`HomepageTechStack`、`HomepageProjects`、`HomepageRoadmap`、`HomepageContact`、`SunCanvas` 的导出名称一致。
