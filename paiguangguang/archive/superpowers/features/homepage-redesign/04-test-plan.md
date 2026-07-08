# Homepage Redesign Test Plan

## 1. Test Scope

This test plan verifies a homepage-only redesign for `/`.

Primary risks:

- Homepage route breaks.
- Existing Agent/RAG/Admin pages regress.
- Backend files or API contracts change accidentally.
- New homepage components introduce global style side effects.
- The homepage becomes unusable on mobile.

## 2. Static Checks

### 2.1 File Boundary Check

Run from repository root:

```bash
git diff --name-only
```

Expected changed files for implementation:

```text
frontend/app/page.tsx
frontend/features/homepage/homepage.tsx
frontend/features/homepage/homepage-data.ts
frontend/features/homepage/homepage-hero.tsx
frontend/features/homepage/homepage-module-links.tsx
frontend/features/homepage/homepage-workflow.tsx
frontend/features/homepage/homepage-projects.tsx
frontend/features/homepage/homepage-tech-stack.tsx
frontend/public/homepage/*
```

The `frontend/public/homepage/*` paths are expected only if static assets are added.

### 2.2 Backend Non-Regression Check

Run:

```bash
git diff -- backend
```

Expected: no output.

### 2.3 Agent/RAG Page Non-Regression Check

Run:

```bash
git diff -- frontend/app/agents frontend/features/knowledge-agent frontend/features/browser-agent frontend/features/office-agent
```

Expected: no output.

### 2.4 Route Path Check

Search for accidental route changes:

```bash
rg '"/agents/knowledge"|"/agents/browser"|"/agents/office"|"/architecture"|"/admin"' frontend
```

Expected: existing route strings remain present, and homepage links use the same paths.

## 3. Build Checks

Run from `frontend/`:

```bash
npm run build
```

Expected:

- Next.js production build completes successfully.
- TypeScript import paths resolve.
- Static assets under `public/homepage/` resolve if used.
- No server component/client component boundary errors are introduced.

If `npm run lint` is available in the local Next.js setup, run:

```bash
npm run lint
```

Expected:

- No lint errors caused by homepage files.

## 4. Manual Route Smoke Tests

Start the frontend:

```bash
cd frontend
npm run dev
```

Open these routes:

```text
http://localhost:3000/
http://localhost:3000/agents/knowledge
http://localhost:3000/agents/knowledge/debug
http://localhost:3000/agents/browser
http://localhost:3000/agents/office
http://localhost:3000/architecture
http://localhost:3000/admin
http://localhost:3000/login
```

Expected:

- `/` renders the redesigned AI Engineer Portfolio homepage.
- Existing routes still load or redirect according to existing auth behavior.
- Global `SiteNav` remains visible and usable.
- Homepage module cards navigate to current routes.
- No page shows a blank screen or runtime error overlay.

## 5. Portfolio Chat Smoke Test

With backend running, use the homepage chat panel:

```text
Ask: What is this project built to demonstrate?
```

Expected:

- The user message appears.
- The assistant reply appears.
- Session status changes from new to active after a successful response.
- Existing error handling still appears if the backend is unreachable.

Backend startup command, if needed:

```bash
cd backend
uv run python -m uvicorn app.main:app --reload --env-file dev.env
```

This redesign must not require backend startup just to render the homepage shell.

## 6. Responsive Visual Checks

Check `/` at these viewport widths:

```text
390 x 844
768 x 1024
1440 x 900
```

Expected:

- Hero text does not overlap with proof cards or navigation.
- Buttons wrap cleanly on mobile.
- Project cards keep readable text and stable spacing.
- Tech stack items do not overflow their containers.
- Portfolio Chat remains usable on mobile.
- No horizontal scrollbar appears from homepage content.

## 7. Accessibility Checks

Manual checks:

- Page has a single primary hero heading.
- Section headings are meaningful and in order.
- Links have descriptive labels.
- Any images have meaningful alt text.
- Keyboard tab order reaches hero links, module links, chat input, chat buttons, and project links.
- Focus outlines are visible through default browser behavior or existing Tailwind focus styles.
- Decorative visual effects do not hide text.

## 8. Performance Checks

Baseline checks:

- Homepage renders without downloading large unused reference assets.
- No audio, shader, or full WebGL reference folders are copied unless used.
- If images are added, they live under `frontend/public/homepage/` and are sized for cards or stack icons.
- The homepage remains readable before Portfolio Chat receives any backend response.

## 9. Acceptance Checklist

The redesign passes when:

- `npm run build` succeeds in `frontend/`.
- `git diff -- backend` is empty.
- `git diff -- frontend/app/agents frontend/features/knowledge-agent frontend/features/browser-agent frontend/features/office-agent` is empty.
- `/` shows the redesigned homepage.
- Existing routes still resolve at the same URLs.
- `PortfolioChatPanel` still uses the existing API behavior.
- Mobile, tablet, and desktop layouts are readable.
- No new dependency has been added without explicit approval.
