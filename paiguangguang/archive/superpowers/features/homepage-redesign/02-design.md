# Homepage Redesign Design

## 1. Design Summary

Build a homepage-specific feature module that turns `/` into a polished AI Engineer Portfolio. The implementation should keep the existing Next.js route, global navigation, auth wrapper, and backend API contracts intact.

The reference portfolio provides the visual direction: a strong hero, section-based storytelling, technology stack display, project cards, and motion/depth. The current app provides the product direction: Portfolio Chat, Knowledge/RAG, Browser Agent, Office Agent, Architecture, and Admin surfaces.

## 2. Architecture

The route stays at `frontend/app/page.tsx`. That file should only import and render a homepage composition component:

```tsx
import { Homepage } from "@/features/homepage/homepage";

export default function HomePage() {
  return <Homepage />;
}
```

Homepage feature files should live under:

```text
frontend/features/homepage/
  homepage.tsx
  homepage-data.ts
  homepage-hero.tsx
  homepage-module-links.tsx
  homepage-workflow.tsx
  homepage-projects.tsx
  homepage-tech-stack.tsx
```

Static assets, if copied from `My_website-main.zip`, should be placed under:

```text
frontend/public/homepage/
  project/
  tech/
  background/
```

This keeps homepage concerns isolated and prevents coupling with Agent/RAG modules.

## 3. Component Responsibilities

| Component | Responsibility |
| --- | --- |
| `Homepage` | Page-level composition and section order. Imports `PortfolioChatPanel` but does not modify it. |
| `HomepageHero` | First viewport identity, concise positioning, key proof points, and primary links. |
| `HomepageModuleLinks` | Cards linking to existing routes without changing route paths. |
| `HomepageWorkflow` | Static visual explanation of AI workflow: user input, retrieval/tools, model response, visible result. |
| `HomepageProjects` | Portfolio project cards inspired by the reference `Works.jsx`, adapted to AI/RAG/Agent proof. |
| `HomepageTechStack` | Stack grid inspired by the reference `Tech.jsx`, adapted to the current project stack. |
| `homepage-data.ts` | Typed static data for modules, projects, stack items, proof points, and workflow steps. |

`PortfolioChatPanel` remains in `frontend/features/portfolio-chat/portfolio-chat-panel.tsx` and is imported as the live V1 module.

## 4. Page Flow

Recommended section order:

1. Hero: "Pai Guangguang AI Engineer Portfolio" with a short statement about full-stack AI systems, RAG, and agent workflows.
2. Proof strip: compact metrics or capability labels such as "Next.js Frontend", "FastAPI Backend", "RAG Pipeline", "Visible Agent Steps".
3. Live Portfolio Chat: reuse the existing panel as the interactive proof point.
4. AI Workflow: static workflow cards showing the portfolio's engineering model.
5. Module Links: route cards for Knowledge Agent, Browser Agent, Office Agent, Architecture, and Admin.
6. Projects: AI/RAG/Agent-focused project cards.
7. Tech Stack: current stack and AI infrastructure.

This flow keeps the page product-focused. It presents the live chat early, then uses the rest of the page to explain the broader system.

## 5. Data Model

Use simple typed arrays instead of scattering content through components.

```ts
export type HomepageLink = {
  title: string;
  href: string;
  description: string;
  status: string;
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
```

The module links must use existing routes only:

- `/agents/knowledge`
- `/agents/browser`
- `/agents/office`
- `/architecture`
- `/admin`

## 6. Visual Direction

The visual direction should borrow the reference project's immersive technical mood while fitting this app's AI platform identity.

Recommended treatment:

- Keep the global `SiteNav`.
- Use a strong hero with layered panels or a lightweight workflow visual, not a separate in-page navbar.
- Use project cards with clear structure: title, description, tags, proof statement, link.
- Use restrained motion if dependencies already exist or if a small dependency is approved.
- Prefer CSS/Tailwind effects before introducing WebGL dependencies.
- If 3D/WebGL is added, make it a progressive enhancement isolated to homepage components.
- Avoid changing `body` or global background rules in a way that affects Agent/RAG/Admin pages.

Color and density:

- The current app uses `ink`, `paper`, `moss`, `clay`, `brass`, and `tide`.
- The homepage may introduce a darker section palette locally, but should not become a one-color purple clone of the reference site.
- Cards should stay readable and avoid nested card layouts.

## 7. Asset Strategy

Use the reference zip as an asset source only when the asset directly supports this homepage:

- Project thumbnails from `src/assets/project/` can be copied selectively into `frontend/public/homepage/project/`.
- Tech icons from `src/assets/tech/` can be copied selectively into `frontend/public/homepage/tech/`.
- Large WebGL models, audio files, and shader folders should not be copied in the first homepage redesign.

The first implementation can also use text-only stack cards to reduce dependency and asset risk.

## 8. Dependency Strategy

Baseline implementation should not require new runtime dependencies.

Allowed without approval:

- Next.js
- React
- TypeScript
- Tailwind CSS
- Existing `PortfolioChatPanel`

Requires explicit approval before implementation:

- `framer-motion`
- `three`
- `@react-three/fiber`
- `@react-three/drei`
- `react-tilt`
- Any package copied from the reference Vite project

This keeps the homepage redesign from silently expanding the app's dependency surface.

## 9. Data Flow

Most homepage data is static:

```text
homepage-data.ts -> homepage components -> rendered route /
```

Portfolio Chat keeps its existing flow:

```text
PortfolioChatPanel -> frontend/lib/api.ts -> /api/v1/chat/portfolio -> existing backend service
```

No new backend data flow is introduced.

## 10. Risk Controls

| Risk | Control |
| --- | --- |
| Route regression | Only edit `frontend/app/page.tsx`; do not touch other `frontend/app/**/page.tsx` files. |
| Agent/RAG visual regression | Keep styles local to homepage components and Tailwind classes. |
| Backend coupling | Do not add new API calls; reuse `PortfolioChatPanel` unchanged. |
| Dependency creep | Start with CSS/Tailwind implementation and static content. |
| Asset bloat | Copy only selected images/icons that are displayed on the homepage. |
| Global layout side effects | Avoid changing `layout.tsx`, `RouteGuard`, `SiteNav`, or `globals.css` unless approved. |

## 11. Review Checklist

Before implementation is accepted:

- `frontend/features/homepage/` contains all new homepage-specific components.
- `frontend/app/page.tsx` remains a thin route wrapper.
- Existing Agent/RAG/Admin route files are unchanged.
- Backend diff is empty.
- Homepage links point to existing routes.
- The page remains readable without backend services running.
