# Task 2: Backend invalidation and manual cache cleanup endpoints

This task depends on Task 1. Use the cache key helpers and cached read paths introduced there.

## Scope

Implement invalidation after write operations and add backend endpoints for manual Redis cleanup:

- clear cached detail entries after create/update/delete/restore-like mutations
- clear cached list prefixes after mutations that change entity collections
- clear dependent user-context cache entries when roles, permissions, workspaces, or user memberships change
- expose admin endpoints that clear list and detail cache entries on demand

## Files

- Modify: `backend/app/services/admin.py`
- Modify: `backend/app/api/v1/admin.py`
- Modify: `backend/app/services/auth.py`
- Modify: `backend/app/storage/cache.py`
- Modify: `backend/tests/test_admin_api.py`
- Modify: `backend/tests/test_auth.py`

## Requirements

- Invalidation must happen after the database transaction commits successfully.
- User changes must invalidate that user's detail key, that user's context key, and the user list prefix.
- Role changes must invalidate the role detail key, role list prefix, and affected user-context keys.
- Permission changes must invalidate the permission detail key, permission list prefix, role caches, and affected user-context keys.
- Workspace changes must invalidate the workspace detail key, workspace list prefix, and affected user-context keys.
- Document changes must invalidate the document detail key and document list prefix.
- Admin cleanup endpoints must require the same management permissions as the affected resource.

## Test-Driven Expectations

Add failing tests first, then implement the minimum code to make them pass.

Suggested focus:

- update and delete operations call `delete` / `delete_prefix` on the expected Redis keys
- manual cleanup endpoints clear the requested list/detail keys
- role and permission updates clear dependent user-context caches

## Context Notes

- Task 1 should already provide `build_entity_cache_key` and `build_entity_cache_prefix`.
- The backend API already groups admin resource endpoints in `backend/app/api/v1/admin.py`.
- Use the existing permission checks and API response envelope patterns already in the repo.

## Report

Write your full report to `.superpowers/sdd/task-2-report.md`.

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
