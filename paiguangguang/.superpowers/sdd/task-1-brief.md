# Task 1: Backend auth context cache and admin read caching

This task is part of the admin Redis cache implementation. It is the first backend step and unblocks the later invalidation/cleanup work and the frontend cache-clear buttons.

## Scope

Implement Redis-backed caching for:

- authenticated user context after login
- admin list/detail reads for documents, users, roles, permissions, and workspaces

The backend remains authoritative. Read paths should check Redis first, fall back to the database on miss, and repopulate Redis with the serialized API payload.

## Files

- Modify: `backend/app/storage/cache.py`
- Modify: `backend/app/services/auth.py`
- Modify: `backend/app/services/admin.py`
- Modify: `backend/app/api/v1/auth.py`
- Modify: `backend/app/api/v1/admin.py`
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/schemas/admin.py`
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/tests/test_admin_api.py`
- Modify: `backend/tests/test_cache_adapter.py` if cache helper behavior needs direct coverage

## Requirements

- Cache the authenticated user's personal data and effective authorization data in Redis after login.
- Cache admin list and detail responses for documents, users, roles, permissions, and workspaces after the first successful load.
- Serve subsequent reads from Redis when the relevant cache key is present.
- Keep using the existing Redis-compatible adapter and in-memory fallback behavior.
- Reuse `CacheAdapter` from `backend/app/storage/cache.py`; do not introduce a second cache abstraction.

## Test-Driven Expectations

Add failing tests first, then implement the minimum code to make them pass.

Suggested focus:

- login populates a cached user-context entry
- `/api/v1/auth/me` can be served from cached auth context
- repeated admin list requests hit cache on the second call
- repeated admin detail requests hit cache on the second call

## Context Notes

- The current auth service issues JWTs and reads the current user from the database.
- The admin service currently queries the database directly for all list/detail endpoints.
- `backend/app/storage/cache.py` already exposes a Redis-capable adapter plus `delete_prefix`.
- Existing admin UI code already expects `AdminUserData`, `AdminRoleData`, `AdminPermissionData`, `AdminWorkspaceData`, and `AdminDocumentData` payloads.

## Report

Write your full report to `.superpowers/sdd/task-1-report.md`.

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
