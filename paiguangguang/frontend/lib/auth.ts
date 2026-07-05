import { getJson, postJson } from "@/lib/api";
import type { AuthTokenData, AuthUser, LoginRequest } from "@/types/auth";

const AUTH_TOKEN_STORAGE_KEY = "paiguangguang.auth.token";

export function getStoredAuthToken() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

export function setStoredAuthToken(token: string) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

export function clearStoredAuthToken() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

export async function login(request: LoginRequest) {
  return postJson<AuthTokenData, LoginRequest>("/api/v1/auth/login", request);
}

export async function fetchCurrentUser(token?: string | null) {
  return getJson<AuthUser>("/api/v1/auth/me", { token: token ?? getStoredAuthToken() });
}
