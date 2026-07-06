"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type AdminMenuItem = {
  href: string;
  label: string;
  description: string;
};

const adminMenuItems: AdminMenuItem[] = [
  { href: "/admin/documents", label: "文档", description: "文档生命周期与入库" },
  { href: "/admin/users", label: "用户", description: "账号访问与工作区成员" },
  { href: "/admin/roles", label: "角色", description: "角色集合与权限分配" },
  { href: "/admin/permissions", label: "权限", description: "权限目录" },
  { href: "/admin/workspaces", label: "工作区", description: "工作区注册与默认标记" },
];

function isActivePath(pathname: string | null, href: string) {
  return pathname === href || pathname?.startsWith(`${href}/`);
}

export function AdminMenuTree() {
  const pathname = usePathname();

  return (
    <nav aria-label="管理后台分区" className="border border-ink/10 bg-white/72 p-4 shadow-sm">
      <div className="border-b border-ink/10 pb-3">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-clay">后台导航</p>
        <h2 className="mt-2 text-lg font-semibold text-ink">管理分区</h2>
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
