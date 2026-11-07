import type { CapabilityKind } from "@/features/assistant/types";

export type AdminUser = {
  id: string;
  username: string;
  role: "admin" | "viewer";
  expiresAt: string;
};

export type AdminSession = {
  authenticated: boolean;
  user: AdminUser;
};

export type CapabilitySnapshot = {
  kind: CapabilityKind;
  name: string;
  description: string;
  category: string;
  icon: string;
  steps: string[];
  tools: string[];
  content: string | null;
  config: Record<string, unknown>;
  executionMode: "demo" | "simulated";
  source: "system" | "managed";
};

export type CapabilityVersion = {
  id: string;
  version: number;
  status: "draft" | "published" | "retired";
  snapshot: CapabilitySnapshot;
  changelog: string;
  createdBy: string;
  publishedBy: string;
  createdAt: string;
  publishedAt: string | null;
  retiredAt: string | null;
};

export type CapabilitySummary = {
  id: string;
  slug: string;
  kind: CapabilityKind;
  name: string;
  description: string;
  category: string;
  icon: string;
  status: "draft" | "published" | "disabled";
  source: "demo" | "admin";
  hasDraft: boolean;
  publishedVersion: number | null;
  draftVersion: number | null;
  executionMode: "demo" | "simulated" | null;
  updatedAt: string;
};

export type CapabilityDetail = CapabilitySummary & {
  createdAt: string;
  createdBy: string;
  draft: CapabilityVersion | null;
  published: CapabilityVersion | null;
  versions: CapabilityVersion[];
};

export type RunItem = {
  id: string;
  capabilityId: string;
  capabilityName: string;
  kind: CapabilityKind | null;
  version: number;
  conversationId: string;
  mode: string;
  status: string;
  createdAt: string;
};

export type AuditItem = {
  id: string;
  actorType: string;
  actorId: string;
  action: string;
  resourceType: string;
  resourceId: string;
  detail: Record<string, unknown>;
  createdAt: string;
};

export type Overview = {
  capabilities: {
    kind: CapabilityKind;
    total: number;
    published: number;
    draft: number;
    disabled: number;
  }[];
  totalRuns: number;
  recentRuns: RunItem[];
  recentAudit: AuditItem[];
  admin: { username: string; role: string; sessionExpiresAt: string };
  environment: string;
};

export type ReleaseItem = {
  capabilityId: string;
  capabilityName: string;
  kind: CapabilityKind;
  versionId: string;
  version: number;
  status: "published" | "retired";
  publishedBy: string;
  publishedAt: string | null;
  retiredAt: string | null;
};

export type AdminSettings = {
  environment: string;
  database: string;
  adminSessionMinutes: number;
  secureAdminCookie: boolean;
  allowedOrigins: string[];
  loginRateLimit: { attempts: number; windowSeconds: number; lockSeconds: number };
  executionMode: string;
  notes: string[];
};

export type CapabilityDraftInput = {
  name: string;
  description: string;
  category: string;
  icon: string;
  steps: string[];
  tools: string[];
  content: string | null;
  config: Record<string, unknown>;
};

export class AdminApiError extends Error {
  status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
  }
}

function csrfToken(): string {
  if (typeof document === "undefined") return "";
  const prefix = "paiguangguang_admin_csrf=";
  return (
    document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(prefix))
      ?.slice(prefix.length) ?? ""
  );
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  let response: Response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      ...init,
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(method !== "GET" && method !== "HEAD"
          ? { "X-CSRF-Token": csrfToken() }
          : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new AdminApiError("无法连接管理 API，请检查服务是否运行。", 0);
  }
  if (!response.ok) {
    let detail = "管理 API 请求失败，请重试。";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* Keep the fallback when the server returns a non-JSON body. */
    }
    throw new AdminApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function getAdminSession(): Promise<AdminSession> {
  return request<AdminSession>("/api/v1/admin/auth/session");
}

export async function loginAdmin(username: string, password: string): Promise<AdminSession> {
  return request<AdminSession>("/api/v1/admin/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function logoutAdmin(): Promise<void> {
  await request<void>("/api/v1/admin/auth/logout", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getOverview(): Promise<Overview> {
  return request<Overview>("/api/v1/admin/overview");
}

export async function listAdminCapabilities(params: {
  kind?: CapabilityKind;
  status?: string;
  q?: string;
}): Promise<CapabilitySummary[]> {
  const query = new URLSearchParams();
  if (params.kind) query.set("kind", params.kind);
  if (params.status) query.set("status", params.status);
  if (params.q?.trim()) query.set("q", params.q.trim());
  const response = await request<{ items: CapabilitySummary[] }>(
    `/api/v1/admin/capabilities?${query.toString()}`,
  );
  return response.items;
}

export async function createCapability(
  kind: CapabilityKind,
  draft: CapabilityDraftInput,
): Promise<CapabilityDetail> {
  return request<CapabilityDetail>("/api/v1/admin/capabilities", {
    method: "POST",
    body: JSON.stringify({ kind, ...draft, changelog: "创建能力草稿" }),
  });
}

export async function getCapability(id: string): Promise<CapabilityDetail> {
  return request<CapabilityDetail>(`/api/v1/admin/capabilities/${id}`);
}

export async function updateCapabilityDraft(
  id: string,
  draftVersionId: string | null,
  draft: CapabilityDraftInput,
): Promise<CapabilityDetail> {
  return request<CapabilityDetail>(`/api/v1/admin/capabilities/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ draftVersionId, ...draft }),
  });
}

export async function publishCapability(
  id: string,
  versionId: string,
): Promise<CapabilityDetail> {
  return request<CapabilityDetail>(`/api/v1/admin/capabilities/${id}/publish`, {
    method: "POST",
    body: JSON.stringify({ versionId, changelog: "发布新版本" }),
  });
}

export async function disableCapability(id: string): Promise<CapabilityDetail> {
  return request<CapabilityDetail>(`/api/v1/admin/capabilities/${id}/disable`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function listReleases(kind?: CapabilityKind): Promise<ReleaseItem[]> {
  const query = kind ? `?kind=${kind}` : "";
  const response = await request<{ items: ReleaseItem[] }>(
    `/api/v1/admin/releases${query}`,
  );
  return response.items;
}

export async function listRuns(cursor?: string): Promise<{
  items: RunItem[];
  total: number;
  nextCursor: string | null;
}> {
  const query = new URLSearchParams({ limit: "50" });
  if (cursor) query.set("cursor", cursor);
  return request(`/api/v1/admin/runs?${query.toString()}`);
}

export async function listAuditEvents(cursor?: string): Promise<{
  items: AuditItem[];
  total: number;
  nextCursor: string | null;
}> {
  const query = new URLSearchParams({ limit: "50" });
  if (cursor) query.set("cursor", cursor);
  return request(`/api/v1/admin/audit-events?${query.toString()}`);
}

export async function getAdminSettings(): Promise<AdminSettings> {
  return request<AdminSettings>("/api/v1/admin/settings");
}
