# Admin Management Feature Plan

## Purpose

This document is the execution guide for extending the admin management area. Future Codex runs should follow this file as the source of truth and avoid modifying unrelated modules.

## Hard Scope Boundaries

- Only change admin management files and directly required shared admin helpers.
- Do not refactor unrelated agent, RAG query, portfolio chat, architecture graph, office agent, browser agent, auth UI, or non-admin navigation modules.
- Do not change database tables unrelated to admin users, roles, permissions, workspaces, documents, or ingestion jobs.
- Do not introduce a `user_permissions` table. User permissions must be derived through `user -> role -> permission` relationships.
- Every completed implementation task must be committed with `git commit` before starting the next task.
- Keep commits small and task-scoped. Do not combine backend pagination, frontend layout, and modal work in one commit.

## Confirmed Product Decisions

- Deletion strategy: hard delete and clean related join-table records.
- Activation behavior: only users and documents have activation or restore actions.
- Admin navigation: route-based pages.
- Relationship selector UI: frontend-derived tree lists, without adding database parent-child hierarchy.
- User permissions: read-only in user detail, calculated from assigned roles.

## Target Routes

- `/admin`: redirect to `/admin/documents` or render the documents page by default.
- `/admin/documents`: document management.
- `/admin/users`: user management.
- `/admin/roles`: role management.
- `/admin/permissions`: permission management.
- `/admin/workspaces`: workspace management.

Each route uses a shared admin layout with a left menu tree and a right content panel. The active menu item must match the current route.

## Backend API Design

All admin list endpoints should support backend pagination and sorting:

- `page`: integer, default `1`, minimum `1`.
- `page_size`: integer, default `20`, maximum `100`.
- `sort_by`: string, resource-specific allowlist.
- `sort_order`: `asc` or `desc`, default chosen per resource.

List endpoints should return a paged payload inside the existing API response wrapper:

```json
{
  "data": {
    "items": [],
    "total": 123,
    "page": 1,
    "page_size": 20
  }
}
```

Allowed sort fields:

- Documents: `title`, `status`, `owner_user_id`, `workspace_id`, `updated_at`, `created_at`.
- Users: `email`, `display_name`, `is_active`, `updated_at`, `created_at`.
- Roles: `name`, `updated_at`, `created_at`.
- Permissions: `name`, `updated_at`, `created_at`.
- Workspaces: `slug`, `name`, `is_default`, `updated_at`, `created_at`.
- Ingestion jobs: `status`, `document_id`, `created_at`, `updated_at`.

Invalid `sort_by` values must return HTTP 400. Do not pass arbitrary client field names into SQLAlchemy ordering.

## Backend Data and Service Rules

Use the existing join tables:

- `user_roles` for user-role assignments.
- `role_permissions` for role-permission assignments.
- `workspace_memberships` for user-workspace assignments.

Do not add direct user-permission storage.

User detail responses should include:

- Basic user fields.
- Assigned role names.
- Assigned workspace IDs or slugs.
- Effective permissions derived from the user's assigned roles.

Role detail responses should include:

- Basic role fields.
- Assigned permission names.

Delete behavior:

- Delete user: remove `user_roles` and `workspace_memberships`, then delete the user.
- Delete role: remove `user_roles` and `role_permissions`, then delete the role.
- Delete permission: remove `role_permissions`, then delete the permission.
- Delete workspace: remove `workspace_memberships`, then delete the workspace.
- Delete document: hard delete the document record and purge document artifacts as needed.

Activation behavior:

- User activation toggles `is_active`.
- Document activation restores a deleted or inactive document state according to the existing document lifecycle fields.
- Roles, permissions, and workspaces do not get an activation action unless a future schema explicitly adds such state.

## Frontend Architecture

Add or refactor admin UI around these shared components:

- `AdminLayout`: left menu tree plus right page content.
- `AdminMenuTree`: route-aware tree for documents, users, roles, permissions, and workspaces.
- `AdminDataTable`: reusable table with backend sorting, pagination, loading, empty, forbidden, and error states.
- `AdminPagination`: page navigation and page-size controls.
- `AdminEntityModal`: card-style modal for view, create, edit, delete, activate, and restore actions.
- `AdminRelationshipTree`: frontend-derived tree multi-select for role, permission, and workspace assignments.

Lists must show brief information only. Full detail belongs in the view modal.

## Frontend Page Behavior

Every resource page should provide:

- A paged and sortable list.
- A create button.
- Row actions: view, edit, delete.
- User and document rows additionally show activate or restore actions when applicable.
- Card-style modals for all actions.

User list summary fields:

- Email.
- Display name.
- Active status.
- Role count.
- Workspace count.
- Updated time.

Role list summary fields:

- Name.
- Description summary.
- Permission count.
- Updated time.

Permission list summary fields:

- Name.
- Description summary.
- Updated time.

Workspace list summary fields:

- Slug.
- Name.
- Default flag.
- Updated time.

Document list summary fields:

- Title or document ID.
- Status.
- Owner.
- Workspace.
- Updated time.

## Modal Behavior

View user modal:

- Show all basic user fields.
- Show assigned roles.
- Show effective permissions derived from roles.
- Show assigned workspaces.

Edit user modal:

- Edit display name, password, and active status.
- Edit assigned roles with the role tree selector.
- Edit assigned workspaces with the workspace tree selector.
- Do not edit direct permissions.

Create user modal:

- Create basic user fields.
- Assign roles and workspaces at creation time.

View role modal:

