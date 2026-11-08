"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/features/auth/provider";
import styles from "@/features/auth/auth.module.css";

export default function RegisterSuccessPage() {
  const { registration, clearRegistration } = useAuth();
  const [copied, setCopied] = useState("");

  useEffect(() => {
    return () => clearRegistration();
  }, [clearRegistration]);

  if (!registration) {
    return (
      <div className={styles.card}>
        <h1>恢复码已不可再次查看</h1>
        <p className={styles.lede}>
          恢复码只在注册成功时显示一次。如果你没有保存，请通过受控支持流程联系管理员，不要仅凭账号请求重置。
        </p>
        <div className={styles.links}>
          <Link href="/assistant/login">前往登录</Link>
          <Link href="/assistant/register">重新注册</Link>
        </div>
      </div>
    );
  }

  const copy = async (label: string, value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(`${label}已复制`);
    } catch {
      setCopied("复制失败，请手动选择文本。");
    }
  };

  return (
    <div className={styles.card}>
      <h1>账号已创建</h1>
      <p className={styles.lede}>请立即保存账号和恢复码。本页面关闭或刷新后，恢复码不会再次显示。</p>
      <dl className={styles.meta}>
        <div>
          <dt>数字账号</dt>
          <dd>{registration.user.accountNumber}</dd>
        </div>
        <div>
          <dt>状态</dt>
          <dd>待审核</dd>
        </div>
      </dl>
      {registration.recovery ? (
        <>
          <strong>一次性恢复码</strong>
          <code className={styles.code}>{registration.recovery.code}</code>
          <div className={styles.actions}>
            <button
              className={styles.secondary}
              onClick={() => copy("账号", registration.user.accountNumber)}
            >
              复制账号
            </button>
            <button
              className={styles.secondary}
              onClick={() => copy("恢复码", registration.recovery?.code ?? "")}
            >
              复制恢复码
            </button>
          </div>
        </>
      ) : (
        <div className={styles.alert}>本次响应未包含新的恢复码，请联系管理员走受控恢复流程。</div>
      )}
      {copied && <div className={styles.info}>{copied}</div>}
      <div className={styles.info} style={{ marginTop: 18 }}>
        恢复码只保存在服务端摘要中，管理员也无法查看明文。
      </div>
      <div className={styles.links}>
        <Link href="/assistant/login">前往登录</Link>
      </div>
    </div>
  );
}
