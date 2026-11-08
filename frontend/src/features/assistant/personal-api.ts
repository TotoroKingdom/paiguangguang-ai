import { csrfToken } from "@/features/auth/api";
import type { Capability } from "./types";

export type ServerSkill = {
  id: string;
  name: string;
  description: string;
  contentMd: string;
  version: number;
  createdAt: string;
  updatedAt: string;
};

export type ServerFile = {
  id: string;
  filename: string;
  contentType: string;
  sizeBytes: number;
  checksum: string;
  createdAt: string;
};

export type ServerMcp = {
  id: string;
  name: string;
  description: string;
  status: "pending" | "approved" | "disabled";
  transport: string;
  tools: { name?: string; description?: string }[];
  createdAt: string;
  reviewedAt: string | null;
};

export type ServerMcpConnection = {
  id: string;
  serverId: string;
  serverName: string;
  status: string;
  hasCredential: boolean;
  createdAt: string;
  lastUsedAt: string | null;
};

export class PersonalApiError extends Error {
  status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "PersonalApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  let response: Response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      ...init,
      headers: {
        ...(init?.body && !(init.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...(method !== "GET" && method !== "HEAD" ? { "X-CSRF-Token": csrfToken() } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new PersonalApiError("无法连接个人资源服务，请检查网络。", 0);
  }
  if (!response.ok) {
    let message = "个人资源请求失败，请重试。";
    try {
      const body = (await response.json()) as {
        error?: { message?: string };
        detail?: string;
      };
      message = body.error?.message ?? body.detail ?? message;
    } catch {
      /* keep fallback */
    }
    throw new PersonalApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function skillToCapability(skill: ServerSkill): Capability {
  return {
    id: skill.id,
    kind: "skill",
    name: skill.name,
    description: skill.description,
    category: "个人技能",
    icon: "skill",
    source: "personal",
    steps: ["加载个人技能", "执行任务"],
    content: skill.contentMd,
    version: skill.version,
  };
}

export async function listSkills(): Promise<ServerSkill[]> {
  const response = await request<{ items: ServerSkill[] }>("/api/v1/me/skills");
  return response.items;
}

export function createSkill(input: {
  name: string;
  description: string;
  contentMd: string;
}): Promise<ServerSkill> {
  return request<ServerSkill>("/api/v1/me/skills", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateSkill(
  id: string,
  input: { name: string; description: string; contentMd: string },
): Promise<ServerSkill> {
  return request<ServerSkill>(`/api/v1/me/skills/${id}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function deleteSkill(id: string): Promise<void> {
  return request<void>(`/api/v1/me/skills/${id}`, { method: "DELETE" });
}

export async function listFiles(): Promise<ServerFile[]> {
  const response = await request<{ items: ServerFile[] }>("/api/v1/me/files");
  return response.items;
}

export function uploadFile(file: File): Promise<ServerFile> {
  const body = new FormData();
  body.append("file", file, file.name);
  return request<ServerFile>("/api/v1/me/files", { method: "POST", body });
}

export function deleteFile(id: string): Promise<void> {
  return request<void>(`/api/v1/me/files/${id}`, { method: "DELETE" });
}

export function fileContentUrl(id: string): string {
  return `/api/v1/me/files/${id}/content`;
}

export async function listMcpServers(): Promise<ServerMcp[]> {
  const response = await request<{ items: ServerMcp[] }>("/api/v1/mcp/servers");
  return response.items;
}

export async function listMcpConnections(): Promise<ServerMcpConnection[]> {
  const response = await request<{ items: ServerMcpConnection[] }>(
    "/api/v1/me/mcp/connections",
  );
  return response.items;
}

export function connectMcp(serverId: string, token: string): Promise<ServerMcpConnection> {
  return request<ServerMcpConnection>("/api/v1/me/mcp/connections", {
    method: "POST",
    body: JSON.stringify({ serverId, token }),
  });
}

export function disconnectMcp(connectionId: string): Promise<void> {
  return request<void>(`/api/v1/me/mcp/connections/${connectionId}`, {
    method: "DELETE",
  });
}
