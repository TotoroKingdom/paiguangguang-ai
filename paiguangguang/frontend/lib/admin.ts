import { deleteJson, getJson, patchJson, postEmptyJson, postJson } from "@/lib/api";
import { getStoredAuthToken } from "@/lib/auth";
import type {
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
} from "@/types/admin";

export function listAdminDocuments() {
  return getJson<AdminDocumentData[]>("/api/v1/admin/documents", { token: getStoredAuthToken() });
}

export function getAdminDocument(documentId: string) {
  return getJson<AdminDocumentData>(`/api/v1/admin/documents/${documentId}`, { token: getStoredAuthToken() });
}

export function createAdminDocument(request: AdminDocumentCreateRequest) {
  return postJson<AdminDocumentData, AdminDocumentCreateRequest>("/api/v1/admin/documents", request, {
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

export function listAdminIngestionJobs() {
  return getJson<AdminIngestionJobData[]>("/api/v1/admin/ingestion-jobs", { token: getStoredAuthToken() });
}

export function getAdminIngestionJob(jobId: string) {
  return getJson<AdminIngestionJobData>(`/api/v1/admin/ingestion-jobs/${jobId}`, { token: getStoredAuthToken() });
}

export function listAdminUsers() {
  return getJson<AdminUserData[]>("/api/v1/admin/users", { token: getStoredAuthToken() });
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

export function disableAdminUser(userId: string) {
  return deleteJson<AdminUserData>(`/api/v1/admin/users/${userId}`, {
    token: getStoredAuthToken(),
  });
}

export function listAdminRoles() {
  return getJson<AdminRoleData[]>("/api/v1/admin/roles", { token: getStoredAuthToken() });
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

export function listAdminPermissions() {
  return getJson<AdminPermissionData[]>("/api/v1/admin/permissions", { token: getStoredAuthToken() });
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

export function listAdminWorkspaces() {
  return getJson<AdminWorkspaceData[]>("/api/v1/admin/workspaces", { token: getStoredAuthToken() });
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
