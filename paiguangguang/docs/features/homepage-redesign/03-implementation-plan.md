# Homepage Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a redesigned AI Engineer Portfolio homepage at `/` using isolated Next.js homepage components.

**Architecture:** Keep the Next.js App Router route unchanged and make `frontend/app/page.tsx` a thin wrapper around `frontend/features/homepage/homepage.tsx`. Static homepage content lives in a typed data module, while existing live chat behavior remains in `PortfolioChatPanel`.

**Tech Stack:** Next.js 14, React 18, TypeScript, Tailwind CSS, existing frontend API helper, existing FastAPI backend contract for Portfolio Chat.

## Global Constraints

- Keep Next.js.
- Do not migrate to Vite or plain React.
- Do not add React Router.
- Do not change route paths.
- Do not change backend files.
- Do not modify Agent, RAG, Architecture, Admin, or Login pages.
- Add independent homepage components under `frontend/features/homepage/`.
- Reuse `PortfolioChatPanel` without changing its API behavior.
- Keep `frontend/app/page.tsx` as the only route file touched for the homepage.
- Avoid new runtime dependencies unless explicitly approved.

---

## File Structure

Planned file changes:

- Modify: `frontend/app/page.tsx`
  - Responsibility: render the homepage feature composition.
- Create: `frontend/features/homepage/homepage.tsx`
  - Responsibility: compose homepage sections and import `PortfolioChatPanel`.
- Create: `frontend/features/homepage/homepage-data.ts`
  - Responsibility: typed data for hero proof points, module links, workflow steps, projects, and tech stack.
- Create: `frontend/features/homepage/homepage-hero.tsx`
  - Responsibility: first viewport identity and primary calls to action.
- Create: `frontend/features/homepage/homepage-module-links.tsx`
  - Responsibility: route cards for existing modules.
- Create: `frontend/features/homepage/homepage-workflow.tsx`
  - Responsibility: static AI workflow explanation.
- Create: `frontend/features/homepage/homepage-projects.tsx`
  - Responsibility: project/proof cards inspired by the reference portfolio.
- Create: `frontend/features/homepage/homepage-tech-stack.tsx`
  - Responsibility: categorized stack display.

No planned backend file changes.

## Task 1: Add Typed Homepage Data

**Files:**

- Create: `frontend/features/homepage/homepage-data.ts`

**Interfaces:**

- Produces: `heroProofPoints: string[]`
- Produces: `moduleLinks: HomepageLink[]`
- Produces: `workflowSteps: WorkflowStep[]`
- Produces: `portfolioProjects: HomepageProject[]`
- Produces: `techStack: HomepageTech[]`

- [ ] **Step 1: Create the data file**

Add:

```ts
export type HomepageLink = {
  title: string;
  href: string;
  description: string;
  status: string;
};

export type WorkflowStep = {
  label: string;
  title: string;
  description: string;
};

export type HomepageProject = {
  name: string;
  description: string;
  tags: string[];
  href: string;
  proof: string;
};

export type HomepageTech = {
  name: string;
  category: "frontend" | "backend" | "ai" | "storage" | "delivery";
};

export const heroProofPoints = [
  "Next.js product surface",
  "FastAPI AI backend",
  "RAG and citations",
  "Visible agent workflows"
];

export const moduleLinks: HomepageLink[] = [
  {
    title: "Knowledge Agent",
    href: "/agents/knowledge",
    description: "Authenticated RAG workspace for documents, retrieval, citations, and debug traces.",
    status: "RAG track"
  },
  {
    title: "Browser Agent",
    href: "/agents/browser",
    description: "Research workflow demo with visible planning, search steps, and synthesis.",
    status: "Agent demo"
  },
  {
    title: "Office Agent",
    href: "/agents/office",
    description: "Office automation demo with tool execution steps and structured output.",
    status: "Agent demo"
  },
  {
    title: "Architecture",
    href: "/architecture",
    description: "Interactive system graph for frontend, backend, AI, storage, and workflow layers.",
    status: "System map"
  },
  {
    title: "Admin",
    href: "/admin",
    description: "Management surface for users, roles, workspaces, documents, and ingestion state.",
    status: "Ops surface"
  }
];

export const workflowSteps: WorkflowStep[] = [
  {
    label: "01",
    title: "User intent",
    description: "The interface captures a question, workflow request, or document task."
  },
  {
    label: "02",
    title: "Retrieval or tools",
    description: "RAG, mock search, office tools, or architecture data provide grounded context."
  },
  {
    label: "03",
    title: "Model reasoning",
    description: "The backend keeps prompts, providers, permissions, and model calls isolated."
  },
  {
    label: "04",
    title: "Visible result",
    description: "The UI exposes answers, sources, steps, and final structured outputs."
  }
];

export const portfolioProjects: HomepageProject[] = [
  {
    name: "Portfolio Chat",
    description: "A live assistant surface for explaining the portfolio, architecture, and project phases.",
    tags: ["Next.js", "FastAPI", "DeepSeek"],
    href: "/",
    proof: "Shows frontend state, API round trip, session memory, and error handling."
  },
  {
    name: "Knowledge Agent",
    description: "A RAG product track with document lifecycle, permissions, retrieval quality, and citations.",
    tags: ["RAG", "Chroma", "RBAC"],
    href: "/agents/knowledge",
    proof: "Demonstrates enterprise-style retrieval architecture and debug visibility."
  },
  {
    name: "Agent Workflows",
    description: "Browser and Office demos that reveal planning, tool calls, and final outputs.",
    tags: ["Agents", "Tools", "SSE"],
    href: "/agents/browser",
    proof: "Shows workflow decomposition instead of hiding work behind a single answer."
  }
];

export const techStack: HomepageTech[] = [
  { name: "Next.js", category: "frontend" },
  { name: "TypeScript", category: "frontend" },
  { name: "Tailwind CSS", category: "frontend" },
  { name: "FastAPI", category: "backend" },
  { name: "Pydantic", category: "backend" },
  { name: "DeepSeek", category: "ai" },
  { name: "RAG", category: "ai" },
  { name: "Chroma", category: "storage" },
  { name: "Redis", category: "storage" },
  { name: "Docker", category: "delivery" }
];
```