- Show all basic role fields.
- Show assigned permissions.

Edit and create role modal:

- Edit role name and description.
- Edit permissions with the permission tree selector.

Permission modals:

- Manage only permission name and description.

Workspace modals:

- Manage only workspace slug, name, and default flag.

Delete modals:

- Require explicit confirmation.
- Explain which related assignments will be cleaned.
- Do not use `window.confirm`; use the shared card-style modal.

## Frontend-Derived Tree Rules

Permission tree:

- Split permission names by `.`.
- Example: `document.view` renders as `document > view`.
- Leaf selection submits the original permission name.

Workspace tree:

- Prefer splitting workspace slug by `/`.
- If no slash exists, render the workspace as a direct child of the root.
- Leaf selection submits the workspace slug expected by the backend.

Role tree:

- Render roles under a root `Roles` node.
- Roles can remain flat unless a naming convention later makes grouping useful.
- Leaf selection submits role names expected by the backend.

## Implementation Sequence

Task 1: Backend pagination models and helpers.

- Add paged response schemas in `backend/app/schemas/admin.py`.
- Add validated pagination and sorting helpers in `backend/app/services/admin.py` or a narrowly scoped admin helper.
- Add tests for valid pagination, invalid sort fields, and sort direction.
- Commit after tests pass.

Task 2: Backend admin list endpoints.

- Update admin list endpoints in `backend/app/api/v1/admin.py`.
- Return paged payloads for users, roles, permissions, workspaces, documents, and ingestion jobs.
- Preserve detail, create, update, and delete endpoint behavior unless required by this plan.
- Update backend tests.
- Commit after tests pass.

Task 3: Backend user effective permissions and activation/restore behavior.

- Extend user detail data to include effective permissions derived through assigned roles.
- Add or confirm user activation endpoint behavior.
- Add document restore or activation behavior only inside admin document lifecycle code.
- Update backend tests for derived user permissions and activation behavior.
- Commit after tests pass.

Task 4: Frontend admin API client and types.

- Update `frontend/types/admin.ts` for paged responses and user effective permissions.
- Update `frontend/lib/admin.ts` list functions to accept pagination and sorting params.
- Keep admin API changes scoped to admin helpers.
- Run frontend type checks.
- Commit after checks pass.

Task 5: Shared admin layout and menu tree.

- Add route-based admin layout and menu tree.
- Add pages for `/admin/documents`, `/admin/users`, `/admin/roles`, `/admin/permissions`, and `/admin/workspaces`.
- Ensure `/admin` redirects or defaults to documents.
- Do not alter unrelated site navigation unless required for the admin entry.
- Run frontend checks.
- Commit after checks pass.

Task 6: Shared data table and pagination UI.

- Build reusable admin table and pagination components.
- Apply them first to one lower-risk resource, preferably permissions.
- Verify backend sorting and paging requests are sent correctly.
- Commit after checks pass.

Task 7: Resource pages.

- Apply the shared table pattern to users, roles, workspaces, documents, and ingestion jobs where used.
- Ensure each list shows summary fields only.
- Commit after checks pass.

Task 8: Shared modal and CRUD actions.

- Replace inline forms and `window.confirm` with shared card-style modals.
- Implement create, view, edit, delete, and activation/restore actions per resource.
- Commit after checks pass.

Task 9: Relationship tree selectors.

- Implement role, permission, and workspace derived trees.
- Use role and workspace trees in user create/edit.
- Use permission tree in role create/edit.
- Commit after checks pass.

Task 10: End-to-end verification and cleanup.

- Run backend tests focused on admin and RBAC.
- Run frontend lint/type/build checks available in the repo.
- Manually verify route navigation, table sorting, pagination, modals, relationship selection, and delete cleanup.
- Commit final cleanup only if there are task-scoped changes.

## Testing Requirements

Backend tests should cover:

- Pagination metadata and returned item counts.
- Sorting for each resource's primary fields.
- Rejection of invalid `sort_by`.
- User effective permissions derived from role assignments.
- Hard delete cleanup for user, role, permission, and workspace relationships.
- User activation and document restore behavior.

Frontend checks should cover what the repo supports:

- TypeScript type checks.
- Linting if configured.
- Build if feasible.
- Component-level or integration tests if an existing test setup is present.

Manual UI verification should cover:

- Menu tree route switching.
- Active menu highlighting.
- Each resource list loading paged data.
- Sort toggling from table headers.
- Page and page-size changes.
- View, create, edit, delete, and activate/restore modals.
- User detail showing roles, effective permissions, and workspaces.
- Role detail showing permissions.

## Migration Notes

No migration is needed for `user_permissions`, because that table must not be added.

A migration may be needed only if document activation/restore requires a new persisted status field. Prefer reusing existing document lifecycle fields such as `status` and `is_deleted` before adding schema.

If backend response shapes change from arrays to paged payloads, update only admin frontend callers. Do not change unrelated API clients.

## Commit Discipline for Future Codex Runs

Before each task:

- Check `git status --short`.
- Identify unrelated user changes and do not revert them.

During each task:

- Edit only files needed for the current task.
- Keep changes within the admin management scope.

After each task:

- Run the relevant tests or checks.
- Stage only files changed for that task.
- Create a git commit before starting the next task.

Suggested commit message pattern:

- `feat(admin): add paged admin list helpers`
- `feat(admin): add route-based admin layout`
- `feat(admin): add relationship tree selectors`
- `test(admin): cover admin pagination and cleanup`
