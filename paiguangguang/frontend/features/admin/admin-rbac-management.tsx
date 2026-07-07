"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { ApiError } from "@/lib/api";
import {
  clearAdminEntityDetailCache,
  clearAdminEntityListCache,
  activateAdminUser,
  createAdminPermission,
  createAdminRole,
  createAdminUser,
  createAdminWorkspace,
  deleteAdminPermission,
  deleteAdminRole,
  deleteAdminWorkspace,
  deleteAdminUser,
  getAdminPermission,
  getAdminRole,
  getAdminUser,
  getAdminWorkspace,
  listAdminPermissions,
  listAdminRoles,
  listAdminUsers,
  listAdminWorkspaces,
  updateAdminPermission,
  updateAdminRole,
  updateAdminUser,
  updateAdminWorkspace,
} from "@/lib/admin";
import { AdminDataTable, type AdminDataTableColumn } from "@/features/admin/admin-data-table";
import { AdminEntityModal } from "@/features/admin/admin-entity-modal";
import { AdminPagination } from "@/features/admin/admin-pagination";
import { AdminRelationshipTree } from "@/features/admin/admin-relationship-tree";
import type {
  AdminPermissionData,
  AdminRoleData,
  AdminUserData,
  AdminWorkspaceData,
} from "@/types/admin";

type LoadState = "loading" | "ready" | "empty" | "forbidden" | "error";

function formatDateTime(value: string | null) {
  if (!value) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatError(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback;
}

function SectionFrame({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Admin</p>
          <h3 className="mt-2 text-2xl font-semibold text-ink">{title}</h3>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-ink/70">{description}</p>
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function InlineField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "email" | "password";
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-semibold text-ink">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
      />
    </label>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-semibold text-ink">{label}</span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        rows={4}
        className="w-full border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
      />
    </label>
  );
}

function CheckboxField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-3 text-sm font-semibold text-ink">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}

function StateBadge({ value }: { value: string }) {
  return <span className="border border-ink/15 bg-paper px-2.5 py-1 text-xs font-semibold text-ink">{value}</span>;
}

function RedisActionButton({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/30 hover:bg-paper disabled:cursor-not-allowed disabled:opacity-60"
      title={label}
      aria-label={label}
    >
      Redis
    </button>
  );
}

function ResourceListButton({
  active,
  title,
  subtitle,
  badge,
  onClick,
}: {
  active: boolean;
  title: string;
  subtitle: string;
  badge: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "block w-full border p-4 text-left transition",
        active ? "border-tide/45 bg-tide/6 shadow-sm" : "border-ink/10 bg-white/65 hover:border-tide/25 hover:bg-white",
      ].join(" ")}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 className="text-base font-semibold text-ink">{title}</h4>
          <p className="mt-1 text-xs font-medium uppercase tracking-wide text-clay">{subtitle}</p>
        </div>
        <StateBadge value={badge} />
      </div>
    </button>
  );
}