- [ ] **Step 2: Run type check through build**

Run:

```bash
cd frontend
npm run build
```

Expected: build succeeds because the data file is not imported by the route yet. Continue to Task 2.

- [ ] **Step 3: Commit this task**

```bash
git add frontend/features/homepage/homepage-data.ts
git commit -m "feat: add homepage portfolio data"
```

## Task 2: Build Homepage Sections

**Files:**

- Create: `frontend/features/homepage/homepage-hero.tsx`
- Create: `frontend/features/homepage/homepage-module-links.tsx`
- Create: `frontend/features/homepage/homepage-workflow.tsx`
- Create: `frontend/features/homepage/homepage-projects.tsx`
- Create: `frontend/features/homepage/homepage-tech-stack.tsx`

**Interfaces:**

- Consumes: exports from `homepage-data.ts`
- Produces: React components `HomepageHero`, `HomepageModuleLinks`, `HomepageWorkflow`, `HomepageProjects`, and `HomepageTechStack`

- [ ] **Step 1: Create `homepage-hero.tsx`**

Use this structure:

```tsx
import Link from "next/link";

import { heroProofPoints } from "./homepage-data";

export function HomepageHero() {
  return (
    <section className="grid min-h-[calc(100vh-9rem)] gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
      <div className="space-y-6">
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">AI Engineer Portfolio</p>
        <h1 className="max-w-4xl text-4xl font-semibold leading-tight text-ink md:text-6xl">
          Pai Guangguang builds visible AI systems, not black-box demos.
        </h1>
        <p className="max-w-2xl text-lg leading-8 text-ink/70">
          A full-stack portfolio for RAG, agent workflows, backend orchestration, and product-grade AI interfaces.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="#portfolio-chat" className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90">
            Try Portfolio Chat
          </Link>
          <Link href="/architecture" className="border border-ink/15 bg-white/70 px-4 py-2.5 text-sm font-semibold text-ink transition hover:bg-white">
            View Architecture
          </Link>
        </div>
        <div className="flex flex-wrap gap-2">
          {heroProofPoints.map((point) => (
            <span key={point} className="border border-ink/10 bg-white/65 px-3 py-2 text-sm font-medium text-ink/70">
              {point}
            </span>
          ))}
        </div>
      </div>
      <div className="border border-ink/10 bg-ink p-5 text-paper shadow-sm">
        <p className="text-sm font-semibold uppercase text-brass">System proof</p>
        <div className="mt-5 space-y-3 text-sm leading-6">
          <div className="border border-paper/10 bg-paper/10 p-4">Frontend surfaces explain each workflow step.</div>
          <div className="border border-paper/10 bg-paper/10 p-4">Backend services isolate prompts, retrieval, tools, and providers.</div>
          <div className="border border-paper/10 bg-paper/10 p-4">RAG and agent pages remain available through stable routes.</div>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Create `homepage-module-links.tsx`**

Add:

```tsx
import Link from "next/link";

