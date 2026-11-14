"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  AdminApiError,
  getAdminSession,
  loginAdmin,
  logoutAdmin,
  type AdminUser,
} from "./api";
import { getSession as getUnifiedSession } from "@/features/auth/api";

type AdminAuthState = {
  status: "loading" | "authenticated" | "anonymous";
  user: AdminUser | null;
  notice: string;
};

type AdminContextValue = AdminAuthState & {
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AdminContext = createContext<AdminContextValue | null>(null);

export function AdminProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AdminAuthState>({
    status: "loading",
    user: null,
    notice: "",
  });

  const refresh = useCallback(async () => {
    try {
      const session = await getAdminSession();
      setState({ status: "authenticated", user: session.user, notice: "" });
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 401) {
        try {
          const unified = await getUnifiedSession();
          if (unified.user.role === "ADMIN" && unified.user.status === "ACTIVE") {
            setState({
              status: "authenticated",
              user: {
                id: unified.user.id,
                username: unified.user.accountNumber,
                role: "admin",
                expiresAt: unified.session.expiresAt,
              },
              notice: "",
            });
            return;
          }
        } catch {
          /* fall through to anonymous */
        }
        setState({ status: "anonymous", user: null, notice: "" });
        return;
      }
      setState({
        status: "anonymous",
        user: null,
        notice:
          error instanceof AdminApiError ? error.message : "无法确认管理员会话，请重试。",
      });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (username: string, password: string) => {
    try {
      const session = await loginAdmin(username.trim(), password);
      setState({ status: "authenticated", user: session.user, notice: "" });
      return true;
    } catch (error) {
      const message =
        error instanceof AdminApiError
          ? error.status === 401
            ? "管理员用户名或密码错误。"
            : error.status === 403
              ? "该账户没有管理员权限。"
              : error.status === 423
                ? "登录失败次数过多，请稍后再试。"
                : error.message
          : "管理员登录失败，请检查凭据后重试。";
      setState((current) => ({
        ...current,
        status: "anonymous",
        user: null,
        notice: message,
      }));
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutAdmin();
    } finally {
      setState({ status: "anonymous", user: null, notice: "" });
    }
  }, []);

  return (
    <AdminContext.Provider value={{ ...state, login, logout, refresh }}>
      {children}
    </AdminContext.Provider>
  );
}

export function useAdmin(): AdminContextValue {
  const context = useContext(AdminContext);
  if (!context) throw new Error("useAdmin must be used within AdminProvider");
  return context;
}
