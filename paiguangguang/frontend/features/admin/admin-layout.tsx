"use client";

import type { ReactNode } from "react";

import { AdminMenuTree } from "@/features/admin/admin-menu-tree";

export function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="space-y-6">
      <header className="border border-ink/10 bg-gradient-to-r from-paper via-white to-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-clay">管理后台</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">后台管理</h1>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-ink/70">
          文档、用户、角色、权限与工作区的路由式管理页面。
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <AdminMenuTree />
        <main className="min-w-0 space-y-6">{children}</main>
      </div>
    </div>
  );
}
