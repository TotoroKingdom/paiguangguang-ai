# Task 3: Admin frontend Redis cleanup controls

This task depends on Tasks 1 and 2. The backend must already expose cache cleanup endpoints.

## Scope

Add frontend controls for Redis cache cleanup in the admin UI:

- a page-level button that clears the current page's list cache
- a row-level Redis icon button before the existing view/edit/delete actions that clears the selected row's detail cache
- refetch the list or detail data after a successful cleanup

## Files

- Modify: `frontend/lib/admin.ts`
- Modify: `frontend/types/admin.ts`
- Modify: `frontend/features/admin/admin-data-table.tsx`
- Modify: `frontend/features/admin/admin-document-management.tsx`
- Modify: `frontend/features/admin/admin-rbac-management.tsx`
- Modify: `frontend/features/admin/admin-shell.tsx` if shared page-level actions need to live there
- Modify: `frontend/tests` if frontend tests exist in this repo

## Requirements

- The browser must never call Redis directly.
- The frontend should call backend cleanup endpoints only.
- The page-level button should clear the current entity list cache for the current pagination and sort state.
- The row-level button should clear the current entity detail cache for that row's ID.
- After cleanup succeeds, immediately refetch the affected data.

## Test-Driven Expectations

Add failing tests first, then implement the minimum code to make them pass.

Suggested focus:

- cleanup API helpers send the correct payloads to the backend
- the table renders a Redis clear button before the regular row actions
- documents page cleanup refetches the visible list and selection detail
- RBAC pages can reuse the same cleanup API helpers and row action pattern

## Context Notes

- The admin documents page already has a refresh button, pagination, and a detail panel.
- The admin RBAC management page already renders user/role/permission/workspace data and can reuse the same cleanup helper pattern.
- Keep the copy and styling consistent with the existing admin UI until the backend contract is verified.

## Report

Write your full report to `.superpowers/sdd/task-3-report.md`.

Report format:

- What you implemented
- What you tested and test results
- TDD evidence: RED command/output, GREEN command/output
- Files changed
- Self-review findings
- Any issues or concerns

Return only:

- Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commits created
- One-line test summary
- Concerns, if any
- Report file path
