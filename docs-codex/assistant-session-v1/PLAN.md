# Implementation Plan

1. T0: create an origin/main-based isolated worktree and record the baseline.
2. T1: implement FastAPI, SQLite, Alembic, anonymous owner isolation, CRUD, turns, and backend tests.
3. T2: add a typed frontend API/data layer and move conversation/message authority to the server while retaining local non-session state.
4. T3: add internal backend Docker service, named SQLite volume, migration/health startup, proxy configuration, and deployment secrets.
5. T4: run focused backend/frontend tests, lint, production build, and available Playwright checks; record truthful evidence.
6. T5: commit, push, open a PR to main, merge only after checks and deployment safety review, then remove only this task's merged worktree and branch.

## Baseline

- Repository: `C:/AI/paiguangguang-ai`
- Baseline: `origin/main` at `31a28441b327f23ca622c150f11879ee737af44a`
- Task worktree: `C:/AI/paiguangguang-ai-assistant-session-sqlite`
- Feature branch: `feat/assistant-session-sqlite`

