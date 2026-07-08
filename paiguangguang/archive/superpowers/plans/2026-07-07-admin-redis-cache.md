# Admin Redis Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cache authenticated user context and admin entity reads in Redis, invalidate cached data after writes, and add frontend controls to clear list/detail cache entries on demand.

**Architecture:** Keep the backend authoritative for all Redis access. Extend the existing cache adapter and service layer so auth and admin reads can hit Redis first, then add targeted invalidation and explicit cleanup endpoints for writes and manual cache clears. After the backend contract is stable, wire the admin frontend to those cleanup endpoints and refetch the affected data.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Redis-compatible cache adapter, Pytest, Next.js App Router, React, TypeScript, Tailwind CSS.

## Global Constraints

- Cache the authenticated user's personal data and effective authorization data in Redis after login.
- Cache admin list and detail responses for documents, users, roles, permissions, and workspaces after the first successful load.
- Serve subsequent reads from Redis when the relevant cache key is present.
- Invalidate Redis entries immediately after write operations that change the cached data.
- The admin UI exposes a page-level Redis cleanup button and row-level Redis cleanup buttons, but the browser never talks to Redis directly.
- The cache layer must keep the existing Redis-compatible adapter and in-memory fallback behavior.
- Use the existing `CacheAdapter` in `backend/app/storage/cache.py` rather than introducing a second cache abstraction.

---

### Task 1: Backend auth context cache and admin read caching

**Files:**
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

**Interfaces:**
- Consumes: `AuthService.login`, `AuthService.get_current_user`, `user_to_data`, `AdminService.list_users`, `AdminService.get_user`, `AdminService.list_roles`, `AdminService.get_role`, `AdminService.list_permissions`, `AdminService.get_permission`, `AdminService.list_workspaces`, `AdminService.get_workspace`, `AdminService.list_documents`, `AdminService.get_document`, `CacheAdapter`, `get_cache_adapter`.
- Produces: Redis-backed user-context caching, Redis-backed admin list/detail caching, and reusable cache key helpers for later invalidation and cleanup work.

- [ ] **Step 1: Add failing tests for auth context caching and repeated admin reads**

```python
def test_auth_me_uses_cached_context(monkeypatch, tmp_path):
    cache = InMemoryCacheAdapter()
    monkeypatch.setattr("app.services.auth.get_cache_adapter", lambda settings=None: cache)
    response = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "Secret123!"})
    assert response.status_code == 200
    assert cache.get("admin:auth:user-context:admin@example.com") is not None


def test_admin_list_and_detail_cache_hits(monkeypatch, tmp_path):
    cache = InMemoryCacheAdapter()
    monkeypatch.setattr("app.services.admin.get_cache_adapter", lambda settings=None: cache)
    first = client.get("/api/v1/admin/users?page=1&page_size=20&sort_by=created_at&sort_order=desc", headers=headers)
    second = client.get("/api/v1/admin/users?page=1&page_size=20&sort_by=created_at&sort_order=desc", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert cache.get("admin:users:list:entity=users:page=1:page_size=20:sort_by=created_at:sort_order=desc") is not None
```

- [ ] **Step 2: Run the focused auth/admin cache tests and confirm they fail**

Run: `pytest backend/tests/test_auth.py backend/tests/test_admin_api.py -k "cache or auth or admin" -v`
Expected: fail because auth context and admin entity responses are still always rebuilt from the database.

- [ ] **Step 3: Implement cache key helpers and cached read paths**

```python
# backend/app/storage/cache.py
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class EntityCacheKeyContext:
    entity: str
    entity_id: str | None = None
    page: int | None = None
    page_size: int | None = None
    sort_by: str | None = None
    sort_order: str | None = None
    user_id: str | None = None


def build_entity_cache_key(namespace: str, context: EntityCacheKeyContext) -> str:
    parts = [namespace.strip(":")]
    parts.append(f"entity={context.entity}")
    if context.entity_id is not None:
        parts.append(f"id={context.entity_id}")
    if context.page is not None:
        parts.append(f"page={context.page}")
    if context.page_size is not None:
        parts.append(f"page_size={context.page_size}")
    if context.sort_by is not None:
        parts.append(f"sort_by={context.sort_by}")
    if context.sort_order is not None:
        parts.append(f"sort_order={context.sort_order}")
    if context.user_id is not None:
        parts.append(f"user={context.user_id}")
    return ":".join(parts)


def build_entity_cache_prefix(namespace: str, entity: str) -> str:
    return f"{namespace.strip(':')}:entity={entity}"
```

```python
# backend/app/services/auth.py
def login(self, session: Session, request: LoginRequest) -> AuthTokenData:
    user = self.authenticate_user(session, request.email, request.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    self.cache_user_context(user)
    return AuthTokenData(access_token=self.create_access_token(user))
```

