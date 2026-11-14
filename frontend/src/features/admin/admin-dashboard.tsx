"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AssistantIcon } from "@/features/assistant/assistant-icon";
import { getOverview, type Overview } from "./api";
import {
  AdminPageHeader,
  EmptyState,
  InlineError,
  LoadingBlock,
  auditTarget,
  formatDate,
  kindLabels,
  statusLabel,
} from "./admin-ui";

const kindLink = {
  tool: "/assistant/admin/tools",
  skill: "/assistant/admin/skills",
  mcp: "/assistant/admin/mcp",
  agent: "/assistant/admin/agents",
} as const;

export function AdminDashboard() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void getOverview()
      .then((data) => {
        if (active) setOverview(data);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "总览加载失败。");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="admin-page">
      <AdminPageHeader
        eyebrow="OVERVIEW / 运行总览"
        title="能力治理，从这里开始"
        description="查看真实能力注册表、发布状态、用户调用记录与管理审计。当前运行时仅提供模拟执行，不会伪装真实调用。"
        actions={
          <Link className="admin-primary-button" href="/assistant/admin/tools">
            管理能力
            <AssistantIcon name="arrow" size={16} />
          </Link>
        }
      />
      {error && <InlineError>{error}</InlineError>}
      {!overview && !error ? (
        <LoadingBlock label="正在读取能力注册表…" />
      ) : overview ? (
        <>
          <section className="admin-stat-grid" aria-label="能力统计">
            {overview.capabilities.map((item) => (
              <Link className="admin-stat-card" href={kindLink[item.kind]} key={item.kind}>
                <span>
                  <AssistantIcon name={item.kind} size={22} />
                </span>
                <div>
                  <small>{kindLabels[item.kind]}</small>
                  <strong>{item.total}</strong>
                  <p>
                    {item.published} 已发布 · {item.draft} 草稿 · {item.disabled} 停用
                  </p>
                </div>
                <AssistantIcon name="arrow" size={16} />
              </Link>
            ))}
          </section>
          <section className="admin-split-grid">
            <div className="admin-panel">
              <div className="admin-panel-heading">
                <div>
                  <p className="admin-eyebrow">RUNS</p>
                  <h2>最近运行</h2>
                </div>
                <Link href="/assistant/admin/runs">全部记录</Link>
              </div>
              <p className="admin-panel-summary">
                共 {overview.totalRuns} 条能力调用记录，全部标注为演示或模拟执行。
              </p>
              {overview.recentRuns.length === 0 ? (
                <EmptyState
                  title="还没有运行记录"
                  description="普通用户选择能力发送消息后，服务端会记录真实的能力调用准入事件。"
                />
              ) : (
                <div className="admin-compact-list">
                  {overview.recentRuns.map((run) => (
                    <div key={run.id}>
                      <span className={`admin-kind-dot admin-kind-dot--${run.kind ?? "tool"}`} />
                      <div>
                        <strong>{run.capabilityName}</strong>
                        <small>
                          v{run.version} · {statusLabel(run.mode)} · {formatDate(run.createdAt)}
                        </small>
                      </div>
                      <span className="admin-status admin-status--published">
                        {statusLabel(run.status)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="admin-panel">
              <div className="admin-panel-heading">
                <div>
                  <p className="admin-eyebrow">AUDIT</p>
                  <h2>管理审计</h2>
                </div>
                <span>{overview.admin.username}</span>
              </div>
              {overview.recentAudit.length === 0 ? (
                <EmptyState
                  title="暂无审计事件"
                  description="登录、创建、保存、发布与停用操作会自动写入审计表。"
                />
              ) : (
                <ol className="admin-audit-list">
                  {overview.recentAudit.map((event) => (
                    <li key={event.id}>
                      <i />
                      <div>
                        <strong>{statusLabel(event.action)}</strong>
                        <p>{auditTarget(event)}</p>
                        <small>{formatDate(event.createdAt)}</small>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
