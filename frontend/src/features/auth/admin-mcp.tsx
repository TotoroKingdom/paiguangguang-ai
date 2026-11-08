"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  adminApproveMcpServer,
  adminCreateMcpServer,
  adminDisableMcpServer,
  adminDiscoverMcpTools,
  adminListMcpServers,
  type AdminMcpServer,
} from "./api";
import { useAuth } from "./provider";
import styles from "./auth.module.css";

const emptyForm = {
  name: "",
  description: "",
  endpointUrl: "https://",
  transport: "http" as "http" | "sse",
};

export function AdminMcpServers() {
  const { session } = useAuth();
  const [servers, setServers] = useState<AdminMcpServer[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const response = await adminListMcpServers();
      setServers(response.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "MCP Server 列表加载失败。");
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
        <h1>MCP Server 治理</h1>
        <p className={styles.lede}>需要统一管理员会话。</p>
        <Link className={styles.primary} href="/assistant/login?next=/assistant/admin/mcp">
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

  return (
    <div className={`${styles.card} ${styles.wide}`}>
      <h1>MCP Server 治理</h1>
      <p className={styles.lede}>
        平台登记并批准远程 MCP Server；用户只能在批准列表内建立个人连接。地址校验会拒绝内网与保留地址。
      </p>
      {error && <div className={styles.alert}>{error}</div>}
      {notice && <div className={styles.info}>{notice}</div>}
      <form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          void run(
            () => adminCreateMcpServer(form),
            `MCP Server“${form.name}”已登记并批准。`,
          ).then(() => setForm(emptyForm));
        }}
      >
        <label className={styles.field}>
          服务名称
          <input
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
            maxLength={120}
            required
          />
        </label>
        <label className={styles.field}>
          说明
          <input
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
            maxLength={1000}
          />
        </label>
        <label className={styles.field}>
          HTTPS 地址
          <input
            type="url"
            value={form.endpointUrl}
            onChange={(event) => setForm({ ...form, endpointUrl: event.target.value })}
            maxLength={512}
            required
          />
        </label>
        <label className={styles.field}>
          传输
          <select
            value={form.transport}
            onChange={(event) =>
              setForm({ ...form, transport: event.target.value as "http" | "sse" })
            }
          >
            <option value="http">HTTP JSON-RPC</option>
            <option value="sse">SSE</option>
          </select>
        </label>
        <div className={styles.actions}>
          <button className={styles.primary} disabled={busy}>
            登记并批准
          </button>
        </div>
      </form>

      <div className={styles.section}>
        <h2>已登记服务</h2>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>名称</th>
              <th>状态</th>
              <th>工具</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {servers.map((server) => (
              <tr key={server.id}>
                <td>
                  <strong>{server.name}</strong>
                  <div className={styles.muted}>{server.description || server.transport}</div>
                </td>
                <td>
                  <span className={styles.badge}>{server.status}</span>
                </td>
                <td>{server.tools.length}</td>
                <td>
                  <div className={styles.rowActions}>
                    <button
                      className={styles.secondary}
                      disabled={busy}
                      onClick={() =>
                        void run(
                          () => adminDiscoverMcpTools(server.id),
                          `已完成“${server.name}”工具发现。`,
                        )
                      }
                    >
                      发现工具
                    </button>
                    {server.status !== "approved" ? (
                      <button
                        className={styles.primary}
                        disabled={busy}
                        onClick={() =>
                          void run(
                            () => adminApproveMcpServer(server.id, "管理员批准"),
                            `已批准“${server.name}”。`,
                          )
                        }
                      >
                        批准
                      </button>
                    ) : (
                      <button
                        className={styles.danger}
                        disabled={busy}
                        onClick={() =>
                          void run(
                            () => adminDisableMcpServer(server.id, "管理员停用"),
                            `已停用“${server.name}”。`,
                          )
                        }
                      >
                        停用
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {!servers.length && (
              <tr>
                <td colSpan={4}>尚未登记 MCP Server。</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
