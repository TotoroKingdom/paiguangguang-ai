import { deleteJson, getJson, patchJson, postEmptyJson, postFormData, postJson } from "@/lib/api";
import { getStoredAuthToken } from "@/lib/auth";
import type {
  AdminPagedResponse,
  AdminPermissionCreateRequest,
  AdminPermissionData,
  AdminPermissionUpdateRequest,
  AdminRoleCreateRequest,
  AdminRoleData,
  AdminRoleUpdateRequest,
  AdminDocumentCreateRequest,
  AdminDocumentData,
  AdminDocumentUpdateRequest,
  AdminIngestionJobData,
  AdminUserCreateRequest,
  AdminUserData,
  AdminUserUpdateRequest,
  AdminWorkspaceCreateRequest,
  AdminWorkspaceData,
  AdminWorkspaceUpdateRequest,
  AdminCacheClearDetailRequest,
  AdminCacheClearListRequest,
} from "@/types/admin";

type AdminListQuery = {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
};

function toAdminPagedResponse<T>(payload: { items: T[]; total: number; page: number; page_size: number }) {
  return Object.assign([...payload.items], {
    total: payload.total,
    page: payload.page,
    page_size: payload.page_size,
  }) as AdminPagedResponse<T>;
}

function buildAdminListQuery(options?: AdminListQuery) {
  const params = new URLSearchParams();
  if (options?.page !== undefined) {
    params.set("page", String(options.page));
  }
  if (options?.pageSize !== undefined) {
    params.set("page_size", String(options.pageSize));
  }
  if (options?.sortBy) {
    params.set("sort_by", options.sortBy);
  }
  if (options?.sortOrder) {
    params.set("sort_order", options.sortOrder);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function listAdminDocuments(options?: AdminListQuery) {
  return getJson<{ items: AdminDocumentData[]; total: number; page: number; page_size: number }>(
    `/api/v1/admin/documents${buildAdminListQuery(options)}`,
    { token: getStoredAuthToken() }
  ).then(toAdminPagedResponse);
}

export function getAdminDocument(documentId: string) {
  return getJson<AdminDocumentData>(`/api/v1/admin/documents/${documentId}`, { token: getStoredAuthToken() });
}

export function createAdminDocument(request: AdminDocumentCreateRequest) {
  return postJson<AdminDocumentData, AdminDocumentCreateRequest>("/api/v1/admin/documents", request, {
    token: getStoredAuthToken(),
  });
}

export function uploadAdminDocument(formData: FormData) {
  return postFormData<AdminDocumentData>("/api/v1/admin/documents/upload", formData, {
    token: getStoredAuthToken(),
  });
}

export function updateAdminDocument(documentId: string, request: AdminDocumentUpdateRequest) {
  return patchJson<AdminDocumentData, AdminDocumentUpdateRequest>(
    `/api/v1/admin/documents/${documentId}`,
    request,
    {
      token: getStoredAuthToken(),
    }
  );
}

export function deleteAdminDocument(documentId: string) {
  return deleteJson<AdminDocumentData>(`/api/v1/admin/documents/${documentId}`, {
    token: getStoredAuthToken(),
  });
}

export function reindexAdminDocument(documentId: string) {
  return postEmptyJson<AdminDocumentData>(`/api/v1/admin/documents/${documentId}/reindex`, {
    token: getStoredAuthToken(),
  });
}

export function restoreAdminDocument(documentId: string) {
  return postEmptyJson<AdminDocumentData>(`/api/v1/admin/documents/${documentId}/restore`, {
    token: getStoredAuthToken(),
  });
}

export function listAdminIngestionJobs(options?: AdminListQuery) {
  return getJson<{ items: AdminIngestionJobData[]; total: number; page: number; page_size: number }>(
    `/api/v1/admin/ingestion-jobs${buildAdminListQuery(options)}`,
    { token: getStoredAuthToken() }
  ).then(toAdminPagedResponse);
}

export function getAdminIngestionJob(jobId: string) {
  return getJson<AdminIngestionJobData>(`/api/v1/admin/ingestion-jobs/${jobId}`, { token: getStoredAuthToken() });
}

export function listAdminUsers(options?: AdminListQuery) {
  return getJson<{ items: AdminUserData[]; total: number; page: number; page_size: number }>(
    `/api/v1/admin/users${buildAdminListQuery(options)}`,
    { token: getStoredAuthToken() }
  ).then(toAdminPagedResponse);
}

export function getAdminUser(userId: string) {
  return getJson<AdminUserData>(`/api/v1/admin/users/${userId}`, { token: getStoredAuthToken() });
}

export function createAdminUser(request: AdminUserCreateRequest) {
  return postJson<AdminUserData, AdminUserCreateRequest>("/api/v1/admin/users", request, {
    token: getStoredAuthToken(),
  });
}

export function updateAdminUser(userId: string, request: AdminUserUpdateRequest) {
  return patchJson<AdminUserData, AdminUserUpdateRequest>(`/api/v1/admin/users/${userId}`, request, {
    token: getStoredAuthToken(),
  });
}

export function deleteAdminUser(userId: string) {
  return deleteJson<AdminUserData>(`/api/v1/admin/users/${userId}`, {
    token: getStoredAuthToken(),
  });
}

export function disableAdminUser(userId: string) {
  return deleteAdminUser(userId);
}

export function activateAdminUser(userId: string) {
  return postEmptyJson<AdminUserData>(`/api/v1/admin/users/${userId}/activate`, {
    token: getStoredAuthToken(),
  });
}

export function listAdminRoles(options?: AdminListQuery) {
  return getJson<{ items: AdminRoleData[]; total: number; page: number; page_size: number }>(
    `/api/v1/admin/roles${buildAdminListQuery(options)}`,
    { token: getStoredAuthToken() }
  ).then(toAdminPagedResponse);
}

export function getAdminRole(roleId: string) {
  return getJson<AdminRoleData>(`/api/v1/admin/roles/${roleId}`, { token: getStoredAuthToken() });
}

export function createAdminRole(request: AdminRoleCreateRequest) {
  return postJson<AdminRoleData, AdminRoleCreateRequest>("/api/v1/admin/roles", request, {
    token: getStoredAuthToken(),
  });
}

export function updateAdminRole(roleId: string, request: AdminRoleUpdateRequest) {
  return patchJson<AdminRoleData, AdminRoleUpdateRequest>(`/api/v1/admin/roles/${roleId}`, request, {
    token: getStoredAuthToken(),
  });
}

export function deleteAdminRole(roleId: string) {
  return deleteJson<AdminRoleData>(`/api/v1/admin/roles/${roleId}`, {
    token: getStoredAuthToken(),
  });
}

export function listAdminPermissions(options?: AdminListQuery) {
  return getJson<{ items: AdminPermissionData[]; total: number; page: number; page_size: number }>(
    `/api/v1/admin/permissions${buildAdminListQuery(options)}`,
    { token: getStoredAuthToken() }
  ).then(toAdminPagedResponse);
}

export function getAdminPermission(permissionId: string) {
  return getJson<AdminPermissionData>(`/api/v1/admin/permissions/${permissionId}`, { token: getStoredAuthToken() });
}

export function createAdminPermission(request: AdminPermissionCreateRequest) {
  return postJson<AdminPermissionData, AdminPermissionCreateRequest>("/api/v1/admin/permissions", request, {
    token: getStoredAuthToken(),
  });
}

export function updateAdminPermission(permissionId: string, request: AdminPermissionUpdateRequest) {
  return patchJson<AdminPermissionData, AdminPermissionUpdateRequest>(
    `/api/v1/admin/permissions/${permissionId}`,
    request,
    {
      token: getStoredAuthToken(),
    }
  );
}

export function deleteAdminPermission(permissionId: string) {
  return deleteJson<AdminPermissionData>(`/api/v1/admin/permissions/${permissionId}`, {
    token: getStoredAuthToken(),
  });
}

export function listAdminWorkspaces(options?: AdminListQuery) {
  return getJson<{ items: AdminWorkspaceData[]; total: number; page: number; page_size: number }>(
    `/api/v1/admin/workspaces${buildAdminListQuery(options)}`,
    { token: getStoredAuthToken() }
  ).then(toAdminPagedResponse);
}

export function getAdminWorkspace(workspaceId: string) {
  return getJson<AdminWorkspaceData>(`/api/v1/admin/workspaces/${workspaceId}`, { token: getStoredAuthToken() });
}

export function createAdminWorkspace(request: AdminWorkspaceCreateRequest) {
  return postJson<AdminWorkspaceData, AdminWorkspaceCreateRequest>("/api/v1/admin/workspaces", request, {
    token: getStoredAuthToken(),
  });
}

export function updateAdminWorkspace(workspaceId: string, request: AdminWorkspaceUpdateRequest) {
  return patchJson<AdminWorkspaceData, AdminWorkspaceUpdateRequest>(
    `/api/v1/admin/workspaces/${workspaceId}`,
    request,
    {
      token: getStoredAuthToken(),
    }
  );
}

export function deleteAdminWorkspace(workspaceId: string) {
  return deleteJson<AdminWorkspaceData>(`/api/v1/admin/workspaces/${workspaceId}`, {
    token: getStoredAuthToken(),
  });
}

export function clearAdminEntityListCache(request: AdminCacheClearListRequest) {
  return postJson<{ cleared: "list"; entity: string }, AdminCacheClearListRequest>("/api/v1/admin/cache/clear-list", request, {
    token: getStoredAuthToken(),
  });
}

export function clearAdminEntityDetailCache(request: AdminCacheClearDetailRequest) {
  return postJson<{ cleared: "detail"; entity: string; entity_id: string }, AdminCacheClearDetailRequest>(
    "/api/v1/admin/cache/clear-detail",
    request,
    {
      token: getStoredAuthToken(),
    }
  );
}
