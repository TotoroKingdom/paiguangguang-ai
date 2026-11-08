export type AccountRole = "USER" | "CREATOR" | "ADMIN";
export type AccountStatus = "PENDING" | "ACTIVE" | "DISABLED" | "REJECTED";
export type SessionScope = "FULL" | "STATUS_ONLY";

export type AccountUser = {
  id: string;
  accountNumber: string;
  nickname: string;
  role: AccountRole;
  status: AccountStatus;
  version: number;
  createdAt: string;
  activatedAt: string | null;
  lastLoginAt: string | null;
};

export type AccountSession = {
  authenticated: boolean;
  user: AccountUser;
  session: { scope: SessionScope; expiresAt: string };
};

export type RecoveryMaterial = { code: string; issuedAt: string; displayMode: "ONE_TIME" };

export type RegistrationResult = {
  user: AccountUser;
  recovery: RecoveryMaterial | null;
  sessionIssued: boolean;
  replayed: boolean;
};

export class AuthApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status = 0, code = "") {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
    this.code = code;
  }
}

export function csrfToken(): string {
  if (typeof document === "undefined") return "";
  const prefix = "paiguangguang_csrf=";
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
        ...(method !== "GET" && method !== "HEAD" ? { "X-CSRF-Token": csrfToken() } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new AuthApiError("无法连接账户服务，请检查网络后重试。", 0, "NETWORK");
  }
  if (!response.ok) {
    let message = "账户服务暂时不可用，请重试。";
    let code = "";
    try {
      const body = (await response.json()) as {
        error?: { code?: string; message?: string };
        detail?: string | { code?: string; message?: string };
      };
      if (body.error?.message) {
        message = body.error.message;
        code = body.error.code ?? "";
      } else if (typeof body.detail === "object" && body.detail?.message) {
        message = body.detail.message;
        code = body.detail.code ?? "";
      } else if (typeof body.detail === "string") {
        message = body.detail;
      }
    } catch {
      /* keep fallback */
    }
    if (response.status === 401 && code === "AUTH_INVALID_CREDENTIALS") {
      message = "账号或密码错误。";
    }
    throw new AuthApiError(message, response.status, code);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function getSession(): Promise<AccountSession> {
  return request<AccountSession>("/api/v1/auth/session");
}

export async function loginAccount(accountNumber: string, password: string): Promise<AccountSession> {
  return request<AccountSession>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ accountNumber, password }),
  });
}

export function registerAccount(input: {
  password: string;
  passwordConfirm: string;
  nickname: string;
}): Promise<RegistrationResult> {
  return request<RegistrationResult>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
    headers: { "Idempotency-Key": crypto.randomUUID() },
  });
}

export function logoutAccount(): Promise<void> {
  return request<void>("/api/v1/auth/logout", { method: "POST", body: "{}" });
}

export function changePassword(input: {
  currentPassword: string;
  newPassword: string;
  newPasswordConfirm: string;
}): Promise<{ recovery: RecoveryMaterial }> {
  return request("/api/v1/auth/password/change", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function rotateRecovery(currentPassword: string): Promise<{ recovery: RecoveryMaterial }> {
  return request("/api/v1/auth/recovery/rotate", {
    method: "POST",
    body: JSON.stringify({ currentPassword }),
  });
}

export function completeRecovery(input: {
  accountNumber: string;
  recoveryCode: string;
  newPassword: string;
  newPasswordConfirm: string;
}): Promise<{ recovery: RecoveryMaterial }> {
  return request("/api/v1/auth/recovery/complete", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function claimLegacyConversations(conversationIds: string[] = []): Promise<{
  claimed: number;
  skipped: number;
  conversationIds: string[];
}> {
  return request("/api/v1/me/legacy-conversations/claim", {
    method: "POST",
    body: JSON.stringify({ conversationIds }),
  });
}

export type AdminUserList = {
  items: AccountUser[];
  total: number;
  nextCursor: string | null;
};

export function adminListUsers(params: {
  status?: string;
  role?: string;
  q?: string;
  cursor?: string;
}): Promise<AdminUserList> {
  const query = new URLSearchParams({ limit: "50" });
  if (params.status) query.set("status", params.status);
  if (params.role) query.set("role", params.role);
  if (params.q?.trim()) query.set("q", params.q.trim());
  if (params.cursor) query.set("cursor", params.cursor);
  return request(`/api/v1/admin/users?${query.toString()}`);
}

export function moderateUser(
  userId: string,
  action: "activate" | "reject" | "disable" | "restore",
  expectedVersion: number,
  reason: string,
): Promise<{ user: AccountUser; auditEventId: string }> {
  return request(`/api/v1/admin/users/${userId}/${action}`, {
    method: "POST",
    body: JSON.stringify({ expectedVersion, reason }),
  });
}

export function setUserRole(
  userId: string,
  role: AccountRole,
  expectedVersion: number,
  reason: string,
): Promise<{ user: AccountUser; auditEventId: string }> {
  return request(`/api/v1/admin/users/${userId}/roles`, {
    method: "PATCH",
    body: JSON.stringify({ role, expectedVersion, reason }),
  });
}
