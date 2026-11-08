"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  creatorCreateCapability,
  creatorListCapabilities,
  creatorRunSummary,
  creatorSubmitCapability,
  creatorTestCapability,
  type CreatorCapabilityInput,
  type GovernanceCapability,
  type CreatorRunSummary,
} from "./api";
import { useAuth } from "./provider";
import styles from "./auth.module.css";

const defaultConfig: Record<CreatorCapabilityInput["kind"], Record<string, unknown>> = {
  tool: { executor: "system", tool: "system.current_time" },
  skill: {},
  agent: {},
};

export function CreatorCenter() {
  const { session } = useAuth();
  const [items, setItems] = useState<GovernanceCapability[]>([]);
  const [summary, setSummary] = useState<CreatorRunSummary | null>(null);
  const [kind, setKind] = useState<CreatorCapabilityInput["kind"]>("tool");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");
  const [configText, setConfigText] = useState(
    JSON.stringify(defaultConfig.tool, null, 2),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const [capabilities, runSummary] = await Promise.all([
        creatorListCapabilities(),
        creatorRunSummary(),
      ]);
      setItems(capabilities);
      setSummary(runSummary);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "创作列表加载失败。");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (session?.user.role === "CREATOR" || session?.user.role === "ADMIN") void load();
  }, [load, session?.user.role]);

  if (
    !session ||
    (session.user.role !== "CREATOR" && session.user.role !== "ADMIN")
  ) {
    return (
      <div className={styles.card}>
        <h1>创作中心</h1>
        <p className={styles.lede}>需要 Creator 或 Admin 角色。</p>
        <Link className={styles.primary} href="/assistant/login?next=/assistant/creator">
          登录
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

  const createDraft = async (event: React.FormEvent) => {
    event.preventDefault();
    let config: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(configText || "{}");
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error();
      config = parsed as Record<string, unknown>;
    } catch {
      setError("执行配置必须是 JSON 对象。");
      return;
    }
    await run(
      () =>
        creatorCreateCapability({
          kind,
          name: name.trim(),
          description: description.trim(),
          category: kind === "tool" ? "工具" : "技能",
          icon: kind,
          steps: [],
          tools: [],
          content: kind === "skill" ? content : null,
          config,
          changelog: "Creator 创建草稿",
        }),
      "草稿已创建。请先测试，再提交审核。",
    );
    setName("");
    setDescription("");
    setContent("");
  };

  return (
    <div className={`${styles.card} ${styles.wide}`}>
      <h1>创作中心</h1>
      <p className={styles.lede}>
        Creator 创建草稿、执行就绪测试并提交审核；发布权仍属于 Admin。
      </p>
      {error && <div className={styles.alert}>{error}</div>}
      {notice && <div className={styles.info}>{notice}</div>}

      <form className={styles.form} onSubmit={createDraft}>
        <div className={styles.filters}>
          <label className={styles.field}>
            类型
            <select
              value={kind}
              onChange={(event) => {
                const next = event.target.value as CreatorCapabilityInput["kind"];
                setKind(next);
                setConfigText(JSON.stringify(defaultConfig[next], null, 2));
              }}
            >
              <option value="tool">只读 Tool</option>
              <option value="skill">Skill</option>
            </select>
          </label>
          <label className={styles.field}>
            名称
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={120}
              required
            />
          </label>
        </div>
        <label className={styles.field}>
          说明
          <input
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            maxLength={2000}
          />
        </label>
        {kind === "skill" && (
          <label className={styles.field}>
            Markdown 正文
            <textarea
              value={content}
              onChange={(event) => setContent(event.target.value)}
              rows={6}
              maxLength={100000}
            />
          </label>
        )}
        <label className={styles.field}>
          执行配置 JSON
          <textarea
            value={configText}
            onChange={(event) => setConfigText(event.target.value)}
            rows={5}
          />
        </label>
        <div className={styles.actions}>
          <button className={styles.primary} disabled={busy}>
            创建草稿
          </button>
        </div>
      </form>

      <div className={styles.section}>
        <h2>我的能力草稿</h2>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>测试</th>
              <th>审核</th>
              <th>发布</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.name}</td>
                <td>{item.kind}</td>
                <td>
                  <span className={styles.badge}>{item.testStatus}</span>
                </td>
                <td>
                  <span className={styles.badge}>{item.reviewStatus}</span>
                </td>
                <td>
                  {item.publishedVersion ? `v${item.publishedVersion}` : "—"}
                </td>
                <td>
                  <div className={styles.rowActions}>
                    <button
                      className={styles.secondary}
                      disabled={busy}
                      onClick={() =>
                        void run(
                          () => creatorTestCapability(item.id),
                          `已完成“${item.name}”测试。`,
                        )
                      }
                    >
                      测试
                    </button>
                    <button
                      className={styles.primary}
                      disabled={busy || item.testStatus !== "passed"}
                      onClick={() => {
                        const reason = window.prompt("提交说明", "请审核")?.trim() ?? "";
                        if (!reason) return;
                        void run(
                          () => creatorSubmitCapability(item.id, reason),
                          `“${item.name}”已提交审核。`,
                        );
                      }}
                    >
                      提交审核
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!items.length && (
              <tr>
                <td colSpan={6}>尚无个人草稿。</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className={styles.section}>
        <h2>运行概览</h2>
        {summary ? (
          <>
            <dl className={styles.meta}>
              <div>
                <dt>总运行</dt>
                <dd>{summary.total}</dd>
              </div>
              {Object.entries(summary.statuses).map(([status, count]) => (
                <div key={status}>
                  <dt>{status}</dt>
                  <dd>{count}</dd>
                </div>
              ))}
            </dl>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>能力</th>
                  <th>状态</th>
                  <th>模式</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                {summary.recent.map((run) => (
                  <tr key={run.id}>
                    <td>{run.capabilityName}</td>
                    <td>
                      <span className={styles.badge}>{run.status}</span>
                    </td>
                    <td>{run.mode}</td>
                    <td>{new Date(run.createdAt).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : (
          <p className={styles.lede}>暂无运行汇总。</p>
        )}
      </div>
    </div>
  );
}
