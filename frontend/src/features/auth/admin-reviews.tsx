"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  governanceApproveCapability,
  governanceListCapabilities,
  governanceRejectCapability,
  governanceReleaseCapability,
  type GovernanceCapability,
} from "./api";
import { useAuth } from "./provider";
import styles from "./auth.module.css";

export function AdminReviews() {
  const { session } = useAuth();
  const [items, setItems] = useState<GovernanceCapability[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      setItems(await governanceListCapabilities());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "审核列表加载失败。");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (session?.user.role === "ADMIN") void load();
  }, [load, session?.user.role]);

  if (!session || session.user.role !== "ADMIN") {
    return (
      <div className={styles.card}>
        <h1>审核与发布</h1>
        <p className={styles.lede}>需要统一管理员会话。</p>
        <Link className={styles.primary} href="/assistant/login?next=/assistant/admin/reviews">
          管理员登录
        </Link>
      </div>
    );
  }

  const run = async (task: () => Promise<unknown>, message: string) => {
    setBusy(true);
    setError("");
    try {
      await task();
      await load();
      setNotice(message);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "操作失败。");
    } finally {
      setBusy(false);
    }
  };

  const submitted = items.filter((item) => item.reviewStatus === "submitted");
  const approved = items.filter(
    (item) => item.reviewStatus === "approved" && item.hasDraft,
  );

  return (
    <div className={`${styles.card} ${styles.wide}`}>
      <h1>审核与发布</h1>
      <p className={styles.lede}>
        审核 Creator 提交的版本快照；批准后仍需单独发布。发布、停用与审计在同一事务内完成。
      </p>
      {error && <div className={styles.alert}>{error}</div>}
      {notice && <div className={styles.info}>{notice}</div>}

      <div className={styles.section}>
        <h2>待审核（{submitted.length}）</h2>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>测试</th>
              <th>说明</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {submitted.map((item) => (
              <tr key={item.id}>
                <td>{item.name}</td>
                <td>{item.kind}</td>
                <td>
                  <span className={styles.badge}>{item.testStatus}</span>
                </td>
                <td>{item.description}</td>
                <td>
                  <div className={styles.rowActions}>
                    <button
                      className={styles.primary}
                      disabled={busy}
                      onClick={() => {
                        const reason = window.prompt("批准理由", "通过审核")?.trim() ?? "";
                        if (!reason) return;
                        void run(
                          () => governanceApproveCapability(item.id, reason),
                          `“${item.name}”已批准，等待发布。`,
                        );
                      }}
                    >
                      批准
                    </button>
                    <button
                      className={styles.danger}
                      disabled={busy}
                      onClick={() => {
                        const reason = window.prompt("驳回理由", "")?.trim() ?? "";
                        if (!reason) return;
                        void run(
                          () => governanceRejectCapability(item.id, reason),
                          `“${item.name}”已驳回。`,
                        );
                      }}
                    >
                      驳回
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!submitted.length && (
              <tr>
                <td colSpan={5}>当前没有待审核能力。</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className={styles.section}>
        <h2>待发布（{approved.length}）</h2>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>当前版本</th>
              <th>草稿版本</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {approved.map((item) => (
              <tr key={item.id}>
                <td>{item.name}</td>
                <td>{item.kind}</td>
                <td>{item.publishedVersion ? `v${item.publishedVersion}` : "—"}</td>
                <td>{item.draftVersion ? `v${item.draftVersion}` : "—"}</td>
                <td>
                  <button
                    className={styles.primary}
                    disabled={busy}
                    onClick={() => {
                      const changelog = window.prompt("发布说明", "发布审核版本")?.trim() ?? "";
                      if (!changelog) return;
                      void run(
                        () => governanceReleaseCapability(item.id, changelog),
                        `“${item.name}”已发布。`,
                      );
                    }}
                  >
                    发布
                  </button>
                </td>
              </tr>
            ))}
            {!approved.length && (
              <tr>
                <td colSpan={5}>当前没有已批准待发布版本。</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
