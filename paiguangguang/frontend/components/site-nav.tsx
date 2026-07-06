"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth-provider";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/agents/knowledge", label: "Knowledge" },
  { href: "/agents/browser", label: "Browser" },
  { href: "/agents/office", label: "Office" },
  { href: "/architecture", label: "Architecture" },
  { href: "/admin", label: "Admin" }
];

export function SiteNav() {
  const pathname = usePathname();
  const { status, user, logout } = useAuth();
  const loginHref = `/login?next=${encodeURIComponent(pathname || "/")}`;

  return (
    <header className="border-b border-ink/10 bg-paper/85 backdrop-blur">
      <nav className="flex w-full flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center">
          <Link href="/" className="text-lg font-semibold tracking-normal text-ink">
            Pai Guangguang AI Lab
          </Link>
          <div className="flex flex-wrap gap-2">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-current={pathname === item.href ? "page" : undefined}
                className={[
                  "border px-3 py-2 text-sm font-medium transition",
                  pathname === item.href
                    ? "border-tide/55 bg-tide text-paper shadow-sm"
                    : "border-ink/10 bg-white/55 text-ink hover:border-tide/40 hover:bg-white"
                ].join(" ")}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {status === "authenticated" ? (
            <>
              <div className="border border-tide/20 bg-tide/10 px-3 py-2 text-sm font-semibold text-tide">
                {user?.email}
              </div>
              <button
                type="button"
                onClick={logout}
                className="border border-ink/10 bg-white/55 px-3 py-2 text-sm font-semibold text-ink transition hover:border-ink/20 hover:bg-white"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link
              href={loginHref}
              className="border border-tide/40 bg-tide px-3 py-2 text-sm font-semibold text-paper transition hover:bg-tide/90"
            >
              Sign in
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
