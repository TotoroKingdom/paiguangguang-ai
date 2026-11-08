"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  AuthApiError,
  getSession,
  loginAccount,
  logoutAccount,
  registerAccount,
  type AccountSession,
  type RegistrationResult,
} from "./api";

type AuthContextValue = {
  status: "loading" | "authenticated" | "anonymous";
  session: AccountSession | null;
  notice: string;
  registration: RegistrationResult | null;
  refresh: () => Promise<AccountSession | null>;
  login: (accountNumber: string, password: string) => Promise<AccountSession | null>;
  register: (input: {
    password: string;
    passwordConfirm: string;
    nickname: string;
  }) => Promise<RegistrationResult | null>;
  logout: () => Promise<void>;
  clearRegistration: () => void;
  canUseService: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthContextValue["status"]>("loading");
  const [session, setSession] = useState<AccountSession | null>(null);
  const [notice, setNotice] = useState("");
  const [registration, setRegistration] = useState<RegistrationResult | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await getSession();
      setSession(next);
      setStatus("authenticated");
      setNotice("");
      return next;
    } catch (error) {
      if (error instanceof AuthApiError && error.status === 401) {
        setSession(null);
        setStatus("anonymous");
        setNotice("");
        return null;
      }
      setSession(null);
      setStatus("anonymous");
      setNotice(error instanceof Error ? error.message : "无法确认账户会话。");
      return null;
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (accountNumber: string, password: string) => {
    try {
      const next = await loginAccount(accountNumber.trim(), password);
      setSession(next);
      setStatus("authenticated");
      setNotice("");
      return next;
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "登录失败，请重试。");
      return null;
    }
  }, []);

  const register = useCallback(
    async (input: { password: string; passwordConfirm: string; nickname: string }) => {
      try {
        const result = await registerAccount(input);
        setRegistration(result);
        setNotice("");
        return result;
      } catch (error) {
        setNotice(error instanceof Error ? error.message : "注册失败，请重试。");
        return null;
      }
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await logoutAccount();
    } finally {
      setSession(null);
      setStatus("anonymous");
      setRegistration(null);
    }
  }, []);

  const clearRegistration = useCallback(() => setRegistration(null), []);
  const canUseService =
    session?.user.status === "ACTIVE" && session.session.scope === "FULL";

  return (
    <AuthContext.Provider
      value={{
        status,
        session,
        notice,
        registration,
        refresh,
        login,
        register,
        logout,
        clearRegistration,
        canUseService,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}

export function useOptionalAuth(): AuthContextValue | null {
  return useContext(AuthContext);
}
