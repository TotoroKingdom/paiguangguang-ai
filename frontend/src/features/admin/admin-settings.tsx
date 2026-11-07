"use client";

import { useEffect, useState } from "react";
import { getAdminSettings, type AdminSettings } from "./api";
import { AdminPageHeader, InlineError, LoadingBlock, formatDate } from "./admin-ui";

export function AdminSettingsPage() {
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void getAdminSettings()
      .then((data) => {
        if (active) setSettings(data);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "系统设置加载失败。");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="admin-page">
      <AdminPageHeader
        eyebrow="SETTINGS / 系统设置"
        title="运行环境与安全策略"
        description="这里展示服务端实际生效的只读配置。尚未实现的配置项不会被包装成可点击但无响应的开关。"
      />
      {error && <InlineError>{error}</InlineError>}
      {!settings ? (
        <LoadingBlock label="正在读取服务端配置…" />
      ) : (
        <section className="admin-settings-grid">
          <article className="admin-panel">
            <p className="admin-eyebrow">IDENTITY</p>
            <h2>管理员会话</h2>
            <dl className="admin-definition-list">
              <div>
                <dt>会话有效期</dt>
                <dd>{settings.adminSessionMinutes} 分钟</dd>
              </div>
              <div>
                <dt>Cookie Secure</dt>
                <dd>{settings.secureAdminCookie ? "已启用" : "开发环境未启用"}</dd>
              </div>
              <div>
                <dt>登录限流</dt>
                <dd>
                  {settings.loginRateLimit.attempts} 次 /{" "}
                  {Math.round(settings.loginRateLimit.windowSeconds / 60)} 分钟
                </dd>
              </div>
              <div>
                <dt>锁定时间</dt>
                <dd>{Math.round(settings.loginRateLimit.lockSeconds / 60)} 分钟</dd>
              </div>
            </dl>
          </article>
          <article className="admin-panel">
            <p className="admin-eyebrow">ENVIRONMENT</p>
            <h2>应用环境</h2>
            <dl className="admin-definition-list">
              <div>
                <dt>环境</dt>
                <dd>{settings.environment}</dd>
              </div>
              <div>
                <dt>数据库</dt>
                <dd>
                  <code>{settings.database}</code>
                </dd>
              </div>
              <div>
                <dt>执行模式</dt>
                <dd>{settings.executionMode}</dd>
              </div>
              <div>
                <dt>当前时间</dt>
                <dd>{formatDate(new Date().toISOString())}</dd>
              </div>
            </dl>
          </article>
          <article className="admin-panel admin-panel--wide">
            <p className="admin-eyebrow">BOUNDARIES</p>
            <h2>当前能力边界</h2>
            <ul className="admin-note-list">
              {settings.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </article>
          <article className="admin-panel admin-panel--wide">
            <p className="admin-eyebrow">ORIGINS</p>
            <h2>允许的浏览器来源</h2>
            <div className="admin-origin-list">
              {settings.allowedOrigins.map((origin) => (
                <code key={origin}>{origin}</code>
              ))}
            </div>
            <p className="admin-form-note">
              管理写操作还需要当前管理会话签发的 CSRF Token。跨来源请求由服务端直接拒绝。
            </p>
          </article>
        </section>
      )}
    </div>
  );
}
