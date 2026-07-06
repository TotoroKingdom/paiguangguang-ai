"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { ApiError } from "@/lib/api";
import {
  createAdminPermission,
  createAdminRole,
  createAdminUser,
  createAdminWorkspace,
  deleteAdminPermission,
  deleteAdminRole,
  deleteAdminWorkspace,
  disableAdminUser,
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
import { AdminPagination } from "@/features/admin/admin-pagination";
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

function splitCsv(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinCsv(value: string[] | null | undefined) {
  return (value ?? []).join(", ");
}

function SectionFrame({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
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
  const [actionState, setActionState] = useState<"create" | "update" | "disable" | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [sortBy, setSortBy] = useState("email");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [total, setTotal] = useState(0);
  const [createForm, setCreateForm] = useState({
    email: "",
    displayName: "",
    password: "",
    isActive: true,
    roles: "",
    workspaceSlugs: "",
  });
  const [editForm, setEditForm] = useState({
    displayName: "",
    password: "",
    isActive: true,
    roles: "",
    workspaceSlugs: "",
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
    void loadUsers();
  }, [page, pageSize, sortBy, sortOrder]);

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
          roles: joinCsv(user.roles),
          workspaceSlugs: joinCsv(user.workspace_ids),
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
  }, [selectedUserId]);

  const selectedUserSummary = selectedUser ?? users.find((user) => user.id === selectedUserId) ?? null;

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
        roles: splitCsv(createForm.roles),
        workspace_slugs: splitCsv(createForm.workspaceSlugs),
      });
      setCreateForm({ email: "", displayName: "", password: "", isActive: true, roles: "", workspaceSlugs: "" });
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
        roles: splitCsv(editForm.roles),
        workspace_slugs: splitCsv(editForm.workspaceSlugs),
      });
      await loadUsers(selectedUserSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to update user."));
    } finally {
      setActionState(null);
    }
  }

  async function handleDisable() {
    if (!selectedUserSummary) {
      return;
    }
    if (!window.confirm(`Disable ${selectedUserSummary.email}?`)) {
      return;
    }
    setActionState("disable");
    setError(null);
    try {
      await disableAdminUser(selectedUserSummary.id);
      await loadUsers(selectedUserSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to disable user."));
    } finally {
      setActionState(null);
    }
  }

  return (
    <SectionFrame
      title="Users"
      description="Create users, edit display names and status, and assign roles or default workspace memberships."
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
        </div>
        <div className="space-y-4">
          <form onSubmit={(event) => void handleCreate(event)} className="border border-ink/10 bg-paper/70 p-4">
            <h4 className="text-base font-semibold text-ink">Create user</h4>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <InlineField label="Email" value={createForm.email} onChange={(email) => setCreateForm((prev) => ({ ...prev, email }))} type="email" />
              <InlineField label="Display name" value={createForm.displayName} onChange={(displayName) => setCreateForm((prev) => ({ ...prev, displayName }))} />
              <InlineField label="Password" value={createForm.password} onChange={(password) => setCreateForm((prev) => ({ ...prev, password }))} type="password" />
              <CheckboxField label="Active" checked={createForm.isActive} onChange={(isActive) => setCreateForm((prev) => ({ ...prev, isActive }))} />
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <InlineField label="Roles" value={createForm.roles} onChange={(roles) => setCreateForm((prev) => ({ ...prev, roles }))} placeholder="user, document_admin" />
              <InlineField label="Workspace slugs" value={createForm.workspaceSlugs} onChange={(workspaceSlugs) => setCreateForm((prev) => ({ ...prev, workspaceSlugs }))} placeholder="default, docs" />
            </div>
            <button
              type="submit"
              disabled={actionState === "create"}
              className="mt-4 border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60"
            >
              {actionState === "create" ? "Creating..." : "Create user"}
            </button>
          </form>

          {selectedUserSummary ? (
            <form onSubmit={(event) => void handleUpdate(event)} className="border border-ink/10 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h4 className="text-base font-semibold text-ink">Edit user</h4>
                  <p className="mt-1 text-xs uppercase tracking-wide text-clay">{selectedUserSummary.id}</p>
                </div>
                <button
                  type="button"
                  onClick={() => void handleDisable()}
                  className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink"
                >
                  {actionState === "disable" ? "Disabling..." : "Disable"}
                </button>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <InlineField label="Display name" value={editForm.displayName} onChange={(displayName) => setEditForm((prev) => ({ ...prev, displayName }))} />
                <InlineField label="Password" value={editForm.password} onChange={(password) => setEditForm((prev) => ({ ...prev, password }))} type="password" placeholder="Leave blank to keep current password" />
                <CheckboxField label="Active" checked={editForm.isActive} onChange={(isActive) => setEditForm((prev) => ({ ...prev, isActive }))} />
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <InlineField label="Roles" value={editForm.roles} onChange={(roles) => setEditForm((prev) => ({ ...prev, roles }))} placeholder="user, document_admin" />
                <InlineField label="Workspace slugs" value={editForm.workspaceSlugs} onChange={(workspaceSlugs) => setEditForm((prev) => ({ ...prev, workspaceSlugs }))} placeholder="default" />
              </div>
              <div className="mt-4 text-xs leading-6 text-ink/55">
                Created {formatDateTime(selectedUserSummary.created_at)}. Updated {formatDateTime(selectedUserSummary.updated_at)}.
              </div>
              <button
                type="submit"
                disabled={actionState === "update"}
                className="mt-4 border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink disabled:opacity-60"
              >
                {actionState === "update" ? "Saving..." : "Save user"}
              </button>
            </form>
          ) : null}
        </div>
      </div>
    </SectionFrame>
  );
}

