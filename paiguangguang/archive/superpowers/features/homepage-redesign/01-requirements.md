# Homepage Redesign Requirements

## 1. Goal

Redesign the existing `/` homepage into an AI Engineer Portfolio landing experience inspired by `C:\Users\totoro\Downloads\My_website-main.zip`, while keeping this project on the current Next.js App Router architecture.

The homepage should present Pai Guangguang as an AI engineer through a stronger first screen, portfolio project proof, visible AI workflow framing, and entry points to the existing Agent, RAG, Architecture, Admin, and Portfolio Chat surfaces.

## 2. Current Project Context

Current application facts:

- Frontend is `frontend/`, using Next.js 14 App Router, TypeScript, Tailwind CSS, and React 18.
- Homepage route is `frontend/app/page.tsx`.
- Global layout is `frontend/app/layout.tsx`, with `SiteNav`, `AuthProvider`, and `RouteGuard`.
- Existing module routes include `/agents/knowledge`, `/agents/knowledge/debug`, `/agents/browser`, `/agents/office`, `/architecture`, `/admin`, and `/login`.
- Portfolio Chat is already implemented at `frontend/features/portfolio-chat/portfolio-chat-panel.tsx` and calls the backend endpoint `/api/v1/chat/portfolio`.
- Backend is FastAPI under `backend/` and must not be changed for this homepage redesign.

## 3. Reference Project Findings

`My_website-main.zip` is a Vite React portfolio site. It should be used as visual and content inspiration, not as a migration target.

Relevant ideas to reuse:

- A memorable full-screen hero with a strong personal brand signal.
- Section-based portfolio flow: Hero, About, Tech, Works, Contact.
- Project cards with thumbnail image, project name, description, tags, and external link.
- Technology stack presentation with recognizable tool names and icons.
- Motion, depth, and WebGL-inspired visual language suitable for a technical portfolio.
- Mobile-aware component behavior and compact navigation.

Reference parts that must not be copied directly into the current app:

- Vite configuration.
- `BrowserRouter` or `react-router-dom`.
- Root `src/App.jsx` structure.
- Existing reference navbar as a replacement for this app's `SiteNav`.
- Audio controls, global store, and unrelated reference utilities.
- Any route architecture that conflicts with Next.js App Router.

## 4. In Scope

The redesign covers only the homepage experience at `/`.

Required homepage capabilities:

- Replace the current simple homepage composition with a polished AI Engineer Portfolio homepage.
- Preserve and feature the existing `PortfolioChatPanel` as the live V1 proof point.
- Add a hero section that communicates AI engineering, RAG, agent workflows, and full-stack delivery.
- Add a section that summarizes the existing product modules and links to their current routes.
- Add a project/work section inspired by the reference `Works.jsx`, adapted to AI/RAG/Agent portfolio content.
- Add a technology section inspired by the reference `Tech.jsx`, adapted to this stack: Next.js, TypeScript, Tailwind CSS, FastAPI, DeepSeek, Chroma, Redis, Docker, and RAG.
- Add a workflow/proof section showing how the portfolio connects user input, retrieval/tooling, model calls, and visible results.
- Add independent homepage-specific components under `frontend/features/homepage/`.
- Keep shared UI changes minimal and only use shared components when they already fit.

## 5. Out of Scope

The redesign must not:

- Migrate the app from Next.js to Vite or plain React.
- Introduce React Router.
- Change existing route paths.
- Change `frontend/app/layout.tsx` unless a minor metadata update is explicitly approved.
- Change Agent, RAG, Architecture, Admin, Login, or backend behavior.
- Change FastAPI routes, schemas, services, storage, auth, RAG, or task/event code.
- Add new backend endpoints.
- Replace `PortfolioChatPanel` API behavior.
- Require Chroma, Redis, or other backend services merely to render the homepage shell.

## 6. Technical Constraints

- Keep Next.js App Router.
- Keep React 18 and TypeScript.
- Keep Tailwind CSS.
- New homepage components must be independent from Agent/RAG page components.
- `frontend/app/page.tsx` should become a thin route entry that imports the homepage feature composition.
- Static homepage content should live in a typed data module such as `frontend/features/homepage/homepage-data.ts`.
- Client components should be used only where interaction or browser APIs require them.
- Any assets copied from the reference zip should go under `frontend/public/homepage/` or another homepage-scoped asset folder.
- Any new dependencies must be justified by visible homepage value and must not be required by Agent/RAG pages.
- Avoid global CSS changes that alter existing Agent/RAG/Admin page layout.

## 7. UX Requirements

- The first viewport must clearly show the identity: AI Engineer Portfolio for Pai Guangguang.
- The homepage should feel like a usable portfolio product, not a generic marketing page.
- Navigation to existing modules must remain obvious.
- The page must be responsive from mobile to desktop.
- Text must not overlap or overflow in cards, buttons, or hero content.
- The visual style may borrow the reference site's futuristic/WebGL feeling, but should stay readable and professional for an AI engineering portfolio.
- Project cards must expose concrete engineering proof: problem, stack, workflow, and link or route.
- Existing global `SiteNav` should remain the primary top navigation.

## 8. Accessibility Requirements

- Use semantic sections and headings in order.
- Link text and button labels must be descriptive.
- Images must include meaningful alt text or be marked decorative when appropriate.
- Interactive controls must be keyboard reachable.
- Color contrast must remain readable on both light and dark sections.
- Decorative animation must respect readability and should not block content.

## 9. Acceptance Criteria

The homepage redesign is acceptable when:

- `/` renders the new AI Engineer Portfolio homepage.
- Existing routes still render at the same paths.
- `PortfolioChatPanel` still appears and uses the existing backend contract.
- No files under `backend/` are modified.
- No Agent/RAG feature files are modified unless the change is strictly an import-independent type or style fix approved separately.
- The app still builds with `npm run build` from `frontend/`.
- The homepage is usable at mobile, tablet, and desktop widths.
- The implementation can be reverted by removing the homepage feature folder and restoring only `frontend/app/page.tsx`.
