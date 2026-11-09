"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/provider";
import styles from "@/features/auth/auth.module.css";

export default function PendingPage() {
  const { session, refresh, logout, status } = useAuth();
  const router = useRouter();
  if (status === "loading") return <div className={styles.card}>正在确认账号状态…</div>;
  if (!session) {
    return (
      <div className={styles.card}>
        <h1>需要登录</h1>
        <p className={styles.lede}>请先使用数字账号登录，再查看审核状态。</p>
        <Link className={styles.primary} href="/assistant/login">
          前往登录
        </Link>
      </div>
    );
  }
  const active = session.user.status === "ACTIVE" && session.session.scope === "FULL";
  return (
    <div className={styles.card}>
      <h1>{active ? "账号已激活" : "等待管理员审核"}</h1>
      <p className={styles.lede}>
        {active
          ? "你的账号已可正常使用聊天、能力和个人资源。"
          : "账号处于待审核、停用或拒绝状态时，只能查看状态和退出登录。"}
      </p>
      <dl className={styles.meta}>
        <div>
          <dt>数字账号</dt>
          <dd>{session.user.accountNumber}</dd>
        </div>
        <div>
          <dt>当前状态</dt>
          <dd>{session.user.status}</dd>
        </div>
        <div>
          <dt>角色</dt>
          <dd>{session.user.role}</dd>
        </div>
      </dl>
      <div className={styles.actions}>
        <button className={styles.secondary} onClick={() => void refresh()}>
          刷新状态
        </button>
        {active && (
          <button className={styles.primary} onClick={() => router.replace("/assistant")}>
            进入工作台
          </button>
        )}
        <button
          className={styles.danger}
          onClick={() => void logout().then(() => router.replace("/assistant/login"))}
        >
          退出登录
        </button>
      </div>
    </div>
  );
}
