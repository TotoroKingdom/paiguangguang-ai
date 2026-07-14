import { getJson, postJson } from "@/lib/api";
import { encryptLoginPassword } from "@/lib/login-encryption";
import type {
  AuthTokenData,
  AuthUser,
  EncryptedLoginRequest,
  LoginEncryptionKeyData,
  LoginRequest,
} from "@/types/auth";

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
  const keyData = await getJson<LoginEncryptionKeyData>("/api/v1/auth/encryption-key");
  const encryptedPassword = await encryptLoginPassword(request.password, keyData);
  const encryptedRequest: EncryptedLoginRequest = {
    email: request.email,
    ...encryptedPassword,
  };
  return postJson<AuthTokenData, EncryptedLoginRequest>(
    "/api/v1/auth/login",
    encryptedRequest
  );
}

export async function fetchCurrentUser(token?: string | null) {
  return getJson<AuthUser>("/api/v1/auth/me", { token: token ?? getStoredAuthToken() });
}
