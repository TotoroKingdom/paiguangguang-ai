# Admin Redis Cache Design Spec

## Overview

This change set adds Redis-backed caching for authentication context and admin data in the backend, plus Redis cache cleanup controls in the admin frontend.

The scope is split into two layers:

1. Backend responsibilities:
   - cache the logged-in user's personal and authorization context in Redis
   - cache admin list and detail payloads for documents, users, roles, permissions, and workspaces
   - invalidate the correct Redis keys after create, update, delete, restore, or similar write operations
2. Frontend responsibilities:
   - expose a global Redis cleanup button for the currently visible admin page
   - expose row-level Redis cleanup buttons next to view, edit, and delete actions so a specific entity cache can be cleared on demand

The implementation should reuse the existing cache abstraction in `backend/app/storage/cache.py` instead of introducing a parallel caching layer.

## Goals

- Cache the authenticated user's personal data and effective authorization data in Redis after login.
- Cache admin list and detail responses for documents, users, roles, permissions, and workspaces after the first successful load.
- Serve subsequent reads from Redis when the relevant cache key is present.
- Invalidate Redis entries immediately after write operations that change the cached data.
- Provide frontend controls to clear the current page's list cache and the selected row's detail cache.
- Keep the design compatible with the current FastAPI, SQLAlchemy, and Next.js structure in the repository.

## Current State

- Authentication currently issues a JWT and fetches the current user from the database on each request.
- Admin list and detail endpoints query the database directly every time.
- The backend already includes a Redis-compatible cache adapter with in-memory fallback.
- The admin frontend already has list/detail views for documents and RBAC management, but no Redis cleanup controls.
- The repository already has admin types, API helpers, and reusable data table components that can support the new cleanup actions.

## Proposed Design

### 1. Authentication Context Cache

After a successful login, the backend should materialize a compact user context object and store it in Redis.

The cached payload should include:

- user identity fields: `id`, `email`, `display_name`, `is_active`
- effective roles
- effective permissions
- accessible workspace IDs
- a version or timestamp field that allows safe refresh after permission changes

Cache behavior:

- The login flow writes the cache before returning the access token response.
- `GET /api/v1/auth/me` and authorization checks should prefer the cached user context when available.
- If the cache entry is missing, the backend may reconstruct the context from the database and repopulate Redis.
- Any user, role, permission, or workspace change that affects the user's effective access should invalidate the corresponding user-context key.

### 2. Admin Entity Cache

The following entities must use Redis-backed read caching:

- documents
- users
- roles
- permissions
- workspaces

For each entity, the backend should maintain two cache layers:

- list cache
- detail cache

List cache rules:

- Key inputs must include entity name, page, page size, sort field, sort order, and any future filter parameters.
- The first read after a miss loads from the database and stores the serialized page response in Redis.
- A cache hit returns the stored page response directly without hitting the database.

Detail cache rules:

- Key inputs must include entity name and stable entity identifier.
- A miss loads the row, converts it to the API response shape, and stores it in Redis.
- A hit returns the cached detail payload directly.

### 3. Cache Invalidation

Write operations must invalidate relevant Redis keys after the database transaction commits successfully.

General rules:

- create, update, delete, restore, and reindex-like mutations must clear the affected detail key
- the same mutation must also clear the relevant list cache prefix so page 1, page 2, and any sorted variants do not serve stale rows
- relationship changes must invalidate dependent caches, not just the directly edited entity

Dependency-aware invalidation:

- user changes must invalidate that user's detail key, that user's context key, and the user list prefix
- role changes must invalidate the role detail key, role list prefix, and affected user context keys
- permission changes must invalidate the permission detail key, permission list prefix, role caches, and affected user context keys
- workspace changes must invalidate the workspace detail key, workspace list prefix, and affected user context keys
- document changes must invalidate the document detail key and document list prefix

The invalidation path should prefer targeted key deletion first. Prefix deletion is acceptable for list caches because list cache keys are already namespaced by entity and query parameters.

### 4. Cache TTL and Safety

Redis should not become an unbounded permanent store.

Policy:

- user context cache: TTL required
- admin list cache: TTL required
- admin detail cache: TTL required

The exact TTL values can follow the backend team's existing cache conventions, but they must be explicit and centralized in configuration or a cache policy module.

Safety rules:

- Redis remains the primary backend when configured and reachable.
- If Redis is unavailable, the existing in-memory fallback may still be used for local development.
- The active cache backend should remain observable through logs or a debug endpoint so developers can tell whether Redis is actually active.

### 5. Frontend Redis Cleanup Controls

The admin UI should expose cache cleanup actions, but the frontend must not talk to Redis directly.

Required controls:

- Top-right page-level button:
  - clears the list cache for the currently visible admin page
  - maps to the current entity and the current pagination/sort context
- Row-level Redis icon button:
  - placed before the existing view, edit, and delete actions
  - clears the detail cache for the current row's entity ID

After a cleanup action succeeds, the frontend should refetch the affected data so the visible page immediately reflects the current state.

The icon button is a UI affordance only. The actual cache deletion happens through a backend endpoint.

### 6. Backend Cache Admin API

Add backend endpoints that accept cache cleanup requests from the admin frontend.

The backend API should support:

- clearing list cache entries for a specific entity and query context
- clearing detail cache entries for a specific entity and ID
- optionally clearing the current admin user's context cache when needed

Authorization:

- only admin users with the relevant management permissions may call these endpoints

Response behavior:

- return a simple success payload indicating what was cleared
- the frontend can then reload the list or detail data

## Implementation Notes

- The existing `CacheAdapter` in `backend/app/storage/cache.py` should be extended rather than replaced.
- Cache key builders should live close to the services that use them so the namespace and invalidation rules stay readable.
- Admin list cache payloads should store the same shaped object returned by the API, including pagination metadata.
- Detail cache payloads should store the same shaped object returned by the API.
- Login context caching should prefer a normalized, reusable shape that can also support future admin dashboards or session introspection.

## Testing Plan

Backend tests:

- login writes a Redis user-context cache entry
- `GET /api/v1/auth/me` can read the cached user context
- admin list endpoints hit Redis on a repeated request
- admin detail endpoints hit Redis on a repeated request
- write operations invalidate the expected detail and list keys
- role and permission updates invalidate dependent user-context keys
- cache cleanup endpoints remove the requested keys

Frontend tests:

- the page-level Redis cleanup button calls the correct backend cleanup action
- the row-level Redis icon button clears the correct entity detail cache
- after cleanup, the list or detail view refetches
- the existing list/detail actions still render correctly next to the new Redis control

## Acceptance Criteria

- Logged-in user context data is cached in Redis and refreshed when related authorization data changes.
- Admin lists and details are cached in Redis after the first successful load.
- Subsequent reads reuse cached data until invalidated or expired.
- Mutations clear the correct Redis keys without requiring a manual full cache purge.
- The admin UI exposes both a current-page cache clear action and a per-row detail cache clear action.
- Cache cleanup actions are backend-driven and do not require direct Redis access from the browser.

## Scope Notes

- This spec intentionally does not change the existing JWT format unless the implementation later proves that a small token payload is insufficient.
- This spec does not introduce a new caching product or a second cache abstraction.
- The first implementation pass should focus on the five requested admin entities and the authenticated user context only.