export function UserManager() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [users, setUsers] = useState<AdminUserData[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<AdminUserData | null>(null);
  const [modal, setModal] = useState<"view" | "create" | "edit" | "delete" | "activate" | null>(null);
  const [actionState, setActionState] = useState<"create" | "update" | "delete" | "activate" | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [sortBy, setSortBy] = useState("email");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [total, setTotal] = useState(0);
  const [roleOptions, setRoleOptions] = useState<AdminRoleData[]>([]);
  const [workspaceOptions, setWorkspaceOptions] = useState<AdminWorkspaceData[]>([]);
  const [createForm, setCreateForm] = useState({
    email: "",
    displayName: "",
    password: "",
    isActive: true,
    roles: [] as string[],
    workspaceSlugs: [] as string[],
  });
  const [editForm, setEditForm] = useState({
    displayName: "",
    password: "",
    isActive: true,
    roles: [] as string[],
    workspaceSlugs: [] as string[],
  });

  async function loadUsers(preferredId?: string | null) {
    setState("loading");
    setError(null);
    try {
      const nextUsers = await listAdminUsers({
        page,
        pageSize,
        sortBy,
        sortOrder,
      });
      setUsers(nextUsers);
      setTotal(nextUsers.total);
      setPage(nextUsers.page);
      setPageSize(nextUsers.page_size);
      const fallbackId =
        preferredId && nextUsers.some((user) => user.id === preferredId) ? preferredId : nextUsers[0]?.id ?? null;
      setSelectedUserId(fallbackId);
      setState(nextUsers.length === 0 ? "empty" : "ready");
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to load users."));
      setState(caughtError instanceof ApiError && caughtError.status === 403 ? "forbidden" : "error");
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function loadOptions() {
      try {
        const [nextRoles, nextWorkspaces] = await Promise.all([
          listAdminRoles({ page: 1, pageSize: 100, sortBy: "name", sortOrder: "asc" }),
          listAdminWorkspaces({ page: 1, pageSize: 100, sortBy: "slug", sortOrder: "asc" }),
        ]);
        if (cancelled) {
          return;
        }
        setRoleOptions(nextRoles);
        setWorkspaceOptions(nextWorkspaces);
      } catch {
        if (!cancelled) {
          setRoleOptions([]);
          setWorkspaceOptions([]);
        }
      }
    }

    void loadOptions();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    void loadUsers();
  }, [page, pageSize, sortBy, sortOrder]);

  function mapWorkspaceIdsToSlugs(workspaceIds: string[]) {
    const lookup = new Map(workspaceOptions.map((workspace) => [workspace.id, workspace.slug]));
    return workspaceIds.map((workspaceId) => lookup.get(workspaceId) ?? workspaceId);
  }

  useEffect(() => {
    if (!selectedUserId) {
      setSelectedUser(null);
      return;
    }
    const currentUserId = selectedUserId;
    let cancelled = false;

    async function loadUser() {
      try {
        const user = await getAdminUser(currentUserId);
        if (cancelled) {
          return;
        }
        setSelectedUser(user);
        setEditForm({
          displayName: user.display_name,
          password: "",
          isActive: user.is_active,
          roles: user.roles,
          workspaceSlugs: mapWorkspaceIdsToSlugs(user.workspace_ids),
        });
      } catch (caughtError) {
        if (!cancelled) {
          setError(formatError(caughtError, "Unable to load user details."));
        }
      }
    }

    void loadUser();
    return () => {
      cancelled = true;
    };
  }, [selectedUserId, workspaceOptions]);

  const selectedUserSummary = selectedUser ?? users.find((user) => user.id === selectedUserId) ?? null;
  const selectedUserWorkspaceSlugs = selectedUserSummary ? mapWorkspaceIdsToSlugs(selectedUserSummary.workspace_ids) : [];
  const roleNames = roleOptions.map((role) => role.name);
  const workspaceSlugs = workspaceOptions.map((workspace) => workspace.slug);

  const userColumns: AdminDataTableColumn<AdminUserData>[] = [
    {
      key: "email",
      header: "Email",
      sortable: true,
      sortKey: "email",
      render: (user) => <span className="font-semibold text-ink">{user.email}</span>,
    },
    {
      key: "display_name",
      header: "Display name",
      sortable: true,
      sortKey: "display_name",
      render: (user) => <span className="text-sm text-ink/70">{user.display_name}</span>,
    },
    {
      key: "is_active",
      header: "Status",
      sortable: true,
      sortKey: "is_active",
      render: (user) => (
        <span className={user.is_active ? "font-semibold text-emerald-700" : "font-semibold text-clay"}>
          {user.is_active ? "Active" : "Inactive"}
        </span>
      ),
    },
    {
      key: "roles",
      header: "Roles",
      render: (user) => <span className="text-sm text-ink/70">{user.roles.length}</span>,
    },
    {
      key: "workspaces",
      header: "Workspaces",
      render: (user) => <span className="text-sm text-ink/70">{user.workspace_ids.length}</span>,
    },
    {
      key: "updated_at",
      header: "Updated",
      sortable: true,
      sortKey: "updated_at",
      render: (user) => <span className="text-sm text-ink/70">{formatDateTime(user.updated_at)}</span>,
    },
  ];

  function handleUserSort(nextSortBy: string) {
    setPage(1);
    if (sortBy === nextSortBy) {
      setSortOrder((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortBy(nextSortBy);
    setSortOrder(nextSortBy === "is_active" ? "desc" : "asc");
  }

  function handleUserPageChange(nextPage: number) {
    setPage(nextPage);
  }

  function handleUserPageSizeChange(nextPageSize: number) {
    setPage(1);
    setPageSize(nextPageSize);
  }

  async function handleClearUserListCache() {
    await clearAdminEntityListCache({
      entity: "users",
      page,
      pageSize,
      sortBy,
      sortOrder,
    });
    await loadUsers(selectedUserId);
  }

  function openCreateModal() {
    setModal("create");
  }

  function openViewModal(userId?: string) {
    if (userId) {
      setSelectedUserId(userId);
    }
    setModal("view");
  }

  function openEditModal(userId?: string) {
    if (userId) {
      setSelectedUserId(userId);
    }
    if (selectedUserSummary) {
      setEditForm({
        displayName: selectedUserSummary.display_name,
        password: "",
        isActive: selectedUserSummary.is_active,
        roles: selectedUserSummary.roles,
        workspaceSlugs: mapWorkspaceIdsToSlugs(selectedUserSummary.workspace_ids),
      });
    }
    setModal("edit");
  }

  function openDeleteModal(userId?: string) {
    if (userId) {
      setSelectedUserId(userId);
    }
    setModal("delete");
  }

  function openActivateModal(userId?: string) {
    if (userId) {
      setSelectedUserId(userId);
    }
    setModal("activate");
  }

  function closeModal() {
    setModal(null);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionState("create");
    setError(null);
    try {
      await createAdminUser({
        email: createForm.email,
        display_name: createForm.displayName,
        password: createForm.password,
        is_active: createForm.isActive,
        roles: createForm.roles,
        workspace_slugs: createForm.workspaceSlugs,
      });
      setCreateForm({ email: "", displayName: "", password: "", isActive: true, roles: [], workspaceSlugs: [] });
      closeModal();
      await loadUsers();
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to create user."));
    } finally {
      setActionState(null);
    }
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedUserSummary) {
      return;
    }
    setActionState("update");
    setError(null);
    try {
      await updateAdminUser(selectedUserSummary.id, {
        display_name: editForm.displayName,
        password: editForm.password || null,
        is_active: editForm.isActive,
        roles: editForm.roles,
        workspace_slugs: editForm.workspaceSlugs,
      });
      closeModal();
      await loadUsers(selectedUserSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to update user."));
    } finally {
      setActionState(null);
    }
  }

  async function handleDelete() {
    if (!selectedUserSummary) {
      return;
    }
    setActionState("delete");
    setError(null);
    try {
      await deleteAdminUser(selectedUserSummary.id);
      closeModal();
      await loadUsers(selectedUserSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to delete user."));
    } finally {
      setActionState(null);
    }
  }

  async function handleActivate() {
    if (!selectedUserSummary) {
      return;
    }
    setActionState("activate");
    setError(null);
    try {
      await activateAdminUser(selectedUserSummary.id);
      closeModal();
      await loadUsers(selectedUserSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to activate user."));
    } finally {
      setActionState(null);
    }
  }

  async function handleClearUserDetailCache() {
    if (!selectedUserSummary) {
      return;
    }
    await clearAdminEntityDetailCache({ entity: "users", entityId: selectedUserSummary.id });
    await loadUsers(selectedUserSummary.id);
  }

  return (
    <SectionFrame
      title="Users"
      description="Create users, edit display names and status, and assign roles or default workspace memberships."
      actions={<RedisActionButton label="清理当前用户列表 Redis 缓存" onClick={() => void handleClearUserListCache()} />}
    >
      {error && state === "ready" ? <div className="mb-4 border border-clay/20 bg-clay/10 p-4 text-sm">{error}</div> : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,0.36fr)_minmax(0,0.64fr)]">
        <div className="space-y-3">
          <AdminDataTable
            columns={userColumns}
            rows={users}
            state={state}
            loadingMessage="Loading users..."
            emptyMessage="No users found."
            forbiddenMessage="You do not have permission to manage users."
            errorMessage={error}
            getRowKey={(user) => user.id}
            activeRowKey={selectedUserId}
            onRowClick={(user) => setSelectedUserId(user.id)}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleUserSort}
          />
          {state === "ready" ? (
            <AdminPagination
              page={page}
              pageSize={pageSize}
              total={total}
              onPageChange={handleUserPageChange}
              onPageSizeChange={handleUserPageSizeChange}
            />
          ) : null}
          <button
            type="button"
            onClick={openCreateModal}
            className="w-full border border-tide/40 bg-tide px-4 py-3 text-sm font-semibold text-paper transition hover:opacity-95"
          >
            Create user
          </button>
        </div>
        <div className="space-y-4">
          {selectedUserSummary ? (
            <section className="border border-ink/10 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h4 className="text-base font-semibold text-ink">Selected user</h4>
                  <p className="mt-1 text-xs uppercase tracking-wide text-clay">{selectedUserSummary.email}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <RedisActionButton label="清理当前用户 Redis 缓存" onClick={() => void handleClearUserDetailCache()} />
                  <button type="button" onClick={() => openViewModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    View
                  </button>
                  <button type="button" onClick={() => openEditModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    Edit
                  </button>
                  <button type="button" onClick={() => openDeleteModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    Delete
                  </button>
                  {!selectedUserSummary.is_active ? (
                    <button type="button" onClick={() => openActivateModal()} className="border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">
                      Activate
                    </button>
                  ) : null}
                </div>
              </div>
              <div className="mt-4 grid gap-3 text-sm text-ink/75 md:grid-cols-2">
                <div>
                  <span className="font-semibold text-ink">Display name:</span> {selectedUserSummary.display_name}
                </div>
                <div>
                  <span className="font-semibold text-ink">Status:</span> {selectedUserSummary.is_active ? "Active" : "Inactive"}
                </div>
                <div>
                  <span className="font-semibold text-ink">Roles:</span> {selectedUserSummary.roles.join(", ") || "None"}
                </div>
                <div>
                  <span className="font-semibold text-ink">Workspaces:</span> {selectedUserWorkspaceSlugs.join(", ") || "None"}
                </div>
              </div>
              <div className="mt-4 text-xs leading-6 text-ink/55">
                Created {formatDateTime(selectedUserSummary.created_at)}. Updated {formatDateTime(selectedUserSummary.updated_at)}.
              </div>
            </section>
          ) : null}
        </div>
      </div>

      <AdminEntityModal
        open={modal === "create"}
        title="Create user"
        description="Create a new user, assign roles, and attach workspace memberships."
        onClose={closeModal}
        footer={null}
      >
        <form onSubmit={(event) => void handleCreate(event)} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <InlineField label="Email" value={createForm.email} onChange={(email) => setCreateForm((prev) => ({ ...prev, email }))} type="email" />
            <InlineField label="Display name" value={createForm.displayName} onChange={(displayName) => setCreateForm((prev) => ({ ...prev, displayName }))} />
            <InlineField label="Password" value={createForm.password} onChange={(password) => setCreateForm((prev) => ({ ...prev, password }))} type="password" />
            <CheckboxField label="Active" checked={createForm.isActive} onChange={(isActive) => setCreateForm((prev) => ({ ...prev, isActive }))} />
          </div>
          <AdminRelationshipTree
            title="Roles"
            description="Select the role bundles assigned to this user."
            values={roleNames}
            selectedValues={createForm.roles}
            onChange={(roles) => setCreateForm((prev) => ({ ...prev, roles }))}
            delimiter={null}
            emptyMessage="No roles available."
          />
          <AdminRelationshipTree
            title="Workspaces"
            description="Select the workspaces this user can access."
            values={workspaceSlugs}
            selectedValues={createForm.workspaceSlugs}
            onChange={(workspaceSlugs) => setCreateForm((prev) => ({ ...prev, workspaceSlugs }))}
            delimiter="/"
            emptyMessage="No workspaces available."
          />
          <div className="flex flex-wrap gap-3">
            <button type="submit" disabled={actionState === "create"} className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60">
              {actionState === "create" ? "Creating..." : "Create user"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </form>
      </AdminEntityModal>

      <AdminEntityModal
        open={modal === "view"}
        title="View user"
        description="Read-only details for the selected user."
        onClose={closeModal}
      >
        {selectedUserSummary ? (
          <div className="space-y-4 text-sm text-ink/75">
            <div className="grid gap-3 md:grid-cols-2">
              <div><span className="font-semibold text-ink">Email:</span> {selectedUserSummary.email}</div>
              <div><span className="font-semibold text-ink">Display name:</span> {selectedUserSummary.display_name}</div>
              <div><span className="font-semibold text-ink">Status:</span> {selectedUserSummary.is_active ? "Active" : "Inactive"}</div>
              <div><span className="font-semibold text-ink">User ID:</span> {selectedUserSummary.id}</div>
            </div>
            <div>
              <div className="font-semibold text-ink">Roles</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {selectedUserSummary.roles.length > 0 ? selectedUserSummary.roles.map((role) => (
                  <span key={role} className="border border-ink/15 bg-paper px-2.5 py-1 text-xs font-semibold text-ink">{role}</span>
                )) : <span className="text-ink/55">None</span>}
              </div>
            </div>
            <div>
              <div className="font-semibold text-ink">Effective permissions</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {selectedUserSummary.effective_permissions.length > 0 ? selectedUserSummary.effective_permissions.map((permission) => (
                  <span key={permission} className="border border-ink/15 bg-paper px-2.5 py-1 text-xs font-semibold text-ink">{permission}</span>
                )) : <span className="text-ink/55">None</span>}
              </div>
            </div>
            <div>
              <div className="font-semibold text-ink">Workspaces</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {selectedUserWorkspaceSlugs.length > 0 ? selectedUserWorkspaceSlugs.map((workspaceSlug) => (
                  <span key={workspaceSlug} className="border border-ink/15 bg-paper px-2.5 py-1 text-xs font-semibold text-ink">{workspaceSlug}</span>
                )) : <span className="text-ink/55">None</span>}
              </div>
            </div>
          </div>
        ) : null}
      </AdminEntityModal>

      <AdminEntityModal
        open={modal === "edit"}
        title="Edit user"
        description="Update the user's profile, active state, roles, and workspace memberships."
        onClose={closeModal}
      >
        <form onSubmit={(event) => void handleUpdate(event)} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <InlineField label="Display name" value={editForm.displayName} onChange={(displayName) => setEditForm((prev) => ({ ...prev, displayName }))} />
            <InlineField label="Password" value={editForm.password} onChange={(password) => setEditForm((prev) => ({ ...prev, password }))} type="password" placeholder="Leave blank to keep current password" />
            <CheckboxField label="Active" checked={editForm.isActive} onChange={(isActive) => setEditForm((prev) => ({ ...prev, isActive }))} />
          </div>
          <AdminRelationshipTree
            title="Roles"
            description="Adjust the role bundles assigned to this user."
            values={roleNames}
            selectedValues={editForm.roles}
            onChange={(roles) => setEditForm((prev) => ({ ...prev, roles }))}
            delimiter={null}
            emptyMessage="No roles available."
          />
          <AdminRelationshipTree
            title="Workspaces"
            description="Adjust the workspace memberships assigned to this user."
            values={workspaceSlugs}
            selectedValues={editForm.workspaceSlugs}
            onChange={(workspaceSlugs) => setEditForm((prev) => ({ ...prev, workspaceSlugs }))}
            delimiter="/"
            emptyMessage="No workspaces available."
          />
          <div className="flex flex-wrap gap-3">
            <button type="submit" disabled={actionState === "update"} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink disabled:opacity-60">
              {actionState === "update" ? "Saving..." : "Save user"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </form>
      </AdminEntityModal>

      <AdminEntityModal
        open={modal === "delete"}
        title="Delete user"
        description="This will permanently remove the user and clean the user-role and workspace membership records."
        onClose={closeModal}
      >
        <div className="space-y-4 text-sm text-ink/75">
          <p>
            Delete <span className="font-semibold text-ink">{selectedUserSummary?.email}</span> and all related assignments?
          </p>
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => void handleDelete()} disabled={actionState === "delete"} className="border border-clay/30 bg-clay px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60">
              {actionState === "delete" ? "Deleting..." : "Delete user"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </div>
      </AdminEntityModal>

      <AdminEntityModal
        open={modal === "activate"}
        title="Activate user"
        description="Restore the user's active status without changing their assignments."
        onClose={closeModal}
      >
        <div className="space-y-4 text-sm text-ink/75">
          <p>
            Activate <span className="font-semibold text-ink">{selectedUserSummary?.email}</span>?
          </p>
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => void handleActivate()} disabled={actionState === "activate"} className="border border-emerald-200 bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">
              {actionState === "activate" ? "Activating..." : "Activate user"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </div>
      </AdminEntityModal>
    </SectionFrame>
  );
}

export function RoleManager() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [roles, setRoles] = useState<AdminRoleData[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<AdminRoleData | null>(null);
  const [modal, setModal] = useState<"view" | "create" | "edit" | "delete" | null>(null);
  const [actionState, setActionState] = useState<"create" | "update" | "delete" | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [sortBy, setSortBy] = useState("name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [total, setTotal] = useState(0);
  const [permissionOptions, setPermissionOptions] = useState<AdminPermissionData[]>([]);
  const [createForm, setCreateForm] = useState({ name: "", description: "", permissions: [] as string[] });
  const [editForm, setEditForm] = useState({ name: "", description: "", permissions: [] as string[] });

  async function loadRoles(preferredId?: string | null) {
    setState("loading");
    setError(null);
    try {
      const nextRoles = await listAdminRoles({
        page,
        pageSize,
        sortBy,
        sortOrder,
      });
      setRoles(nextRoles);
      setTotal(nextRoles.total);
      setPage(nextRoles.page);
      setPageSize(nextRoles.page_size);
      const fallbackId = preferredId && nextRoles.some((role) => role.id === preferredId) ? preferredId : nextRoles[0]?.id ?? null;
      setSelectedRoleId(fallbackId);
      setState(nextRoles.length === 0 ? "empty" : "ready");
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to load roles."));
      setState(caughtError instanceof ApiError && caughtError.status === 403 ? "forbidden" : "error");
    }
  }

  useEffect(() => {
    void loadRoles();
  }, [page, pageSize, sortBy, sortOrder]);

  useEffect(() => {
    let cancelled = false;

    async function loadOptions() {
      try {
        const nextPermissions = await listAdminPermissions({ page: 1, pageSize: 100, sortBy: "name", sortOrder: "asc" });
        if (!cancelled) {
          setPermissionOptions(nextPermissions);
        }
      } catch {
        if (!cancelled) {
          setPermissionOptions([]);
        }
      }
    }

    void loadOptions();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedRoleId) {
      setSelectedRole(null);
      return;
    }
    const currentRoleId = selectedRoleId;
    let cancelled = false;

    async function loadRole() {
      try {
        const role = await getAdminRole(currentRoleId);
        if (cancelled) {
          return;
        }
        setSelectedRole(role);
        setEditForm({
          name: role.name,
          description: role.description ?? "",
          permissions: role.permissions,
        });
      } catch (caughtError) {
        if (!cancelled) {
          setError(formatError(caughtError, "Unable to load role details."));
        }
      }
    }

    void loadRole();
    return () => {
      cancelled = true;
    };
  }, [selectedRoleId]);

  const selectedRoleSummary = selectedRole ?? roles.find((role) => role.id === selectedRoleId) ?? null;
  const permissionNames = permissionOptions.map((permission) => permission.name);

  const roleColumns: AdminDataTableColumn<AdminRoleData>[] = [
    {
      key: "name",
      header: "Name",
      sortable: true,
      sortKey: "name",
      render: (role) => <span className="font-semibold text-ink">{role.name}</span>,
    },
    {
      key: "description",
      header: "Description",
      render: (role) => <span className="text-sm text-ink/70">{role.description ?? "No description"}</span>,
    },
    {
      key: "permissions",
      header: "Permissions",
      render: (role) => <span className="text-sm text-ink/70">{role.permissions.length}</span>,
    },
    {
      key: "updated_at",
      header: "Updated",
      sortable: true,
      sortKey: "updated_at",
      render: (role) => <span className="text-sm text-ink/70">{formatDateTime(role.updated_at)}</span>,
    },
  ];

  function handleRoleSort(nextSortBy: string) {
    setPage(1);
    if (sortBy === nextSortBy) {
      setSortOrder((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortBy(nextSortBy);
    setSortOrder("asc");
  }

  function handleRolePageChange(nextPage: number) {
    setPage(nextPage);
  }

  function handleRolePageSizeChange(nextPageSize: number) {
    setPage(1);
    setPageSize(nextPageSize);
  }

  async function handleClearRoleListCache() {
    await clearAdminEntityListCache({
      entity: "roles",
      page,
      pageSize,
      sortBy,
      sortOrder,
    });
    await loadRoles(selectedRoleId);
  }

  function openCreateModal() {
    setModal("create");
  }

  function openViewModal(roleId?: string) {
    if (roleId) {
      setSelectedRoleId(roleId);
    }
    setModal("view");
  }

  function openEditModal(roleId?: string) {
    if (roleId) {
      setSelectedRoleId(roleId);
    }
    if (selectedRoleSummary) {
      setEditForm({
        name: selectedRoleSummary.name,
        description: selectedRoleSummary.description ?? "",
        permissions: selectedRoleSummary.permissions,
      });
    }
    setModal("edit");
  }

  function openDeleteModal(roleId?: string) {
    if (roleId) {
      setSelectedRoleId(roleId);
    }
    setModal("delete");
  }

  function closeModal() {
    setModal(null);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionState("create");
    setError(null);
    try {
      await createAdminRole({
        name: createForm.name,
        description: createForm.description || null,
        permissions: createForm.permissions,
      });
      setCreateForm({ name: "", description: "", permissions: [] });
      closeModal();
      await loadRoles();
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to create role."));
    } finally {
      setActionState(null);
    }
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedRoleSummary) {
      return;
    }
    setActionState("update");
    setError(null);
    try {
      await updateAdminRole(selectedRoleSummary.id, {
        name: editForm.name,
        description: editForm.description || null,
        permissions: editForm.permissions,
      });
      closeModal();
      await loadRoles(selectedRoleSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to update role."));
    } finally {
      setActionState(null);
    }
  }

  async function handleDelete() {
    if (!selectedRoleSummary) {
      return;
    }
    setActionState("delete");
    setError(null);
    try {
      await deleteAdminRole(selectedRoleSummary.id);
      closeModal();
      await loadRoles(selectedRoleSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to delete role."));
    } finally {
      setActionState(null);
    }
  }

  async function handleClearRoleDetailCache() {
    if (!selectedRoleSummary) {
      return;
    }
    await clearAdminEntityDetailCache({ entity: "roles", entityId: selectedRoleSummary.id });
    await loadRoles(selectedRoleSummary.id);
  }

  return (
    <SectionFrame
      title="Roles"
      description="Create roles, edit their permissions, and inspect the permission bundles assigned to staff accounts."
      actions={<RedisActionButton label="清理当前角色列表 Redis 缓存" onClick={() => void handleClearRoleListCache()} />}
    >
      {error && state === "ready" ? <div className="mb-4 border border-clay/20 bg-clay/10 p-4 text-sm">{error}</div> : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,0.36fr)_minmax(0,0.64fr)]">
        <div className="space-y-3">
          <AdminDataTable
            columns={roleColumns}
            rows={roles}
            state={state}
            loadingMessage="Loading roles..."
            emptyMessage="No roles found."
            forbiddenMessage="You do not have permission to manage roles."
            errorMessage={error}
            getRowKey={(role) => role.id}
            activeRowKey={selectedRoleId}
            onRowClick={(role) => setSelectedRoleId(role.id)}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleRoleSort}
          />
          {state === "ready" ? (
            <AdminPagination
              page={page}
              pageSize={pageSize}
              total={total}
              onPageChange={handleRolePageChange}
              onPageSizeChange={handleRolePageSizeChange}
            />
          ) : null}
          <button
            type="button"
            onClick={openCreateModal}
            className="w-full border border-tide/40 bg-tide px-4 py-3 text-sm font-semibold text-paper transition hover:opacity-95"
          >
            Create role
          </button>
        </div>
        <div className="space-y-4">
          {selectedRoleSummary ? (
            <section className="border border-ink/10 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h4 className="text-base font-semibold text-ink">Selected role</h4>
                  <p className="mt-1 text-xs uppercase tracking-wide text-clay">{selectedRoleSummary.name}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <RedisActionButton label="清理当前角色 Redis 缓存" onClick={() => void handleClearRoleDetailCache()} />
                  <button type="button" onClick={() => openViewModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    View
                  </button>
                  <button type="button" onClick={() => openEditModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    Edit
                  </button>
                  <button type="button" onClick={() => openDeleteModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    Delete
                  </button>
                </div>
              </div>
              <div className="mt-4 grid gap-3 text-sm text-ink/75 md:grid-cols-2">
                <div><span className="font-semibold text-ink">Name:</span> {selectedRoleSummary.name}</div>
                <div><span className="font-semibold text-ink">Permissions:</span> {selectedRoleSummary.permissions.length}</div>
                <div className="md:col-span-2"><span className="font-semibold text-ink">Description:</span> {selectedRoleSummary.description ?? "No description"}</div>
              </div>
              <div className="mt-4 text-xs leading-6 text-ink/55">
                Created {formatDateTime(selectedRoleSummary.created_at)}. Updated {formatDateTime(selectedRoleSummary.updated_at)}.
              </div>
            </section>
          ) : null}
        </div>
      </div>

      <AdminEntityModal
        open={modal === "create"}
        title="Create role"
        description="Create a role and assign permissions from the relationship tree."
        onClose={closeModal}
      >
        <form onSubmit={(event) => void handleCreate(event)} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <InlineField label="Name" value={createForm.name} onChange={(name) => setCreateForm((prev) => ({ ...prev, name }))} />
            <TextAreaField label="Description" value={createForm.description} onChange={(description) => setCreateForm((prev) => ({ ...prev, description }))} />
          </div>
          <AdminRelationshipTree
            title="Permissions"
            description="Select the permissions bundled into this role."
            values={permissionNames}
            selectedValues={createForm.permissions}
            onChange={(permissions) => setCreateForm((prev) => ({ ...prev, permissions }))}
            delimiter="."
            emptyMessage="No permissions available."
          />
          <div className="flex flex-wrap gap-3">
            <button type="submit" disabled={actionState === "create"} className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60">
              {actionState === "create" ? "Creating..." : "Create role"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </form>
      </AdminEntityModal>

      <AdminEntityModal
        open={modal === "view"}
        title="View role"
        description="Read-only details for the selected role."
        onClose={closeModal}
      >
        {selectedRoleSummary ? (
          <div className="space-y-4 text-sm text-ink/75">
            <div className="grid gap-3 md:grid-cols-2">
              <div><span className="font-semibold text-ink">Name:</span> {selectedRoleSummary.name}</div>
              <div><span className="font-semibold text-ink">Role ID:</span> {selectedRoleSummary.id}</div>
              <div className="md:col-span-2"><span className="font-semibold text-ink">Description:</span> {selectedRoleSummary.description ?? "No description"}</div>
            </div>
            <div>
              <div className="font-semibold text-ink">Permissions</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {selectedRoleSummary.permissions.length > 0 ? selectedRoleSummary.permissions.map((permission) => (
                  <span key={permission} className="border border-ink/15 bg-paper px-2.5 py-1 text-xs font-semibold text-ink">{permission}</span>
                )) : <span className="text-ink/55">None</span>}
              </div>
            </div>
          </div>
        ) : null}
      </AdminEntityModal>

      <AdminEntityModal
        open={modal === "edit"}
        title="Edit role"
        description="Update the role metadata and its permission bundle."
        onClose={closeModal}
      >
        <form onSubmit={(event) => void handleUpdate(event)} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <InlineField label="Name" value={editForm.name} onChange={(name) => setEditForm((prev) => ({ ...prev, name }))} />
            <TextAreaField label="Description" value={editForm.description} onChange={(description) => setEditForm((prev) => ({ ...prev, description }))} />
          </div>
          <AdminRelationshipTree
            title="Permissions"
            description="Adjust the permissions bundled into this role."
            values={permissionNames}
            selectedValues={editForm.permissions}
            onChange={(permissions) => setEditForm((prev) => ({ ...prev, permissions }))}
            delimiter="."
            emptyMessage="No permissions available."
          />
          <div className="flex flex-wrap gap-3">
            <button type="submit" disabled={actionState === "update"} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink disabled:opacity-60">
              {actionState === "update" ? "Saving..." : "Save role"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </form>
      </AdminEntityModal>

      <AdminEntityModal
        open={modal === "delete"}
        title="Delete role"
        description="This will remove the role and clean its user-role and role-permission assignments."
        onClose={closeModal}
      >
        <div className="space-y-4 text-sm text-ink/75">
          <p>
            Delete <span className="font-semibold text-ink">{selectedRoleSummary?.name}</span>?
          </p>
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => void handleDelete()} disabled={actionState === "delete"} className="border border-clay/30 bg-clay px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60">
              {actionState === "delete" ? "Deleting..." : "Delete role"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </div>
      </AdminEntityModal>
    </SectionFrame>
  );
}

export function PermissionManager() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<AdminPermissionData[]>([]);
  const [selectedPermissionId, setSelectedPermissionId] = useState<string | null>(null);
  const [selectedPermission, setSelectedPermission] = useState<AdminPermissionData | null>(null);
  const [modal, setModal] = useState<"view" | "create" | "edit" | "delete" | null>(null);
  const [actionState, setActionState] = useState<"create" | "update" | "delete" | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [sortBy, setSortBy] = useState("name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [total, setTotal] = useState(0);
  const [createForm, setCreateForm] = useState({ name: "", description: "" });
  const [editForm, setEditForm] = useState({ name: "", description: "" });

  async function loadPermissions(preferredId?: string | null) {
    setState("loading");
    setError(null);
    try {
      const nextPermissions = await listAdminPermissions({
        page,
        pageSize,
        sortBy,
        sortOrder,
      });
      setPermissions(nextPermissions);
      setTotal(nextPermissions.total);
      setPage(nextPermissions.page);
      setPageSize(nextPermissions.page_size);
      const fallbackId =
        preferredId && nextPermissions.some((permission) => permission.id === preferredId)
          ? preferredId
          : nextPermissions[0]?.id ?? null;
      setSelectedPermissionId(fallbackId);
      setState(nextPermissions.length === 0 ? "empty" : "ready");
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to load permissions."));
      setState(caughtError instanceof ApiError && caughtError.status === 403 ? "forbidden" : "error");
    }
  }

  useEffect(() => {
    void loadPermissions();
  }, [page, pageSize, sortBy, sortOrder]);

  useEffect(() => {
    if (!selectedPermissionId) {
      setSelectedPermission(null);
      return;
    }
    const currentPermissionId = selectedPermissionId;
    let cancelled = false;

    async function loadPermission() {
      try {
        const permission = await getAdminPermission(currentPermissionId);
        if (cancelled) {
          return;
        }
        setSelectedPermission(permission);
        setEditForm({
          name: permission.name,
          description: permission.description ?? "",
        });
      } catch (caughtError) {
        if (!cancelled) {
          setError(formatError(caughtError, "Unable to load permission details."));
        }
      }
    }

    void loadPermission();
    return () => {
      cancelled = true;
    };
  }, [selectedPermissionId]);

  const selectedPermissionSummary = selectedPermission ?? permissions.find((permission) => permission.id === selectedPermissionId) ?? null;

  const permissionColumns: AdminDataTableColumn<AdminPermissionData>[] = [
    {
      key: "name",
      header: "Name",
      sortable: true,
      sortKey: "name",
      render: (permission) => <span className="font-semibold text-ink">{permission.name}</span>,
    },
    {
      key: "description",
      header: "Description",
      render: (permission) => <span className="text-sm text-ink/70">{permission.description ?? "No description"}</span>,
    },
    {
      key: "updated_at",
      header: "Updated",
      sortable: true,
      sortKey: "updated_at",
      render: (permission) => <span className="text-sm text-ink/70">{formatDateTime(permission.updated_at)}</span>,
    },
  ];

  function handleSort(nextSortBy: string) {
    setPage(1);
    if (sortBy === nextSortBy) {
      setSortOrder((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortBy(nextSortBy);
    setSortOrder(nextSortBy === "updated_at" ? "desc" : "asc");
  }

  function handlePageChange(nextPage: number) {
    setPage(nextPage);
  }

  function handlePageSizeChange(nextPageSize: number) {
    setPage(1);
    setPageSize(nextPageSize);
  }

  async function handleClearPermissionListCache() {
    await clearAdminEntityListCache({
      entity: "permissions",
      page,
      pageSize,
      sortBy,
      sortOrder,
    });
    await loadPermissions(selectedPermissionId);
  }

  function openCreateModal() {
    setModal("create");
  }

  function openViewModal(permissionId?: string) {
    if (permissionId) {
      setSelectedPermissionId(permissionId);
    }
    setModal("view");
  }

  function openEditModal(permissionId?: string) {
    if (permissionId) {
      setSelectedPermissionId(permissionId);
    }
    if (selectedPermissionSummary) {
      setEditForm({
        name: selectedPermissionSummary.name,
        description: selectedPermissionSummary.description ?? "",
      });
    }
    setModal("edit");
  }

  function openDeleteModal(permissionId?: string) {
    if (permissionId) {
      setSelectedPermissionId(permissionId);
    }
    setModal("delete");
  }

  function closeModal() {
    setModal(null);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionState("create");
    setError(null);
    try {
      await createAdminPermission({
        name: createForm.name,
        description: createForm.description || null,
      });
      setCreateForm({ name: "", description: "" });
      closeModal();
      await loadPermissions();
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to create permission."));
    } finally {
      setActionState(null);
    }
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPermissionSummary) {
      return;
    }
    setActionState("update");
    setError(null);
    try {
      await updateAdminPermission(selectedPermissionSummary.id, {
        name: editForm.name,
        description: editForm.description || null,
      });
      closeModal();
      await loadPermissions(selectedPermissionSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to update permission."));
    } finally {
      setActionState(null);
    }
  }

  async function handleDelete() {
    if (!selectedPermissionSummary) {
      return;
    }
    setActionState("delete");
    setError(null);
    try {
      await deleteAdminPermission(selectedPermissionSummary.id);
      closeModal();
      await loadPermissions(selectedPermissionSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to delete permission."));
    } finally {
      setActionState(null);
    }
  }

  async function handleClearPermissionDetailCache() {
    if (!selectedPermissionSummary) {
      return;
    }
    await clearAdminEntityDetailCache({ entity: "permissions", entityId: selectedPermissionSummary.id });
    await loadPermissions(selectedPermissionSummary.id);
  }

  return (
    <SectionFrame
      title="Permissions"
      description="Create and edit permission definitions that can be assigned to roles."
      actions={<RedisActionButton label="清理当前权限列表 Redis 缓存" onClick={() => void handleClearPermissionListCache()} />}
    >
      {error && state === "ready" ? <div className="mb-4 border border-clay/20 bg-clay/10 p-4 text-sm">{error}</div> : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,0.36fr)_minmax(0,0.64fr)]">
        <div className="space-y-3">
          <AdminDataTable
            columns={permissionColumns}
            rows={permissions}
            state={state}
            loadingMessage="Loading permissions..."
            emptyMessage="No permissions found."
            forbiddenMessage="You do not have permission to manage permissions."
            errorMessage={error}
            getRowKey={(permission) => permission.id}
            activeRowKey={selectedPermissionId}
            onRowClick={(permission) => setSelectedPermissionId(permission.id)}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleSort}
          />
          {state === "ready" ? (
            <AdminPagination
              page={page}
              pageSize={pageSize}
              total={total}
              onPageChange={handlePageChange}
              onPageSizeChange={handlePageSizeChange}
            />
          ) : null}
          <button
            type="button"
            onClick={openCreateModal}
            className="w-full border border-tide/40 bg-tide px-4 py-3 text-sm font-semibold text-paper transition hover:opacity-95"
          >
            Create permission
          </button>
        </div>
        <div className="space-y-4">
          {selectedPermissionSummary ? (
            <section className="border border-ink/10 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h4 className="text-base font-semibold text-ink">Selected permission</h4>
                  <p className="mt-1 text-xs uppercase tracking-wide text-clay">{selectedPermissionSummary.name}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <RedisActionButton label="清理当前权限 Redis 缓存" onClick={() => void handleClearPermissionDetailCache()} />
                  <button type="button" onClick={() => openViewModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    View
                  </button>
                  <button type="button" onClick={() => openEditModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    Edit
                  </button>
                  <button type="button" onClick={() => openDeleteModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    Delete
                  </button>
                </div>
              </div>
              <div className="mt-4 grid gap-3 text-sm text-ink/75 md:grid-cols-2">
                <div><span className="font-semibold text-ink">Name:</span> {selectedPermissionSummary.name}</div>
                <div><span className="font-semibold text-ink">Permission ID:</span> {selectedPermissionSummary.id}</div>
                <div className="md:col-span-2"><span className="font-semibold text-ink">Description:</span> {selectedPermissionSummary.description ?? "No description"}</div>
              </div>
              <div className="mt-4 text-xs leading-6 text-ink/55">
                Created {formatDateTime(selectedPermissionSummary.created_at)}. Updated {formatDateTime(selectedPermissionSummary.updated_at)}.
              </div>
            </section>
          ) : null}
        </div>
      </div>

      <AdminEntityModal open={modal === "create"} title="Create permission" description="Create a new permission definition." onClose={closeModal}>
        <form onSubmit={(event) => void handleCreate(event)} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <InlineField label="Name" value={createForm.name} onChange={(name) => setCreateForm((prev) => ({ ...prev, name }))} />
            <TextAreaField label="Description" value={createForm.description} onChange={(description) => setCreateForm((prev) => ({ ...prev, description }))} />
          </div>
          <div className="flex flex-wrap gap-3">
            <button type="submit" disabled={actionState === "create"} className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60">
              {actionState === "create" ? "Creating..." : "Create permission"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </form>
      </AdminEntityModal>

      <AdminEntityModal open={modal === "view"} title="View permission" description="Read-only details for the selected permission." onClose={closeModal}>
        {selectedPermissionSummary ? (
          <div className="space-y-4 text-sm text-ink/75">
            <div className="grid gap-3 md:grid-cols-2">
              <div><span className="font-semibold text-ink">Name:</span> {selectedPermissionSummary.name}</div>
              <div><span className="font-semibold text-ink">Permission ID:</span> {selectedPermissionSummary.id}</div>
              <div className="md:col-span-2"><span className="font-semibold text-ink">Description:</span> {selectedPermissionSummary.description ?? "No description"}</div>
            </div>
          </div>
        ) : null}
      </AdminEntityModal>

      <AdminEntityModal open={modal === "edit"} title="Edit permission" description="Update the permission name and description." onClose={closeModal}>
        <form onSubmit={(event) => void handleUpdate(event)} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <InlineField label="Name" value={editForm.name} onChange={(name) => setEditForm((prev) => ({ ...prev, name }))} />
            <TextAreaField label="Description" value={editForm.description} onChange={(description) => setEditForm((prev) => ({ ...prev, description }))} />
          </div>
          <div className="flex flex-wrap gap-3">
            <button type="submit" disabled={actionState === "update"} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink disabled:opacity-60">
              {actionState === "update" ? "Saving..." : "Save permission"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </form>
      </AdminEntityModal>

      <AdminEntityModal open={modal === "delete"} title="Delete permission" description="This will remove the permission and clean its role-permission assignments." onClose={closeModal}>
        <div className="space-y-4 text-sm text-ink/75">
          <p>
            Delete <span className="font-semibold text-ink">{selectedPermissionSummary?.name}</span>?
          </p>
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => void handleDelete()} disabled={actionState === "delete"} className="border border-clay/30 bg-clay px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60">
              {actionState === "delete" ? "Deleting..." : "Delete permission"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </div>
      </AdminEntityModal>
    </SectionFrame>
  );
}

export function WorkspaceManager() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<AdminWorkspaceData[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [selectedWorkspace, setSelectedWorkspace] = useState<AdminWorkspaceData | null>(null);
  const [modal, setModal] = useState<"view" | "create" | "edit" | "delete" | null>(null);
  const [actionState, setActionState] = useState<"create" | "update" | "delete" | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [sortBy, setSortBy] = useState("slug");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [total, setTotal] = useState(0);
  const [createForm, setCreateForm] = useState({ slug: "", name: "", isDefault: false });
  const [editForm, setEditForm] = useState({ slug: "", name: "", isDefault: false });

  async function loadWorkspaces(preferredId?: string | null) {
    setState("loading");
    setError(null);
    try {
      const nextWorkspaces = await listAdminWorkspaces({
        page,
        pageSize,
        sortBy,
        sortOrder,
      });
      setWorkspaces(nextWorkspaces);
      setTotal(nextWorkspaces.total);
      setPage(nextWorkspaces.page);
      setPageSize(nextWorkspaces.page_size);
      const fallbackId =
        preferredId && nextWorkspaces.some((workspace) => workspace.id === preferredId)
          ? preferredId
          : nextWorkspaces[0]?.id ?? null;
      setSelectedWorkspaceId(fallbackId);
      setState(nextWorkspaces.length === 0 ? "empty" : "ready");
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to load workspaces."));
      setState(caughtError instanceof ApiError && caughtError.status === 403 ? "forbidden" : "error");
    }
  }

  useEffect(() => {
    void loadWorkspaces();
  }, [page, pageSize, sortBy, sortOrder]);

  useEffect(() => {
    if (!selectedWorkspaceId) {
      setSelectedWorkspace(null);
      return;
    }
    const currentWorkspaceId = selectedWorkspaceId;
    let cancelled = false;

    async function loadWorkspace() {
      try {
        const workspace = await getAdminWorkspace(currentWorkspaceId);
        if (cancelled) {
          return;
        }
        setSelectedWorkspace(workspace);
        setEditForm({
          slug: workspace.slug,
          name: workspace.name,
          isDefault: workspace.is_default,
        });
      } catch (caughtError) {
        if (!cancelled) {
          setError(formatError(caughtError, "Unable to load workspace details."));
        }
      }
    }

    void loadWorkspace();
    return () => {
      cancelled = true;
    };
  }, [selectedWorkspaceId]);

  const selectedWorkspaceSummary =
    selectedWorkspace ?? workspaces.find((workspace) => workspace.id === selectedWorkspaceId) ?? null;

  const workspaceColumns: AdminDataTableColumn<AdminWorkspaceData>[] = [
    {
      key: "slug",
      header: "Slug",
      sortable: true,
      sortKey: "slug",
      render: (workspace) => <span className="font-semibold text-ink">{workspace.slug}</span>,
    },
    {
      key: "name",
      header: "Name",
      sortable: true,
      sortKey: "name",
      render: (workspace) => <span className="text-sm text-ink/70">{workspace.name}</span>,
    },
    {
      key: "is_default",
      header: "Default",
      sortable: true,
      sortKey: "is_default",
      render: (workspace) => (
        <span className={workspace.is_default ? "font-semibold text-emerald-700" : "font-semibold text-clay"}>
          {workspace.is_default ? "Default" : "No"}
        </span>
      ),
    },
    {
      key: "updated_at",
      header: "Updated",
      sortable: true,
      sortKey: "updated_at",
      render: (workspace) => <span className="text-sm text-ink/70">{formatDateTime(workspace.updated_at)}</span>,
    },
  ];

  function handleWorkspaceSort(nextSortBy: string) {
    setPage(1);
    if (sortBy === nextSortBy) {
      setSortOrder((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortBy(nextSortBy);
    setSortOrder(nextSortBy === "is_default" ? "desc" : "asc");
  }

  function handleWorkspacePageChange(nextPage: number) {
    setPage(nextPage);
  }

  function handleWorkspacePageSizeChange(nextPageSize: number) {
    setPage(1);
    setPageSize(nextPageSize);
  }

  async function handleClearWorkspaceListCache() {
    await clearAdminEntityListCache({
      entity: "workspaces",
      page,
      pageSize,
      sortBy,
      sortOrder,
    });
    await loadWorkspaces(selectedWorkspaceId);
  }

  function openCreateModal() {
    setModal("create");
  }

  function openViewModal(workspaceId?: string) {
    if (workspaceId) {
      setSelectedWorkspaceId(workspaceId);
    }
    setModal("view");
  }

  function openEditModal(workspaceId?: string) {
    if (workspaceId) {
      setSelectedWorkspaceId(workspaceId);
    }
    if (selectedWorkspaceSummary) {
      setEditForm({
        slug: selectedWorkspaceSummary.slug,
        name: selectedWorkspaceSummary.name,
        isDefault: selectedWorkspaceSummary.is_default,
      });
    }
    setModal("edit");
  }

  function openDeleteModal(workspaceId?: string) {
    if (workspaceId) {
      setSelectedWorkspaceId(workspaceId);
    }
    setModal("delete");
  }

  function closeModal() {
    setModal(null);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionState("create");
    setError(null);
    try {
      await createAdminWorkspace({
        slug: createForm.slug,
        name: createForm.name,
        is_default: createForm.isDefault,
      });
      setCreateForm({ slug: "", name: "", isDefault: false });
      closeModal();
      await loadWorkspaces();
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to create workspace."));
    } finally {
      setActionState(null);
    }
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedWorkspaceSummary) {
      return;
    }
    setActionState("update");
    setError(null);
    try {
      await updateAdminWorkspace(selectedWorkspaceSummary.id, {
        slug: editForm.slug,
        name: editForm.name,
        is_default: editForm.isDefault,
      });
      closeModal();
      await loadWorkspaces(selectedWorkspaceSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to update workspace."));
    } finally {
      setActionState(null);
    }
  }

  async function handleDelete() {
    if (!selectedWorkspaceSummary) {
      return;
    }
    setActionState("delete");
    setError(null);
    try {
      await deleteAdminWorkspace(selectedWorkspaceSummary.id);
      closeModal();
      await loadWorkspaces(selectedWorkspaceSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to delete workspace."));
    } finally {
      setActionState(null);
    }
  }

  async function handleClearWorkspaceDetailCache() {
    if (!selectedWorkspaceSummary) {
      return;
    }
    await clearAdminEntityDetailCache({ entity: "workspaces", entityId: selectedWorkspaceSummary.id });
    await loadWorkspaces(selectedWorkspaceSummary.id);
  }

  return (
    <SectionFrame
      title="Workspaces"
      description="Maintain workspace records and mark the current default workspace for permission scoping."
      actions={<RedisActionButton label="清理当前工作区列表 Redis 缓存" onClick={() => void handleClearWorkspaceListCache()} />}
    >
      {error && state === "ready" ? <div className="mb-4 border border-clay/20 bg-clay/10 p-4 text-sm">{error}</div> : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,0.36fr)_minmax(0,0.64fr)]">
        <div className="space-y-3">
          <AdminDataTable
            columns={workspaceColumns}
            rows={workspaces}
            state={state}
            loadingMessage="Loading workspaces..."
            emptyMessage="No workspaces found."
            forbiddenMessage="You do not have permission to manage workspaces."
            errorMessage={error}
            getRowKey={(workspace) => workspace.id}
            activeRowKey={selectedWorkspaceId}
            onRowClick={(workspace) => setSelectedWorkspaceId(workspace.id)}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleWorkspaceSort}
          />
          {state === "ready" ? (
            <AdminPagination
              page={page}
              pageSize={pageSize}
              total={total}
              onPageChange={handleWorkspacePageChange}
              onPageSizeChange={handleWorkspacePageSizeChange}
            />
          ) : null}
          <button
            type="button"
            onClick={openCreateModal}
            className="w-full border border-tide/40 bg-tide px-4 py-3 text-sm font-semibold text-paper transition hover:opacity-95"
          >
            Create workspace
          </button>
        </div>
        <div className="space-y-4">
          {selectedWorkspaceSummary ? (
            <section className="border border-ink/10 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h4 className="text-base font-semibold text-ink">Selected workspace</h4>
                  <p className="mt-1 text-xs uppercase tracking-wide text-clay">{selectedWorkspaceSummary.slug}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <RedisActionButton label="清理当前工作区 Redis 缓存" onClick={() => void handleClearWorkspaceDetailCache()} />
                  <button type="button" onClick={() => openViewModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    View
                  </button>
                  <button type="button" onClick={() => openEditModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    Edit
                  </button>
                  <button type="button" onClick={() => openDeleteModal()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                    Delete
                  </button>
                </div>
              </div>
              <div className="mt-4 grid gap-3 text-sm text-ink/75 md:grid-cols-2">
                <div><span className="font-semibold text-ink">Slug:</span> {selectedWorkspaceSummary.slug}</div>
                <div><span className="font-semibold text-ink">Name:</span> {selectedWorkspaceSummary.name}</div>
                <div><span className="font-semibold text-ink">Default:</span> {selectedWorkspaceSummary.is_default ? "Yes" : "No"}</div>
                <div><span className="font-semibold text-ink">Workspace ID:</span> {selectedWorkspaceSummary.id}</div>
              </div>
              <div className="mt-4 text-xs leading-6 text-ink/55">
                Created {formatDateTime(selectedWorkspaceSummary.created_at)}. Updated {formatDateTime(selectedWorkspaceSummary.updated_at)}.
              </div>
            </section>
          ) : null}
        </div>
      </div>

      <AdminEntityModal open={modal === "create"} title="Create workspace" description="Create a workspace and mark it as default if needed." onClose={closeModal}>
        <form onSubmit={(event) => void handleCreate(event)} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <InlineField label="Slug" value={createForm.slug} onChange={(slug) => setCreateForm((prev) => ({ ...prev, slug }))} />
            <InlineField label="Name" value={createForm.name} onChange={(name) => setCreateForm((prev) => ({ ...prev, name }))} />
          </div>
          <CheckboxField label="Default workspace" checked={createForm.isDefault} onChange={(isDefault) => setCreateForm((prev) => ({ ...prev, isDefault }))} />
          <div className="flex flex-wrap gap-3">
            <button type="submit" disabled={actionState === "create"} className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60">
              {actionState === "create" ? "Creating..." : "Create workspace"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </form>
      </AdminEntityModal>

      <AdminEntityModal open={modal === "view"} title="View workspace" description="Read-only details for the selected workspace." onClose={closeModal}>
        {selectedWorkspaceSummary ? (
          <div className="space-y-4 text-sm text-ink/75">
            <div className="grid gap-3 md:grid-cols-2">
              <div><span className="font-semibold text-ink">Slug:</span> {selectedWorkspaceSummary.slug}</div>
              <div><span className="font-semibold text-ink">Name:</span> {selectedWorkspaceSummary.name}</div>
              <div><span className="font-semibold text-ink">Default:</span> {selectedWorkspaceSummary.is_default ? "Yes" : "No"}</div>
              <div><span className="font-semibold text-ink">Workspace ID:</span> {selectedWorkspaceSummary.id}</div>
            </div>
          </div>
        ) : null}
      </AdminEntityModal>

      <AdminEntityModal open={modal === "edit"} title="Edit workspace" description="Update the slug, display name, and default flag." onClose={closeModal}>
        <form onSubmit={(event) => void handleUpdate(event)} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <InlineField label="Slug" value={editForm.slug} onChange={(slug) => setEditForm((prev) => ({ ...prev, slug }))} />
            <InlineField label="Name" value={editForm.name} onChange={(name) => setEditForm((prev) => ({ ...prev, name }))} />
          </div>
          <CheckboxField label="Default workspace" checked={editForm.isDefault} onChange={(isDefault) => setEditForm((prev) => ({ ...prev, isDefault }))} />
          <div className="flex flex-wrap gap-3">
            <button type="submit" disabled={actionState === "update"} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink disabled:opacity-60">
              {actionState === "update" ? "Saving..." : "Save workspace"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </form>
      </AdminEntityModal>

      <AdminEntityModal open={modal === "delete"} title="Delete workspace" description="This will remove the workspace and clean its membership records." onClose={closeModal}>
        <div className="space-y-4 text-sm text-ink/75">
          <p>
            Delete <span className="font-semibold text-ink">{selectedWorkspaceSummary?.slug}</span>?
          </p>
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => void handleDelete()} disabled={actionState === "delete"} className="border border-clay/30 bg-clay px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60">
              {actionState === "delete" ? "Deleting..." : "Delete workspace"}
            </button>
            <button type="button" onClick={closeModal} className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink">
              Cancel
            </button>
          </div>
        </div>
      </AdminEntityModal>
    </SectionFrame>
  );
}

export function AdminRbacManagement() {
  return (
    <AuthGate
      title="Admin RBAC Management"
      description="Manage users, roles, permissions, and the default workspace records that gate access to the knowledge base."
    >
      <div className="space-y-8">
        <UserManager />
        <RoleManager />
        <PermissionManager />
        <WorkspaceManager />
      </div>
    </AuthGate>
  );
}
