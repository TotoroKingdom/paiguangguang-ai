"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { AssistantIcon } from "@/features/assistant/assistant-icon";
import { useAdmin } from "./admin-provider";
import { LoadingBlock } from "./admin-ui";

const navigation = [
  { href: "/assistant/admin", name: "总览仪表盘", icon: "chart" },
  { href: "/assistant/admin/tools", name: "工具管理", icon: "tool" },
  { href: "/assistant/admin/skills", name: "技能管理", icon: "skill" },
  { href: "/assistant/admin/mcp", name: "MCP 连接管理", icon: "mcp" },
  { href: "/assistant/admin/agents", name: "智能体管理", icon: "agent" },
  { href: "/assistant/admin/releases", name: "发布中心", icon: "upload" },
  { href: "/assistant/admin/runs", name: "运行记录", icon: "list" },
  { href: "/assistant/admin/settings", name: "系统设置", icon: "settings" },
];

function pageTitle(pathname: string): string {
  if (pathname.startsWith("/assistant/admin/capabilities/")) return "能力详情";
  return (
    navigation
      .filter((item) => item.href !== "/assistant/admin")
      .find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))?.name ??
    "总览仪表盘"
  );
}

export function AdminFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status, user, notice, logout } = useAdmin();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isLogin = pathname === "/assistant/admin/login";

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (status === "loading") return;
    if (status === "anonymous" && !isLogin) {
      const next = encodeURIComponent(pathname);
      router.replace(`/assistant/admin/login?next=${next}`);
    }
    if (status === "authenticated" && isLogin) {
      router.replace("/assistant/admin");
    }
  }, [isLogin, pathname, router, status]);

  if (isLogin) return <>{children}</>;

  if (status === "loading") {
    return (
      <div className="admin-splash">
        <LoadingBlock label="正在校验管理员会话…" />
      </div>
    );
  }

  if (status !== "authenticated" || !user) {
    return (
      <div className="admin-splash">
        {notice ? <p role="alert">{notice}</p> : <LoadingBlock label="正在跳转登录…" />}
      </div>
    );
  }

  return (
    <div className="admin-root">
      {mobileOpen && (
        <button
          className="admin-backdrop"
          aria-label="关闭管理导航"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        className={`admin-sidebar${mobileOpen ? " admin-sidebar--open" : ""}`}
        aria-label="管理控制台导航"
      >
        <Link href="/assistant/admin" className="admin-brand">
          <span>
            <AssistantIcon name="spark" size={20} />
          </span>
          <div>
            <strong>能力控制台</strong>
            <small>ASSISTANT ADMIN</small>
          </div>
        </Link>
        <nav>
          {navigation.map((item) => {
            const active =
              item.href === "/assistant/admin"
                ? pathname === item.href
                : pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={active ? "admin-nav-link admin-nav-link--active" : "admin-nav-link"}
              >
                <AssistantIcon name={item.icon} size={19} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
        <div className="admin-sidebar-footer">
          <Link href="/assistant" className="admin-return-link">
            <AssistantIcon name="arrow" size={16} />
            返回用户工作台
          </Link>
          <div className="admin-account">
            <span className="admin-avatar">{user.username.slice(0, 1).toUpperCase()}</span>
            <div>
              <strong>{user.username}</strong>
              <small>{user.role === "admin" ? "管理员" : "只读成员"}</small>
            </div>
            <button
              type="button"
              aria-label="退出管理员登录"
              onClick={() => {
                void logout().then(() => router.replace("/assistant/admin/login"));
              }}
            >
              <AssistantIcon name="close" size={16} />
            </button>
          </div>
        </div>
      </aside>
      <div className="admin-main">
        <header className="admin-topbar">
          <button
            className="admin-mobile-toggle"
            aria-label="打开管理导航"
            onClick={() => setMobileOpen(true)}
          >
            <AssistantIcon name="menu" />
          </button>
          <div>
            <span>管理控制台</span>
            <strong>{pageTitle(pathname)}</strong>
          </div>
          <div className="admin-topbar-status">
            <i />
            服务端已连接
          </div>
        </header>
        <main className="admin-content">{children}</main>
      </div>
    </div>
  );
}
