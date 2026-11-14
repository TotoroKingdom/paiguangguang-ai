"use client";

import { useEffect, useState } from "react";
import {
  listAuditEvents,
  listRuns,
  type AuditItem,
  type RunItem,
} from "./api";
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

export function AdminRuns() {
  const [tab, setTab] = useState<"runs" | "audit">("runs");
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [runTotal, setRunTotal] = useState(0);
  const [runCursor, setRunCursor] = useState<string | null>(null);
  const [audits, setAudits] = useState<AuditItem[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditCursor, setAuditCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    const request = tab === "runs" ? listRuns() : listAuditEvents();
    void request
      .then((data) => {
        if (!active) return;
        if (tab === "runs") {
          setRuns(data.items as RunItem[]);
          setRunTotal(data.total);
          setRunCursor(data.nextCursor);
        } else {
          setAudits(data.items as AuditItem[]);
          setAuditTotal(data.total);
          setAuditCursor(data.nextCursor);
        }
        setError("");
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "运行记录加载失败。");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [tab]);

  const loadMore = async () => {
    setLoadingMore(true);
    setError("");
    try {
      if (tab === "runs" && runCursor) {
        const data = await listRuns(runCursor);
        setRuns((current) => [...current, ...data.items]);
        setRunCursor(data.nextCursor);
        setRunTotal(data.total);
      } else if (tab === "audit" && auditCursor) {
        const data = await listAuditEvents(auditCursor);
        setAudits((current) => [...current, ...data.items]);
        setAuditCursor(data.nextCursor);
        setAuditTotal(data.total);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "加载更多记录失败。");
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <div className="admin-page">
      <AdminPageHeader
        eyebrow="OBSERVABILITY / 治理记录"
        title="运行与审计记录"
        description="能力调用准入和所有管理写操作都记录在服务端。演示执行会明确标记，不会伪装为真实工具结果。"
      />
      <div className="admin-tabs" role="tablist" aria-label="记录类型">
        <button
          role="tab"
          aria-selected={tab === "runs"}
          className={tab === "runs" ? "admin-tab admin-tab--active" : "admin-tab"}
          onClick={() => setTab("runs")}
        >
          能力调用
          <span>{runTotal}</span>
        </button>
        <button
          role="tab"
          aria-selected={tab === "audit"}
          className={tab === "audit" ? "admin-tab admin-tab--active" : "admin-tab"}
          onClick={() => setTab("audit")}
        >
          管理审计
          <span>{auditTotal}</span>
        </button>
      </div>
      {error && <InlineError>{error}</InlineError>}
      {loading ? (
        <LoadingBlock label={tab === "runs" ? "正在读取运行记录…" : "正在读取审计事件…"} />
      ) : tab === "runs" ? (
        runs.length === 0 ? (
          <EmptyState
            title="暂无能力调用记录"
            description="普通用户选择能力发送消息后，这里会记录真实的服务端准入结果。"
          />
        ) : (
          <>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>能力</th>
                    <th>类型</th>
                    <th>版本</th>
                    <th>执行模式</th>
                    <th>状态</th>
                    <th>会话 ID</th>
                    <th>时间</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id}>
                      <td>
                        <strong>{run.capabilityName}</strong>
                      </td>
                      <td>{run.kind ? kindLabels[run.kind] : "已删除能力"}</td>
                      <td>v{run.version}</td>
                      <td>
                        <span className="admin-mode">
                          {run.mode === "demo" ? "演示" : "模拟"}
                        </span>
                      </td>
                      <td>
                        <span className="admin-status admin-status--published">
                          {statusLabel(run.status)}
                        </span>
                      </td>
                      <td>
                        <code className="admin-id">{run.conversationId || "—"}</code>
                      </td>
                      <td>{formatDate(run.createdAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {runCursor && (
              <button
                className="admin-secondary-button admin-load-more"
                onClick={() => void loadMore()}
                disabled={loadingMore}
              >
                {loadingMore ? "正在加载…" : "加载更多"}
              </button>
            )}
          </>
        )
      ) : audits.length === 0 ? (
        <EmptyState
          title="暂无审计事件"
          description="管理员登录、保存草稿、发布与停用操作会自动写入审计记录。"
        />
      ) : (
        <>
          <div className="admin-audit-table">
            {audits.map((event) => (
              <article key={event.id}>
                <span className={`admin-audit-icon admin-audit-icon--${event.actorType}`}>
                  {event.actorType === "admin" ? "A" : "S"}
                </span>
                <div>
                  <strong>{statusLabel(event.action)}</strong>
                  <p>{auditTarget(event)}</p>
                </div>
                <code>{event.actorId || "system"}</code>
                <time>{formatDate(event.createdAt)}</time>
              </article>
            ))}
          </div>
          {auditCursor && (
            <button
              className="admin-secondary-button admin-load-more"
              onClick={() => void loadMore()}
              disabled={loadingMore}
            >
              {loadingMore ? "正在加载…" : "加载更多"}
            </button>
          )}
        </>
      )}
    </div>
  );
}