```python
# backend/app/services/admin.py
def list_users(self, session: Session, *, page: int = 1, page_size: int = 20, sort_by: str | None = None, sort_order: str = "desc") -> AdminPagedData[AdminUserData]:
    cache_key = build_entity_cache_key(
        "admin:users:list",
        EntityCacheKeyContext(entity="users", page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order),
    )
    cached = self.cache.get(cache_key)
    if cached is not None:
        return AdminPagedData.model_validate(cached)
    data = _build_paged_data(
        session,
        User,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        allowed_sort_by={"email", "display_name", "is_active", "updated_at", "created_at"},
        default_sort_by="created_at",
        item_mapper=_user_to_admin_data,
    )
    self.cache.set(cache_key, data.model_dump(), ttl_seconds=600)
    return data
```

- [ ] **Step 4: Re-run the focused tests until they pass**

Run: `pytest backend/tests/test_auth.py backend/tests/test_admin_api.py -k "cache or auth or admin" -v`
Expected: pass, with repeated list/detail requests served from Redis when present.

- [ ] **Step 5: Commit**

```bash
git add backend/app/storage/cache.py backend/app/services/auth.py backend/app/services/admin.py backend/app/api/v1/auth.py backend/app/api/v1/admin.py backend/app/schemas/auth.py backend/app/schemas/admin.py backend/tests/test_auth.py backend/tests/test_admin_api.py backend/tests/test_cache_adapter.py
git commit -m "feat: cache auth context and admin reads in redis"
```

### Task 2: Backend invalidation and manual cache cleanup endpoints

**Files:**
- Modify: `backend/app/services/admin.py`
- Modify: `backend/app/api/v1/admin.py`
- Modify: `backend/app/services/auth.py`
- Modify: `backend/app/storage/cache.py`
- Modify: `backend/tests/test_admin_api.py`
- Modify: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: the entity cache helpers introduced in Task 1, write methods in `AdminService`, and the authenticated user context cache from `AuthService`.
- Produces: targeted invalidation after writes, plus backend endpoints that clear list and detail caches for a chosen admin entity.

- [ ] **Step 1: Add failing tests for write-triggered invalidation and cleanup endpoints**

```python
def test_admin_writes_invalidate_list_and_detail_cache(monkeypatch, tmp_path):
    cache = InMemoryCacheAdapter()
    monkeypatch.setattr("app.services.admin.get_cache_adapter", lambda settings=None: cache)
    updated = client.patch(f"/api/v1/admin/users/{user_id}", headers=headers, json={"display_name": "Updated"})
    deleted = client.delete(f"/api/v1/admin/documents/{document_id}", headers=headers)
    assert updated.status_code == 200
    assert deleted.status_code == 200
    assert cache.get(f"admin:users:detail:entity=users:id={user_id}") is None
    assert cache.get("admin:users:list:entity=users:page=1:page_size=20:sort_by=created_at:sort_order=desc") is None


def test_admin_cache_cleanup_endpoints_clear_requested_entries(monkeypatch, tmp_path):
    response = client.post(
        "/api/v1/admin/cache/clear-list",
        headers=headers,
        json={"entity": "users", "page": 1, "page_size": 20, "sort_by": "created_at", "sort_order": "desc"},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"cleared": "list", "entity": "users"}

    response = client.post(
        "/api/v1/admin/cache/clear-detail",
        headers=headers,
        json={"entity": "users", "entity_id": user_id},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"cleared": "detail", "entity": "users", "entity_id": user_id}
```

- [ ] **Step 2: Run the focused invalidation/cleanup tests and confirm they fail**

Run: `pytest backend/tests/test_admin_api.py -k "cache or invalidate or clear" -v`
Expected: fail because write paths still do not clear Redis keys and no cleanup endpoints exist yet.

- [ ] **Step 3: Implement invalidation hooks and cleanup endpoints**

```python
# backend/app/services/admin.py
def _invalidate_entity_cache(self, session: Session, entity: str, entity_id: str | None = None) -> None:
    if entity_id is not None:
        self.cache.delete(build_entity_cache_key(f"admin:{entity}:detail", EntityCacheKeyContext(entity=entity, entity_id=entity_id)))
    self.cache.delete_prefix(build_entity_cache_prefix(f"admin:{entity}:list", entity))


def clear_entity_list_cache(self, entity: str, *, page: int | None = None, page_size: int | None = None, sort_by: str | None = None, sort_order: str | None = None) -> None:
    self.cache.delete_prefix(build_entity_cache_prefix(f"admin:{entity}:list", entity))


def clear_entity_detail_cache(self, entity: str, entity_id: str) -> None:
    self.cache.delete(build_entity_cache_key(f"admin:{entity}:detail", EntityCacheKeyContext(entity=entity, entity_id=entity_id)))
```

```python
# backend/app/api/v1/admin.py
@router.post("/cache/clear-list")
def clear_admin_list_cache(request: AdminCacheClearListRequest, service: AdminService = Depends(get_admin_service), current_user: User = Depends(get_current_user), session: Session = Depends(get_db_session), rbac_service: RBACService = Depends(get_rbac_service)) -> ApiResponse[dict[str, str]]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    return ApiResponse(data=service.clear_entity_list_cache(request.entity, page=request.page, page_size=request.page_size, sort_by=request.sort_by, sort_order=request.sort_order))


@router.post("/cache/clear-detail")
def clear_admin_detail_cache(request: AdminCacheClearDetailRequest, service: AdminService = Depends(get_admin_service), current_user: User = Depends(get_current_user), session: Session = Depends(get_db_session), rbac_service: RBACService = Depends(get_rbac_service)) -> ApiResponse[dict[str, str]]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    return ApiResponse(data=service.clear_entity_detail_cache(request.entity, request.entity_id))
```