export function RoleManager() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [roles, setRoles] = useState<AdminRoleData[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<AdminRoleData | null>(null);
  const [actionState, setActionState] = useState<"create" | "update" | "delete" | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [sortBy, setSortBy] = useState("name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [total, setTotal] = useState(0);
  const [createForm, setCreateForm] = useState({ name: "", description: "", permissions: "" });
  const [editForm, setEditForm] = useState({ name: "", description: "", permissions: "" });

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
          permissions: joinCsv(role.permissions),
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

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionState("create");
    setError(null);
    try {
      await createAdminRole({
        name: createForm.name,
        description: createForm.description || null,
        permissions: splitCsv(createForm.permissions),
      });
      setCreateForm({ name: "", description: "", permissions: "" });
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
        permissions: splitCsv(editForm.permissions),
      });
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
    if (!window.confirm(`Delete role ${selectedRoleSummary.name}?`)) {
      return;
    }
    setActionState("delete");
    setError(null);
    try {
      await deleteAdminRole(selectedRoleSummary.id);
      await loadRoles(selectedRoleSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to delete role."));
    } finally {
      setActionState(null);
    }
  }

  return (
    <SectionFrame
      title="Roles"
      description="Create roles, edit their permissions, and inspect the permission bundles assigned to staff accounts."
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
        </div>
        <div className="space-y-4">
          <form onSubmit={(event) => void handleCreate(event)} className="border border-ink/10 bg-paper/70 p-4">
            <h4 className="text-base font-semibold text-ink">Create role</h4>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <InlineField label="Name" value={createForm.name} onChange={(name) => setCreateForm((prev) => ({ ...prev, name }))} />
              <TextAreaField label="Description" value={createForm.description} onChange={(description) => setCreateForm((prev) => ({ ...prev, description }))} />
            </div>
            <div className="mt-4">
              <InlineField label="Permissions" value={createForm.permissions} onChange={(permissions) => setCreateForm((prev) => ({ ...prev, permissions }))} placeholder="document.view, document.delete" />
            </div>
            <button type="submit" disabled={actionState === "create"} className="mt-4 border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60">
              {actionState === "create" ? "Creating..." : "Create role"}
            </button>
          </form>

          {selectedRoleSummary ? (
            <form onSubmit={(event) => void handleUpdate(event)} className="border border-ink/10 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h4 className="text-base font-semibold text-ink">Edit role</h4>
                  <p className="mt-1 text-xs uppercase tracking-wide text-clay">{selectedRoleSummary.id}</p>
                </div>
                <button type="button" onClick={() => void handleDelete()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                  {actionState === "delete" ? "Deleting..." : "Delete"}
                </button>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <InlineField label="Name" value={editForm.name} onChange={(name) => setEditForm((prev) => ({ ...prev, name }))} />
                <TextAreaField label="Description" value={editForm.description} onChange={(description) => setEditForm((prev) => ({ ...prev, description }))} />
              </div>
              <div className="mt-4">
                <InlineField label="Permissions" value={editForm.permissions} onChange={(permissions) => setEditForm((prev) => ({ ...prev, permissions }))} placeholder="document.view, document.reindex" />
              </div>
              <div className="mt-4 text-xs leading-6 text-ink/55">
                Created {formatDateTime(selectedRoleSummary.created_at)}. Updated {formatDateTime(selectedRoleSummary.updated_at)}.
              </div>
              <button type="submit" disabled={actionState === "update"} className="mt-4 border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink disabled:opacity-60">
                {actionState === "update" ? "Saving..." : "Save role"}
              </button>
            </form>
          ) : null}
        </div>
      </div>
    </SectionFrame>
  );
}

export function PermissionManager() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<AdminPermissionData[]>([]);
  const [selectedPermissionId, setSelectedPermissionId] = useState<string | null>(null);
  const [selectedPermission, setSelectedPermission] = useState<AdminPermissionData | null>(null);
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
    if (!window.confirm(`Delete permission ${selectedPermissionSummary.name}?`)) {
      return;
    }
    setActionState("delete");
    setError(null);
    try {
      await deleteAdminPermission(selectedPermissionSummary.id);
      await loadPermissions(selectedPermissionSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to delete permission."));
    } finally {
      setActionState(null);
    }
  }

  return (
    <SectionFrame
      title="Permissions"
      description="Create and edit permission definitions that can be assigned to roles."
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
        </div>
        <div className="space-y-4">
          <form onSubmit={(event) => void handleCreate(event)} className="border border-ink/10 bg-paper/70 p-4">
            <h4 className="text-base font-semibold text-ink">Create permission</h4>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <InlineField label="Name" value={createForm.name} onChange={(name) => setCreateForm((prev) => ({ ...prev, name }))} />
              <TextAreaField label="Description" value={createForm.description} onChange={(description) => setCreateForm((prev) => ({ ...prev, description }))} />
            </div>
            <button type="submit" disabled={actionState === "create"} className="mt-4 border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60">
              {actionState === "create" ? "Creating..." : "Create permission"}
            </button>
          </form>

          {selectedPermissionSummary ? (
            <form onSubmit={(event) => void handleUpdate(event)} className="border border-ink/10 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h4 className="text-base font-semibold text-ink">Edit permission</h4>
                  <p className="mt-1 text-xs uppercase tracking-wide text-clay">{selectedPermissionSummary.id}</p>
                </div>
                <button type="button" onClick={() => void handleDelete()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                  {actionState === "delete" ? "Deleting..." : "Delete"}
                </button>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <InlineField label="Name" value={editForm.name} onChange={(name) => setEditForm((prev) => ({ ...prev, name }))} />
                <TextAreaField label="Description" value={editForm.description} onChange={(description) => setEditForm((prev) => ({ ...prev, description }))} />
              </div>
              <div className="mt-4 text-xs leading-6 text-ink/55">
                Created {formatDateTime(selectedPermissionSummary.created_at)}. Updated {formatDateTime(selectedPermissionSummary.updated_at)}.
              </div>
              <button type="submit" disabled={actionState === "update"} className="mt-4 border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink disabled:opacity-60">
                {actionState === "update" ? "Saving..." : "Save permission"}
              </button>
            </form>
          ) : null}
        </div>
      </div>
    </SectionFrame>
  );
}

export function WorkspaceManager() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<AdminWorkspaceData[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [selectedWorkspace, setSelectedWorkspace] = useState<AdminWorkspaceData | null>(null);
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
    if (!window.confirm(`Delete workspace ${selectedWorkspaceSummary.slug}?`)) {
      return;
    }
    setActionState("delete");
    setError(null);
    try {
      await deleteAdminWorkspace(selectedWorkspaceSummary.id);
      await loadWorkspaces(selectedWorkspaceSummary.id);
    } catch (caughtError) {
      setError(formatError(caughtError, "Unable to delete workspace."));
    } finally {
      setActionState(null);
    }
  }

  return (
    <SectionFrame
      title="Workspaces"
      description="Maintain workspace records and mark the current default workspace for permission scoping."
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
        </div>
        <div className="space-y-4">
          <form onSubmit={(event) => void handleCreate(event)} className="border border-ink/10 bg-paper/70 p-4">
            <h4 className="text-base font-semibold text-ink">Create workspace</h4>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <InlineField label="Slug" value={createForm.slug} onChange={(slug) => setCreateForm((prev) => ({ ...prev, slug }))} />
              <InlineField label="Name" value={createForm.name} onChange={(name) => setCreateForm((prev) => ({ ...prev, name }))} />
            </div>
            <div className="mt-4">
              <CheckboxField label="Default workspace" checked={createForm.isDefault} onChange={(isDefault) => setCreateForm((prev) => ({ ...prev, isDefault }))} />
            </div>
            <button type="submit" disabled={actionState === "create"} className="mt-4 border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper disabled:opacity-60">
              {actionState === "create" ? "Creating..." : "Create workspace"}
            </button>
          </form>

          {selectedWorkspaceSummary ? (
            <form onSubmit={(event) => void handleUpdate(event)} className="border border-ink/10 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h4 className="text-base font-semibold text-ink">Edit workspace</h4>
                  <p className="mt-1 text-xs uppercase tracking-wide text-clay">{selectedWorkspaceSummary.id}</p>
                </div>
                <button type="button" onClick={() => void handleDelete()} className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink">
                  {actionState === "delete" ? "Deleting..." : "Delete"}
                </button>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <InlineField label="Slug" value={editForm.slug} onChange={(slug) => setEditForm((prev) => ({ ...prev, slug }))} />
                <InlineField label="Name" value={editForm.name} onChange={(name) => setEditForm((prev) => ({ ...prev, name }))} />
              </div>
              <div className="mt-4">
                <CheckboxField label="Default workspace" checked={editForm.isDefault} onChange={(isDefault) => setEditForm((prev) => ({ ...prev, isDefault }))} />
              </div>
              <div className="mt-4 text-xs leading-6 text-ink/55">
                Created {formatDateTime(selectedWorkspaceSummary.created_at)}. Updated {formatDateTime(selectedWorkspaceSummary.updated_at)}.
              </div>
              <button type="submit" disabled={actionState === "update"} className="mt-4 border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink disabled:opacity-60">
                {actionState === "update" ? "Saving..." : "Save workspace"}
              </button>
            </form>
          ) : null}
        </div>
      </div>
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
