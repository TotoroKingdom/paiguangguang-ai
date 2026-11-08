"use client";

import { useEffect, useState } from "react";
import { AssistantDialog } from "./assistant-dialog";
import { AssistantIcon } from "./assistant-icon";
import {
  connectMcp,
  disconnectMcp,
  listMcpConnections,
  listMcpServers,
  type ServerMcp,
  type ServerMcpConnection,
} from "./personal-api";
import styles from "./catalog.module.css";

export function McpServerCatalog() {
  const [servers, setServers] = useState<ServerMcp[]>([]);
  const [connections, setConnections] = useState<ServerMcpConnection[]>([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<ServerMcp | null>(null);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const refresh = async () => {
    setBusy(true);
    setError("");
    try {
      const [serverList, connectionList] = await Promise.all([
        listMcpServers(),
        listMcpConnections(),
      ]);
      setServers(serverList);
      setConnections(connectionList);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "MCP 服务列表加载失败。");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const connectionFor = (server: ServerMcp) =>
    connections.find((item) => item.serverId === server.id);
  const visible = servers.filter((server) =>
    `${server.name} ${server.description}`
      .toLowerCase()
      .includes(query.trim().toLowerCase()),
  );

  return (
    <section className={styles.page}>
      <div className={styles.heading}>
        <div>
          <p className={styles.eyebrow}>平台批准 · 个人授权</p>
          <h1>连接器中心</h1>
          <p>
            普通用户只能连接平台已批准的 MCP Server。凭据由服务端加密保存，不会回显明文，也不能提交任意远程地址。
          </p>
        </div>
        <div className={styles.headingActions}>
          <button className={styles.outline} disabled={busy} onClick={() => void refresh()}>
            刷新
          </button>
        </div>
      </div>
      {notice && (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      <label className={styles.search}>
        <AssistantIcon name="search" size={20} />
        <span className={styles.srOnly}>搜索连接器</span>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜索已批准服务…"
        />
      </label>
      <div className={styles.filterRow}>
        <span>共 {visible.length} 个已批准服务</span>
      </div>
      {visible.length === 0 ? (
        <p className={styles.empty}>当前没有可连接的平台批准 MCP Server。</p>
      ) : (
        <div className={styles.grid}>
          {visible.map((server, index) => {
            const connection = connectionFor(server);
            return (
              <article className={styles.card} key={server.id}>
                <button className={styles.cardMain} onClick={() => setSelected(server)}>
                  <span className={`${styles.iconBox} ${styles[`tone${index % 4}`]}`}>
                    <AssistantIcon name="mcp" size={30} />
                  </span>
                  <span>
                    <strong>{server.name}</strong>
                    <span className={styles.description}>{server.description}</span>
                  </span>
                </button>
                <div className={styles.cardBottom}>
                  <span className={styles.badge}>
                    <span
                      aria-hidden="true"
                      className={`${styles.statusDot} ${connection ? styles.statusConnected : ""}`}
                    />
                    {connection ? "已授权" : "未连接"} · {server.tools.length} 个工具
                  </span>
                  <button className={styles.smallButton} onClick={() => setSelected(server)}>
                    {connection ? "管理授权" : "连接"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
      {selected && (
        <AssistantDialog
          title={selected.name}
          onClose={() => {
            setSelected(null);
            setToken("");
          }}
        >
          <p className={styles.dialogHint}>{selected.description}</p>
          <p className={styles.muted}>
            服务地址由平台管理员登记；用户端不提供任意 URL 配置。
          </p>
          {selected.tools.length > 0 && (
            <p>
              已发现工具：{selected.tools.map((tool) => tool.name ?? "未命名").join("、")}
            </p>
          )}
          {connectionFor(selected) ? (
            <div className={styles.dialogActions}>
              <button
                className={styles.danger}
                disabled={busy}
                onClick={() => {
                  const connection = connectionFor(selected);
                  if (!connection) return;
                  void (async () => {
                    try {
                      await disconnectMcp(connection.id);
                      await refresh();
                      setSelected(null);
                      setNotice("已撤销个人 MCP 授权。");
                    } catch (cause) {
                      setError(cause instanceof Error ? cause.message : "撤销授权失败。");
                    }
                  })();
                }}
              >
                撤销个人授权
              </button>
            </div>
          ) : (
            <div className={styles.form}>
              <label>
                个人访问 Token（可选）
                <input
                  type="password"
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                  autoComplete="off"
                  placeholder="只保存在服务端加密存储中"
                />
              </label>
              <p className={styles.muted}>MCP 工具调用尚未接入当前 Agent Runtime，连接记录先用于授权治理。</p>
              <div className={styles.dialogActions}>
                <button
                  className={styles.primary}
                  disabled={busy}
                  onClick={() => {
                    void (async () => {
                      setBusy(true);
											setError("");
                      try {
                        await connectMcp(selected.id, token);
                        await refresh();
                        setSelected(null);
                        setToken("");
                        setNotice("个人授权已保存。");
                      } catch (cause) {
                        setError(cause instanceof Error ? cause.message : "连接失败。");
                      } finally {
                        setBusy(false);
                      }
                    })();
                  }}
                >
                  保存个人授权
                </button>
              </div>
            </div>
          )}
        </AssistantDialog>
      )}
    </section>
  );
}
