"use client";

import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  clearStoredAuthToken,
  fetchCurrentUser,
  getStoredAuthToken,
  login as loginRequest,
  setStoredAuthToken,
} from "@/lib/auth";
import type { AuthUser, LoginRequest } from "@/types/auth";

type AuthState = "loading" | "anonymous" | "authenticated" | "expired";

type AuthContextValue = {
  status: AuthState;
  user: AuthUser | null;
  token: string | null;
  login: (request: LoginRequest) => Promise<AuthUser>;
  logout: () => void;
  refreshSession: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

async function loadUserFromToken(token: string) {
  const user = await fetchCurrentUser(token);
  return { token, user };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthState>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);

  async function refreshSession() {
    const storedToken = getStoredAuthToken();
    if (!storedToken) {
      setStatus("anonymous");
      setUser(null);
      setToken(null);
      return;
    }

    try {
      const session = await loadUserFromToken(storedToken);
      setUser(session.user);
      setToken(session.token);
      setStatus("authenticated");
    } catch (error) {
      clearStoredAuthToken();
      setUser(null);
      setToken(null);
      setStatus(error instanceof ApiError && error.status === 401 ? "expired" : "anonymous");
    }
  }

  useEffect(() => {
    void refreshSession();
  }, []);

  async function login(request: LoginRequest) {
    const response = await loginRequest(request);
    setStoredAuthToken(response.access_token);
    const session = await loadUserFromToken(response.access_token);
    setUser(session.user);
    setToken(session.token);
    setStatus("authenticated");
    return session.user;
  }

  function logout() {
    clearStoredAuthToken();
    setStatus("anonymous");
    setUser(null);
    setToken(null);
  }

  return (
    <AuthContext.Provider
      value={{
        status,
        user,
        token,
        login,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