import { moduleLinks } from "./homepage-data";

export function HomepageModuleLinks() {
  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">Existing modules</p>
        <h2 className="mt-2 text-3xl font-semibold text-ink">Explore the AI system surfaces</h2>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {moduleLinks.map((module) => (
          <Link
            key={module.href}
            href={module.href}
            className="border border-ink/10 bg-white/65 p-5 transition hover:border-tide/45 hover:bg-white"
          >
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-xl font-semibold text-ink">{module.title}</h3>
              <span className="border border-tide/20 bg-tide/10 px-2.5 py-1 text-xs font-semibold text-tide">
                {module.status}
              </span>
            </div>
            <p className="mt-3 text-sm leading-7 text-ink/70">{module.description}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Create `homepage-workflow.tsx`**

Add:

```tsx
import { workflowSteps } from "./homepage-data";

export function HomepageWorkflow() {
  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">Workflow visibility</p>
        <h2 className="mt-2 text-3xl font-semibold text-ink">Every AI surface shows how the answer is made</h2>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        {workflowSteps.map((step) => (
          <div key={step.label} className="border border-ink/10 bg-white/65 p-5">
            <p className="text-sm font-semibold text-brass">{step.label}</p>
            <h3 className="mt-3 text-lg font-semibold text-ink">{step.title}</h3>
            <p className="mt-3 text-sm leading-7 text-ink/70">{step.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Create `homepage-projects.tsx`**

Add:

```tsx
import Link from "next/link";

import { portfolioProjects } from "./homepage-data";

export function HomepageProjects() {
  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">Portfolio proof</p>
        <h2 className="mt-2 text-3xl font-semibold text-ink">Projects framed as engineering evidence</h2>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {portfolioProjects.map((project) => (
          <article key={project.name} className="flex min-h-[18rem] flex-col border border-ink/10 bg-white/65 p-5">
            <div className="flex-1">
              <h3 className="text-xl font-semibold text-ink">{project.name}</h3>
              <p className="mt-3 text-sm leading-7 text-ink/70">{project.description}</p>
              <p className="mt-4 border-l-4 border-brass bg-paper px-4 py-3 text-sm leading-6 text-ink/75">
                {project.proof}
              </p>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {project.tags.map((tag) => (
                <span key={tag} className="border border-ink/10 bg-paper px-2.5 py-1 text-xs font-semibold text-ink/65">
                  {tag}
                </span>
              ))}
            </div>
            <Link href={project.href} className="mt-5 text-sm font-semibold text-tide hover:text-tide/80">
              Open project
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Create `homepage-tech-stack.tsx`**

Add:

```tsx
import type { HomepageTech } from "./homepage-data";
import { techStack } from "./homepage-data";

const categoryLabels: Record<HomepageTech["category"], string> = {
  frontend: "Frontend",
  backend: "Backend",
  ai: "AI",
  storage: "Storage",
  delivery: "Delivery"
};

export function HomepageTechStack() {
  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">Stack</p>
        <h2 className="mt-2 text-3xl font-semibold text-ink">Built with production-oriented AI tooling</h2>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {techStack.map((item) => (
          <div key={`${item.category}-${item.name}`} className="border border-ink/10 bg-white/65 p-4">
            <p className="text-xs font-semibold uppercase text-moss">{categoryLabels[item.category]}</p>
            <p className="mt-2 text-base font-semibold text-ink">{item.name}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 6: Run lint or build feedback**

Run:

```bash
cd frontend
npm run build
```

Expected: TypeScript compilation passes once all imports are wired in Task 3.

- [ ] **Step 7: Commit this task**

```bash
git add frontend/features/homepage
git commit -m "feat: add homepage sections"
```

## Task 3: Compose the Homepage Route

**Files:**

- Create: `frontend/features/homepage/homepage.tsx`
- Modify: `frontend/app/page.tsx`

**Interfaces:**

- Consumes: `HomepageHero`, `HomepageWorkflow`, `HomepageModuleLinks`, `HomepageProjects`, `HomepageTechStack`, and `PortfolioChatPanel`
- Produces: default homepage route content at `/`

- [ ] **Step 1: Create `homepage.tsx`**

Add:

```tsx
import { PortfolioChatPanel } from "@/features/portfolio-chat/portfolio-chat-panel";

import { HomepageHero } from "./homepage-hero";
import { HomepageModuleLinks } from "./homepage-module-links";
import { HomepageProjects } from "./homepage-projects";
import { HomepageTechStack } from "./homepage-tech-stack";
import { HomepageWorkflow } from "./homepage-workflow";

export function Homepage() {
  return (
    <div className="space-y-12">
      <HomepageHero />
      <section id="portfolio-chat" className="scroll-mt-24">
        <PortfolioChatPanel />
      </section>
      <HomepageWorkflow />
      <HomepageModuleLinks />
      <HomepageProjects />
      <HomepageTechStack />
    </div>
  );
}
```

- [ ] **Step 2: Replace `frontend/app/page.tsx`**

Replace the current inline homepage with:

```tsx
import { Homepage } from "@/features/homepage/homepage";

export default function HomePage() {
  return <Homepage />;
}
```

- [ ] **Step 3: Verify route imports**

Run:

```bash
cd frontend
npm run build
```

Expected: build completes successfully and `/` is generated as the homepage route.

- [ ] **Step 4: Commit this task**

```bash
git add frontend/app/page.tsx frontend/features/homepage/homepage.tsx
git commit -m "feat: compose redesigned homepage"
```

## Task 4: Optional Homepage Assets From Reference Zip

**Files:**

- Optional create: `frontend/public/homepage/project/*`
- Optional create: `frontend/public/homepage/tech/*`
- Optional modify: `frontend/features/homepage/homepage-data.ts`
- Optional modify: `frontend/features/homepage/homepage-projects.tsx`
- Optional modify: `frontend/features/homepage/homepage-tech-stack.tsx`

**Interfaces:**

- Consumes: selected image files copied from `My_website-main.zip`
- Produces: optional `imageSrc` fields in homepage data

- [ ] **Step 1: Select only displayed assets**

Acceptable first asset set:

```text
My_website-main/src/assets/project/aigc.png
My_website-main/src/assets/project/particles.png
My_website-main/src/assets/project/su7.png
My_website-main/src/assets/tech/typescript.png
My_website-main/src/assets/tech/threejs.svg
My_website-main/src/assets/tech/docker.png
```

- [ ] **Step 2: Copy assets to homepage public folder**

Create target folders:

```powershell
New-Item -ItemType Directory -Force 'frontend\public\homepage\project' | Out-Null
New-Item -ItemType Directory -Force 'frontend\public\homepage\tech' | Out-Null
```

Extract selected files from the archive or copy them from an expanded reference folder. The final paths must be:

```text
frontend/public/homepage/project/
frontend/public/homepage/tech/
```

- [ ] **Step 3: Extend data types**

Add optional image fields:

```ts
export type HomepageProject = {
  name: string;
  description: string;
  tags: string[];
  href: string;
  proof: string;
  imageSrc?: string;
};

export type HomepageTech = {
  name: string;
  category: "frontend" | "backend" | "ai" | "storage" | "delivery";
  imageSrc?: string;
};
```

- [ ] **Step 4: Render images with `next/image`**

Use `Image` only when `imageSrc` exists. Keep alt text equal to the project or technology name.

- [ ] **Step 5: Verify image paths**

Run:

```bash
cd frontend
npm run build
```

Expected: build succeeds and no missing static asset errors appear.

- [ ] **Step 6: Commit this task**

```bash
git add frontend/public/homepage frontend/features/homepage
git commit -m "feat: add homepage portfolio assets"
```

## Task 5: Regression Verification

**Files:**

- No source files required.

**Interfaces:**

- Consumes: completed homepage implementation
- Produces: verification evidence before merge or handoff

- [ ] **Step 1: Confirm backend is untouched**

Run:

```bash
git diff -- backend
```

Expected: no output.

- [ ] **Step 2: Confirm Agent/RAG route files are untouched**

Run:

```bash
git diff -- frontend/app/agents frontend/features/knowledge-agent frontend/features/browser-agent frontend/features/office-agent
```

Expected: no output.

- [ ] **Step 3: Build frontend**

Run:

```bash
cd frontend
npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Smoke test routes manually**

Start:

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000/
http://localhost:3000/agents/knowledge
http://localhost:3000/agents/browser
http://localhost:3000/agents/office
http://localhost:3000/architecture
http://localhost:3000/admin
```

Expected: all paths still resolve. Auth-gated pages may redirect according to existing `RouteGuard` behavior.

- [ ] **Step 5: Commit verification fixes if needed**

```bash
git add frontend/app/page.tsx frontend/features/homepage frontend/public/homepage
git commit -m "fix: polish homepage regression issues"
```

Skip this commit when no verification fixes were made.
