"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  adminListUsers,
  moderateUser,
  setUserRole,
  type AccountRole,
  type AccountStatus,
  type AccountUser,
} from "./api";
import { useAuth } from "./provider";
import styles from "./auth.module.css";

export function AdminUsers() {
  const { session } = useAuth();
  const [users, setUsers] = useState<AccountUser[]>([]);
  const [status, setStatus] = useState<AccountStatus | "">("PENDING");
  const [role, setRole] = useState<AccountRole | "">("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const result = await adminListUsers({
        status: status || undefined,
        role: role || undefined,
        q: query,
      });
      setUsers(result.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法加载用户列表。");
    } finally {
      setBusy(false);
    }
  }, [query, role, status]);

  useEffect(() => {
    if (session?.user.role === "ADMIN") void load();
  }, [load, session?.user.role]);

  if (!session || session.user.role !== "ADMIN") {
    return (
      <div className={styles.card}>
        <h1>用户管理</h1>
        <p className={styles.lede}>需要统一管理员会话。请使用管理员数字账号登录。</p>
        <Link className={styles.primary} href="/assistant/login?next=/assistant/admin/users">
          管理员登录
        </Link>
      </div>
    );
  }

  const act = async (user: AccountUser, action: "activate" | "reject" | "disable" | "restore") => {
    const reason =
      action === "activate" ? "审核通过" : window.prompt("请输入原因（必填）", "")?.trim() ?? "";
    if (action !== "activate" && !reason) return;
    setBusy(true);
    setError("");
    try {
      await moderateUser(user.id, action, user.version, reason);
      setNotice(`已对账号 ${user.accountNumber} 执行 ${action}。`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "操作失败。");
    } finally {
      setBusy(false);
    }
  };

  const changeRole = async (user: AccountUser, nextRole: AccountRole) => {
    const reason = window.prompt("请输入角色变更原因（必填）", "")?.trim() ?? "";
    if (!reason) return;
    setBusy(true);
    setError("");
    try {
      await setUserRole(user.id, nextRole, user.version, reason);
      setNotice(`账号 ${user.accountNumber} 的角色已更新。`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "角色变更失败。");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`${styles.card} ${styles.wide}`}>
      <h1>用户管理</h1>
      <p className={styles.lede}>激活、拒绝、停用与角色变更均写入审计；最后一名有效管理员受保护。</p>
      {error && <div className={styles.alert}>{error}</div>}
      {notice && <div className={styles.info}>{notice}</div>}
      <div className={styles.filters}>
        <label className={styles.field}>
          状态
          <select value={status} onChange={(event) => setStatus(event.target.value as AccountStatus | "")}>
            <option value="">全部</option>
            <option value="PENDING">PENDING</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="DISABLED">DISABLED</option>
            <option value="REJECTED">REJECTED</option>
          </select>
        </label>
        <label className={styles.field}>
          角色
          <select value={role} onChange={(event) => setRole(event.target.value as AccountRole | "")}>
            <option value="">全部</option>
            <option value="USER">USER</option>
            <option value="CREATOR">CREATOR</option>
            <option value="ADMIN">ADMIN</option>
          </select>
        </label>
        <label className={styles.field}>
          搜索
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="账号或昵称" />
        </label>
        <button className={styles.secondary} disabled={busy} onClick={() => void load()}>
          查询
        </button>
      </div>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>账号</th>
            <th>昵称</th>
            <th>角色</th>
            <th>状态</th>
            <th>版本</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>{user.accountNumber}</td>
              <td>{user.nickname || "—"}</td>
              <td>
                <span className={styles.badge}>{user.role}</span>
              </td>
              <td>
                <span className={styles.badge}>{user.status}</span>
              </td>
              <td>{user.version}</td>
              <td>
                <div className={styles.rowActions}>
                  {user.status === "PENDING" && (
                    <>
                      <button className={styles.primary} onClick={() => void act(user, "activate")}>
                        激活
                      </button>
                      <button className={styles.danger} onClick={() => void act(user, "reject")}>
                        拒绝
                      </button>
                    </>
                  )}
                  {user.status === "ACTIVE" && (
                    <button className={styles.danger} onClick={() => void act(user, "disable")}>
                      停用
                    </button>
                  )}
                  {user.status === "DISABLED" && (
                    <button className={styles.secondary} onClick={() => void act(user, "restore")}>
                      恢复
                    </button>
                  )}
                  <select
                    value={user.role}
                    onChange={(event) => void changeRole(user, event.target.value as AccountRole)}
                  >
                    <option value="USER">USER</option>
                    <option value="CREATOR">CREATOR</option>
                    <option value="ADMIN">ADMIN</option>
                  </select>
                </div>
              </td>
            </tr>
          ))}
          {!users.length && (
            <tr>
              <td colSpan={6}>没有符合条件的用户。</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
