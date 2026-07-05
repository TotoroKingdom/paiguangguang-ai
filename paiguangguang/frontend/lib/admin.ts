import { deleteJson, getJson, patchJson, postEmptyJson, postJson } from "@/lib/api";
import { getStoredAuthToken } from "@/lib/auth";
import type {
  AdminDocumentCreateRequest,
  AdminDocumentData,
  AdminDocumentUpdateRequest,
  AdminIngestionJobData,
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
