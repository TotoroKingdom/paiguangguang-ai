# Acceptance Record

Date: 2026-11-07 (Asia/Shanghai)

## Completed scope

- FastAPI + SQLAlchemy 2 + Alembic SQLite persistence for conversations and messages.
- Signed HttpOnly SameSite anonymous owner cookie and owner-scoped CRUD.
- Empty conversation creation, metadata list/search/cursor pagination, direct URL loading, rename with optimistic version conflict, delete with FK cascade, idempotent `clientTurnId` turns, final message status persistence, and orphaned `generating` recovery.
- Typed same-origin frontend API client and Provider integration. Sessions/messages are server-owned; drafts, files, skills, favorites, connectors, and other existing demo state remain local.
- One-time legacy import keeps the old `paiguangguang.assistant.v1` key and excludes the six fixed seed conversations. Migration keys and turn keys are idempotent.
- Next rewrite proxy, internal backend Compose service, SQLite named volume, migration-on-start, health check, production secret fail-fast, and dual-image GitHub Actions deployment.

## Automated verification

| Area | Command | Result |
| --- | --- | --- |
| Backend | `backend/.venv/Scripts/python.exe -m pytest tests -q` | PASS: 12 passed, 1 deprecation warning |
| Backend syntax | `backend/.venv/Scripts/python.exe -m compileall -q app alembic` | PASS |
| Migration | `backend/.venv/Scripts/alembic.exe upgrade head` against isolated SQLite | PASS |
| Frontend typecheck | `frontend/npx tsc --noEmit` | PASS during production build; standalone run requires generated `.next/types` after a clean build |
| Frontend unit/component | `frontend/npm test` | PASS: 19 test files, 76 tests; React act warnings in existing async test setup only |
| Frontend lint | `frontend/npm run lint` | PASS: no warnings/errors |
| Frontend production build | `frontend/npm run build` | PASS: Next.js 14.2.35 |
| Session Playwright | `frontend/npx playwright test e2e/assistant-session-v1.spec.ts --project=desktop` with local FastAPI + Next proxy | PASS: 3 passed |
| Full Playwright regression | `frontend/npx playwright test --project=desktop --project=mobile` with Playwright-managed FastAPI + Next proxy | PASS: 38 passed after updating legacy assertions to the server-session contract; no remaining failures |
| Compose config | `docker compose --env-file .env.example config` | PASS |
| Docker images | backend and frontend `docker build` commands with a temporary smoke tag | PASS: both images built locally |
| Container smoke | temporary Compose project with isolated named volume | PASS: Alembic startup, backend health, frontend same-origin `/api/v1/health`, create/turn, backend recreate, and same-owner read after recreate |
| GitHub Checks | PR #9 `Assistant session CI` run 1 | PASS: Backend tests and Frontend tests and E2E |

## Browser scenarios observed

- New empty server conversation receives a UUID and opens `/assistant/chat/{id}`.
- First user turn and simulated final reply survive refresh and direct URL load.
- Rename and delete persist through the API; deleted URL returns the not-found view.
- Stop persists `stopped`; refresh preserves it; retry updates the same assistant message without duplicating the user turn.
- Two isolated browser contexts cannot read each other's conversation; the API returns 404 for the foreign owner.
- The existing assistant UI retains the explicit simulated-reply label; no real LLM/MCP execution was added.

## Deployment status and residual risk

- Local deployment configuration was validated syntactically and the local FastAPI/Next proxy path was exercised. Both production images and a temporary Compose smoke project were built and tested; the temporary images/containers/volume were removed afterward. The production GitHub Actions workflow was not triggered from this worktree, so GHCR push, server SSH deployment, actual production backup/restore, and production health status remain unobserved.
- Production requires `ASSISTANT_OWNER_COOKIE_SECRET` (at least 32 characters), `ASSISTANT_ALLOWED_ORIGINS`, and HTTPS `ASSISTANT_OWNER_COOKIE_SECURE=true`; the workflow fails before `docker compose up` when these are absent.
- Generating recovery is conservative: recent generating messages remain generating for concurrent tabs; only messages older than `ASSISTANT_ORPHAN_GENERATION_AFTER_SECONDS` become stopped.
- Anonymous owner cookies provide browser isolation, not authentication or sensitive-data protection. Cross-device sync and account login remain out of scope.
- Manual visual acceptance beyond the automated desktop session scenarios was not claimed; the existing site/3D routes were covered by the pre-existing regression suite and production build.

## Branch consolidation verification

Date: 2026-11-07 (Asia/Shanghai)

- `main` was merged into `dev` without dropping the independent Three.js history; the later `/lab/3d/robot` implementation and `/threejs` redirect were retained.
- PR #9's six commits were merged into `dev` with the SQLite API, Alembic migration, frontend session client, CI, backup, rollback, and dual-image deployment configuration.
- Backend: `12 passed`; frontend: `19` test files and `76` tests passed; TypeScript, ESLint, and the Next.js production build passed.
- Assistant session Playwright: `6 passed` across desktop and mobile, including create, refresh persistence, rename/delete, stop/retry, and browser isolation.
- Local Docker images built from both Dockerfiles. Compose startup, production fail-fast configuration, frontend-to-backend health, session/turn persistence, backend restart persistence, and SQLite backup integrity were observed locally.
- Windows-built containers initially failed because `docker-entrypoint.sh` had CRLF line endings; the Dockerfile now normalizes the entrypoint and `.gitattributes` enforces LF for shell files.
- `npm audit --omit=dev` against the public npm registry reports 1 critical and 3 high production dependency findings. The critical finding is in Next.js 14.2.35 and the available fix is a breaking major upgrade; this release does not claim that dependency risk is resolved.
- Production publish remains **BLOCKED**: the repository lacks `ASSISTANT_OWNER_COOKIE_SECRET` and `ASSISTANT_ALLOWED_ORIGINS`; the production server exposes no HTTPS listener or certificate, its Nginx configuration only serves a default HTTP host on port 80, and the deploy account has no usable non-interactive sudo. No `dev` → `main` merge or production deployment was performed.

