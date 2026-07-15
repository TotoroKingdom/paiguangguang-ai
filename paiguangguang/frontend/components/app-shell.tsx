"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { SiteNav } from "@/components/site-nav";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname() || "/";
  const isHome = pathname === "/";
  const isChatbot = pathname === "/chat-bot";

  return (
    <>
      {!isHome && !isChatbot ? <SiteNav /> : null}
      <main
        className={
          isHome
            ? "w-full p-0"
            : isChatbot
              ? "h-dvh min-h-0 w-full overflow-hidden p-0"
              : "w-full px-4 py-6 sm:px-6 md:py-8 lg:px-8"
        }
      >
        {children}
      </main>
    </>
  );
}
