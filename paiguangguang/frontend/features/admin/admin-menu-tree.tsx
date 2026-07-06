"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type AdminMenuItem = {
  href: string;
  label: string;
  description: string;
};

const adminMenuItems: AdminMenuItem[] = [
  { href: "/admin/documents", label: "Documents", description: "Document lifecycle and ingestion" },
  { href: "/admin/users", label: "Users", description: "Account access and workspace membership" },
  { href: "/admin/roles", label: "Roles", description: "Role bundles and assigned permissions" },
  { href: "/admin/permissions", label: "Permissions", description: "Permission catalog" },
  { href: "/admin/workspaces", label: "Workspaces", description: "Workspace registry and default flag" },
];

function isActivePath(pathname: string | null, href: string) {
  return pathname === href || pathname?.startsWith(`${href}/`);
}

export function AdminMenuTree() {
  const pathname = usePathname();

  return (
    <nav aria-label="Admin sections" className="border border-ink/10 bg-white/72 p-4 shadow-sm">
      <div className="border-b border-ink/10 pb-3">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-clay">Admin tree</p>
        <h2 className="mt-2 text-lg font-semibold text-ink">Management areas</h2>
      </div>
      <ul className="mt-4 space-y-2">
        {adminMenuItems.map((item) => {
          const active = isActivePath(pathname, item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={[
                  "block border px-4 py-3 transition",
                  active
                  ? "border-tide/45 bg-tide/10 shadow-sm"
                    : "border-ink/10 bg-paper/70 hover:border-tide/30 hover:bg-white",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-ink">{item.label}</div>
                    <div className="mt-1 text-xs leading-5 text-ink/60">{item.description}</div>
                  </div>
                  <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-current opacity-50" aria-hidden="true" />
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
