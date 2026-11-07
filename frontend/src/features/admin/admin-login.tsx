"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { AssistantIcon } from "@/features/assistant/assistant-icon";
import { useAdmin } from "./admin-provider";
import { InlineError } from "./admin-ui";

export function AdminLogin() {
  const router = useRouter();
  const { status, user, notice, login } = useAdmin();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status === "authenticated" && user) {
      router.replace("/assistant/admin");
    }
  }, [router, status, user]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!username.trim() || !password || busy) return;
    setBusy(true);
    const ok = await login(username, password);
    setBusy(false);
    if (!ok) return;
    const next = new URLSearchParams(window.location.search).get("next");
    router.replace(next?.startsWith("/assistant/admin") ? next : "/assistant/admin");
  };

  return (
    <main className="admin-login-page">
      <section className="admin-login-card" aria-label="管理员登录">
        <div className="admin-login-mark">
          <AssistantIcon name="spark" size={24} />
        </div>
        <p className="admin-eyebrow">PAIGUANGGUANG / CAPABILITY CONSOLE</p>
        <h1>管理控制台登录</h1>
        <p className="admin-login-copy">
          管理员身份与普通浏览器会话相互独立。登录会话由服务端校验，并使用
          HttpOnly Cookie 保存。
        </p>
        <form onSubmit={submit}>
          <label>
            管理员用户名
            <input
              aria-label="管理员用户名"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              maxLength={80}
              required
            />
          </label>
          <label>
            管理员密码
            <span className="admin-password-field">
              <input
                aria-label="管理员密码"
                type={visible ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                maxLength={256}
                required
              />
              <button
                type="button"
                onClick={() => setVisible((current) => !current)}
                aria-label={visible ? "隐藏密码" : "显示密码"}
              >
                {visible ? "隐藏" : "显示"}
              </button>
            </span>
          </label>
          {notice && <InlineError>{notice}</InlineError>}
          <button className="admin-primary-button" type="submit" disabled={busy}>
            {busy ? "正在验证…" : "安全登录"}
            <AssistantIcon name="arrow" size={17} />
          </button>
        </form>
        <div className="admin-login-footer">
          <span>连续失败会触发临时锁定</span>
          <Link href="/assistant">返回用户工作台</Link>
        </div>
      </section>
      <aside className="admin-login-aside">
        <span>ADMINISTRATION / V1</span>
        <h2>能力不是按钮，而是可发布、可审计的服务端资源。</h2>
        <ul>
          <li>草稿与已发布版本隔离，发布快照不可被覆盖。</li>
          <li>用户目录只读取已发布能力，停用后立即退出可用列表。</li>
          <li>所有管理写操作校验管理员会话、Origin 与 CSRF Token。</li>
        </ul>
      </aside>
    </main>
  );
}