- [ ] **Step 4: Re-run the focused tests until they pass**

Run: `pytest backend/tests/test_admin_api.py -k "cache or invalidate or clear" -v`
Expected: pass, and mutation tests should show the correct Redis keys being removed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/admin.py backend/app/api/v1/admin.py backend/app/storage/cache.py backend/tests/test_admin_api.py backend/tests/test_auth.py
git commit -m "feat: invalidate admin redis caches after writes"
```

### Task 3: Admin frontend Redis cleanup controls

**Files:**
- Modify: `frontend/lib/admin.ts`
- Modify: `frontend/types/admin.ts`
- Modify: `frontend/features/admin/admin-data-table.tsx`
- Modify: `frontend/features/admin/admin-document-management.tsx`
- Modify: `frontend/features/admin/admin-rbac-management.tsx`
- Modify: `frontend/features/admin/admin-shell.tsx` if shared page-level actions need to live there
- Modify: `frontend/tests` if frontend tests exist in this repo

**Interfaces:**
- Consumes: the backend cleanup endpoints from Task 2, the admin list/detail data shapes already used by the document and RBAC screens, and the current pagination/sort state on each page.
- Produces: a page-level list cache clear action and row-level detail cache clear action that refetch the affected page after success.

- [ ] **Step 1: Add failing frontend assertions for the cleanup buttons and refetch behavior**

```tsx
// The admin page toolbar should render a Redis clear button.
// Each table action row should render a Redis icon button before view/edit/delete.
// Clicking the buttons should call the new admin cleanup API helpers.
<button type="button" onClick={handleClearCurrentListCache}>清理本页 Redis 缓存</button>
<button type="button" aria-label="清理当前行 Redis 缓存" onClick={() => handleClearRowCache(row.entityId)}>🧹</button>
```

- [ ] **Step 2: Run the frontend tests or typecheck and confirm the failures**

Run: `cd frontend; npm run lint`
Expected: fail because the cleanup helpers, buttons, and handler wiring do not exist yet.

- [ ] **Step 3: Implement the cleanup API helpers and UI wiring**

```ts
// frontend/lib/admin.ts
export function clearAdminEntityListCache(request: { entity: string; page?: number; pageSize?: number; sortBy?: string; sortOrder?: "asc" | "desc" }) {
  return postJson<{ cleared: "list"; entity: string }, typeof request>("/api/v1/admin/cache/clear-list", request, {
    token: getStoredAuthToken(),
  });
}


export function clearAdminEntityDetailCache(request: { entity: string; entityId: string }) {
  return postJson<{ cleared: "detail"; entity: string; entity_id: string }, typeof request>("/api/v1/admin/cache/clear-detail", request, {
    token: getStoredAuthToken(),
  });
}
```

```tsx
// frontend/features/admin/admin-data-table.tsx
export function AdminDataTable<T>({ leadingActionCell, rows, getRowKey }: { leadingActionCell?: (row: T) => ReactNode; rows: T[]; getRowKey: (row: T) => string }) {
  return (
    <table>
      <tbody>{rows.map((row) => <tr key={getRowKey(row)}><td>{leadingActionCell?.(row)}</td></tr>)}</tbody>
    </table>
  );
}
```

```tsx
// frontend/features/admin/admin-document-management.tsx
async function handleClearCurrentListCache() {
  await clearAdminEntityListCache({
    entity: "documents",
    page,
    pageSize,
    sortBy,
    sortOrder,
  });
  await loadData(selectedDocumentId);
}

async function handleClearRowCache(documentId: string) {
  await clearAdminEntityDetailCache({ entity: "documents", entityId: documentId });
  await loadData(documentId);
}
```

- [ ] **Step 4: Re-run frontend verification until green**

Run: `cd frontend; npm run lint`
Expected: pass, and the Redis cleanup controls should appear and refetch data after success.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/admin.ts frontend/types/admin.ts frontend/features/admin/admin-data-table.tsx frontend/features/admin/admin-document-management.tsx frontend/features/admin/admin-rbac-management.tsx frontend/features/admin/admin-shell.tsx
git commit -m "feat: add admin redis cleanup controls"
```

## Self-Review

- Spec coverage: Task 1 covers auth context caching and cached reads for all five admin entities. Task 2 covers invalidation after writes and manual cleanup endpoints. Task 3 covers the frontend controls and refetch flow.
- Placeholder scan: no placeholder markers remain in the concrete task steps.
- Type consistency: the plan uses one set of helper names for entity list/detail cache keys and one set of admin cleanup request shapes so the later tasks can depend on them without renaming.
