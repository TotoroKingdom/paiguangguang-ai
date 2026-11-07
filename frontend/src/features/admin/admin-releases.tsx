"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { CapabilityKind } from "@/features/assistant/types";
import { listReleases, type ReleaseItem } from "./api";
import {
  AdminPageHeader,
  EmptyState,
  InlineError,
  LoadingBlock,
  StatusBadge,
  formatDate,
  kindLabels,
  kindRoutes,
} from "./admin-ui";

const kinds: (CapabilityKind | "")[] = ["", "tool", "skill", "mcp", "agent"];

export function AdminReleases() {
  const [kind, setKind] = useState<CapabilityKind | "">("");
  const [items, setItems] = useState<ReleaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    void listReleases(kind || undefined)
      .then((data) => {
        if (!active) return;
        setItems(data);
        setError("");
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "发布记录加载失败。");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [kind]);

  return (
    <div className="admin-page">
      <AdminPageHeader
        eyebrow="RELEASES / 发布中心"
        title="版本发布记录"
        description="所有发布与退役版本均来自服务端快照。新发布会让旧版本退役，已发布快照本身不会被修改。"
      />
      <section className="admin-toolbar">
        <div className="admin-filter-row">
          {kinds.map((item) => (
            <button
              key={item || "all"}
              className={kind === item ? "admin-chip admin-chip--active" : "admin-chip"}
              aria-pressed={kind === item}
              onClick={() => setKind(item)}
            >
              {item ? kindLabels[item] : "全部类型"}
            </button>
          ))}
        </div>
        <span className="admin-result-count">共 {items.length} 个版本</span>
      </section>
      {error && <InlineError>{error}</InlineError>}
      {loading ? (
        <LoadingBlock label="正在读取发布记录…" />
      ) : items.length === 0 ? (
        <EmptyState
          title="还没有发布版本"
          description="在能力详情页保存草稿并发布后，版本会出现在这里。"
          action={
            <Link className="admin-secondary-button" href="/assistant/admin/tools">
              前往工具管理
            </Link>
          }
        />
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>能力</th>
                <th>版本</th>
                <th>状态</th>
                <th>发布人</th>
                <th>发布时间</th>
                <th>退役时间</th>
                <th aria-label="操作" />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.versionId}>
                  <td>
                    <div className="admin-release-name">
                      <span className={`admin-kind-dot admin-kind-dot--${item.kind}`} />
                      <div>
                        <strong>{item.capabilityName}</strong>
                        <small>{kindLabels[item.kind]}</small>
                      </div>
                    </div>
                  </td>
                  <td>
                    <strong className="admin-version">v{item.version}</strong>
                  </td>
                  <td>
                    <StatusBadge status={item.status} />
                  </td>
                  <td>
                    <code>{item.publishedBy || "—"}</code>
                  </td>
                  <td>{formatDate(item.publishedAt)}</td>
                  <td>{formatDate(item.retiredAt)}</td>
                  <td>
                    <Link
                      className="admin-row-link"
                      href={`/assistant/admin/capabilities/${item.capabilityId}`}
                    >
                      查看
                      <span aria-hidden="true">→</span>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="admin-page-footnote">
        发布中心当前只展示版本与状态；回滚到旧版本尚未实现，需要新建草稿后重新发布。
        能力类型快捷入口：
        {(["tool", "skill", "mcp", "agent"] as CapabilityKind[]).map((item) => (
          <Link key={item} href={kindRoutes[item]}>
            {kindLabels[item]}
          </Link>
        ))}
      </p>
    </div>
  );
}
