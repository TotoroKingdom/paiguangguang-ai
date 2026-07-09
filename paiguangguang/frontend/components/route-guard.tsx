"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/components/auth-provider";

type RouteGuardProps = {
  children: ReactNode;
};

function buildLoginHref(pathname: string, searchParams: Pick<URLSearchParams, "toString">) {
  const search = searchParams.toString();
  const nextPath = search ? `${pathname}?${search}` : pathname;
  return `/login?next=${encodeURIComponent(nextPath || "/")}`;
}

function isPublicRoute(pathname: string) {
  return pathname === "/" || pathname === "/login";
}

export function RouteGuard({ children }: RouteGuardProps) {
  const pathname = usePathname() || "/";
  const searchParams = useSearchParams();
  const router = useRouter();
  const { status } = useAuth();
  const publicRoute = isPublicRoute(pathname);
  const loginHref = buildLoginHref(pathname, searchParams);

  useEffect(() => {
    if (!publicRoute && (status === "anonymous" || status === "expired")) {
      router.replace(loginHref);
    }
  }, [loginHref, pathname, publicRoute, router, status]);

  if (publicRoute || status === "authenticated") {
    return <>{children}</>;
  }

  return (
    <div className="w-full px-4 py-10 sm:px-6 lg:px-8">
      <div className="border border-ink/10 bg-white/72 p-6 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-clay">Authentication</p>
        <h1 className="mt-2 text-2xl font-semibold text-ink">Checking session</h1>
        <p className="mt-2 text-sm leading-7 text-ink/70">
          {status === "loading" ? "Loading your session..." : "Redirecting to the login page..."}
        </p>
      </div>
    </div>
  );
}
