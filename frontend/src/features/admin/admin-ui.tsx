import type { ReactNode } from "react";
import type { CapabilityKind } from "@/features/assistant/types";

export const kindLabels: Record<CapabilityKind, string> = {
  tool: "工具",
  skill: "技能",
  mcp: "MCP 连接",
  agent: "智能体",
};

export const kindRoutes: Record<CapabilityKind, string> = {
  tool: "/assistant/admin/tools",
  skill: "/assistant/admin/skills",
  mcp: "/assistant/admin/mcp",
  agent: "/assistant/admin/agents",
};

export function AdminPageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="admin-page-header">
      <div>
        <p className="admin-eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions && <div className="admin-page-actions">{actions}</div>}
    </header>
  );
}

export function StatusBadge({
  status,
}: {
  status: "draft" | "published" | "disabled" | "retired";
}) {
  const labels = {
    draft: "草稿",
    published: "已发布",
    disabled: "已停用",
    retired: "历史版本",
  } as const;
  return (
    <span className={`admin-status admin-status--${status}`}>{labels[status]}</span>
  );
}

export function LoadingBlock({ label = "正在加载…" }: { label?: string }) {
  return (
    <div className="admin-loading" role="status">
      <span />
      {label}
    </div>
  );
}

export function InlineError({ children }: { children: ReactNode }) {
  return (
    <p className="admin-alert admin-alert--error" role="alert">
      {children}
    </p>
  );
}

export function InlineNotice({ children }: { children: ReactNode }) {
  return (
    <p className="admin-alert admin-alert--success" role="status">
      {children}
    </p>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="admin-empty">
      <strong>{title}</strong>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: "草稿",
    published: "已发布",
    disabled: "已停用",
    retired: "历史版本",
    accepted: "已受理",
    demo: "演示执行",
    simulated: "模拟执行",
    "capability.created": "创建能力",
    "capability.draft.saved": "保存草稿",
    "capability.published": "发布版本",
    "capability.disabled": "停用能力",
    "admin.login": "管理员登录",
    "admin.logout": "管理员退出",
  };
  return labels[status] ?? status;
}

export function auditTarget(event: {
  action: string;
  resourceId: string;
  detail: Record<string, unknown>;
}): string {
  if (typeof event.detail.name === "string" && event.detail.name.trim()) {
    return event.detail.name;
  }
  if (event.action === "admin.login" || event.action === "admin.logout") {
    return "管理员会话";
  }
  return event.resourceId || "系统级事件";
}
