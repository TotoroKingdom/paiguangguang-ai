"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/features/auth/provider";
import styles from "@/features/auth/auth.module.css";

export default function RegisterPage() {
  const { register, notice } = useAuth();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [nickname, setNickname] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (password.length < 6) {
      setError("密码至少需要 6 位。");
      return;
    }
    if (password !== passwordConfirm) {
      setError("两次输入的密码不一致。");
      return;
    }
    setBusy(true);
    const result = await register({ password, passwordConfirm, nickname });
    setBusy(false);
    if (result) router.push("/assistant/register/success");
  };

  return (
    <div className={styles.card}>
      <h1>注册数字账号</h1>
      <p className={styles.lede}>
        账号由服务器按注册顺序自动分配，从 100 开始递增。注册后为待审核状态，管理员激活后方可使用正式服务。
      </p>
      {(error || notice) && <div className={styles.alert}>{error || notice}</div>}
      <form className={styles.form} onSubmit={submit}>
        <label className={styles.field}>
          密码（至少 6 位）
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            minLength={6}
            maxLength={128}
            required
          />
        </label>
        <label className={styles.field}>
          确认密码
          <input
            type="password"
            value={passwordConfirm}
            onChange={(event) => setPasswordConfirm(event.target.value)}
            autoComplete="new-password"
            minLength={6}
            maxLength={128}
            required
          />
        </label>
        <label className={styles.field}>
          昵称（可选）
          <input
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            maxLength={80}
            autoComplete="nickname"
          />
        </label>
        <div className={styles.actions}>
          <button className={styles.primary} disabled={busy}>
            {busy ? "正在注册…" : "创建账号"}
          </button>
          <Link className={styles.secondary} href="/assistant/login">
            已有账号
          </Link>
        </div>
      </form>
    </div>
  );
}
