"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useAuth } from "@/features/auth/provider";
import { safeReturnTo } from "@/features/auth/return-to";
import styles from "@/features/auth/auth.module.css";

function LoginForm() {
  const { login, notice, status } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [accountNumber, setAccountNumber] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    const session = await login(accountNumber, password);
    setBusy(false);
    if (!session) return;
    const safeNext = safeReturnTo(params.get("next"));
    if (session.user.status !== "ACTIVE" || session.session.scope !== "FULL") {
      router.replace("/assistant/pending");
      return;
    }
    router.replace(safeNext ?? "/assistant");
  };

  return (
    <div className={styles.card}>
      <h1>登录智能助手</h1>
      <p className={styles.lede}>使用管理员分配的数字账号。新账号需审核激活后才能使用正式服务。</p>
      {status === "authenticated" && <div className={styles.info}>当前浏览器已有登录会话。</div>}
      {(error || notice) && <div className={styles.alert}>{error || notice}</div>}
      <form className={styles.form} onSubmit={submit}>
        <label className={styles.field}>
          数字账号
          <input
            value={accountNumber}
            onChange={(event) => setAccountNumber(event.target.value)}
            inputMode="numeric"
            pattern="[1-9][0-9]*"
            autoComplete="username"
            required
          />
        </label>
        <label className={styles.field}>
          密码
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            minLength={6}
            required
          />
        </label>
        <div className={styles.actions}>
          <button className={styles.primary} disabled={busy}>
            {busy ? "正在登录…" : "登录"}
          </button>
          <Link className={styles.secondary} href="/assistant/register">
            注册新账号
          </Link>
        </div>
      </form>
      <div className={styles.links}>
        <Link href="/assistant">先以访客身份使用</Link>
        <Link href="/">返回网站</Link>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className={styles.card}>正在加载登录页…</div>}>
      <LoginForm />
    </Suspense>
  );
}
