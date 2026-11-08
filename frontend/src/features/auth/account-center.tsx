"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { changePassword, claimLegacyConversations, rotateRecovery } from "./api";
import { useAuth } from "./provider";
import styles from "./auth.module.css";
import { getRunQuota, type RunQuota } from "@/features/assistant/personal-api";

export function AccountCenter() {
  const { session, status, logout, refresh } = useAuth();
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [quota, setQuota] = useState<RunQuota | null>(null);

  useEffect(() => {
    if (!session || session.user.status !== "ACTIVE") return;
    let active = true;
    void getRunQuota()
      .then((value) => {
        if (active) setQuota(value);
      })
      .catch(() => {
        if (active) setQuota(null);
      });
    return () => {
      active = false;
    };
  }, [session]);

  if (status === "loading") return <div className={styles.card}>正在加载个人中心…</div>;
  if (!session) {
    return (
      <div className={styles.card}>
        <h1>个人中心</h1>
        <p className={styles.lede}>登录后可查看账号状态、修改密码并认领旧匿名会话。</p>
        <Link className={styles.primary} href="/assistant/login?next=/assistant/me">
          前往登录
        </Link>
      </div>
    );
  }

  const active = session.user.status === "ACTIVE" && session.session.scope === "FULL";

  const submitPassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await changePassword({
        currentPassword,
        newPassword,
        newPasswordConfirm,
      });
      setRecoveryCode(result.recovery.code);
      setCurrentPassword("");
      setNewPassword("");
      setNewPasswordConfirm("");
      setNotice("密码已更新，其他会话已撤销。请保存新的恢复码。");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "密码修改失败。");
    } finally {
      setBusy(false);
    }
  };

  const rotate = async () => {
    if (!currentPassword) {
      setError("请先填写当前密码。");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await rotateRecovery(currentPassword);
      setRecoveryCode(result.recovery.code);
      setNotice("恢复码已轮换，旧恢复码立即失效。");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "恢复码轮换失败。");
    } finally {
      setBusy(false);
    }
  };

  const claim = async () => {
    setBusy(true);
    setError("");
    try {
      const result = await claimLegacyConversations([]);
      setNotice(`已认领 ${result.claimed} 条匿名会话。`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "匿名会话认领失败。");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`${styles.card} ${styles.wide}`}>
      <h1>个人中心</h1>
      <p className={styles.lede}>账号、状态与安全设置以服务端返回为准。</p>
      <dl className={styles.meta}>
        <div>
          <dt>数字账号</dt>
          <dd>{session.user.accountNumber}</dd>
        </div>
        <div>
          <dt>昵称</dt>
          <dd>{session.user.nickname || "未设置"}</dd>
        </div>
        <div>
          <dt>角色</dt>
          <dd>{session.user.role}</dd>
        </div>
        <div>
          <dt>状态</dt>
          <dd>{session.user.status}</dd>
        </div>
        <div>
          <dt>今日 Run 配额</dt>
          <dd>{quota ? `${quota.used} / ${quota.limit}` : "—"}</dd>
        </div>
      </dl>
      {!active && (
        <div className={styles.alert}>

          当前账号不是 ACTIVE 全功能会话，聊天与个人资源写入会被服务端拒绝。
          <Link href="/assistant/pending">查看审核状态</Link>
        </div>
      )}
      {error && <div className={styles.alert}>{error}</div>}
      {notice && <div className={styles.info}>{notice}</div>}
      {recoveryCode && (
        <code className={styles.code} data-testid="rotated-recovery-code">
          {recoveryCode}
        </code>
      )}

      <section className={styles.section}>
        <h2>修改密码</h2>
        <form className={styles.form} onSubmit={submitPassword}>
          <label className={styles.field}>
            当前密码
            <input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <label className={styles.field}>
            新密码（至少 6 位）
            <input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              autoComplete="new-password"
              minLength={6}
              required
            />
          </label>
          <label className={styles.field}>
            确认新密码
            <input
              type="password"
              value={newPasswordConfirm}
              onChange={(event) => setNewPasswordConfirm(event.target.value)}
              autoComplete="new-password"
              minLength={6}
              required
            />
          </label>
          <div className={styles.actions}>
            <button className={styles.primary} disabled={busy}>
              更新密码
            </button>
            <button type="button" className={styles.secondary} disabled={busy} onClick={() => void rotate()}>
              轮换恢复码
            </button>
          </div>
        </form>
      </section>

      <section className={styles.section}>
        <h2>旧匿名会话</h2>
        <p className={styles.lede}>
          仅在你当前浏览器仍持有原始匿名签名时才可认领。系统不会自动把匿名历史归给登录账号。
        </p>
        <button className={styles.secondary} disabled={busy || !active} onClick={() => void claim()}>
          认领本浏览器匿名历史
        </button>
      </section>

      <div className={styles.links}>
        {session.user.role === "ADMIN" && <Link href="/assistant/admin/users">用户管理</Link>}
        <button
          type="button"
          className={styles.secondary}
          onClick={() => void refresh()}
        >
          刷新会话
        </button>
        <button
          type="button"
          className={styles.danger}
          onClick={() => void logout().then(() => router.replace("/assistant/login"))}
        >
          退出登录
        </button>
      </div>
    </div>
  );
}
