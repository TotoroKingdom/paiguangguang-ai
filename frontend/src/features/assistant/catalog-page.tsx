"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AssistantDialog } from "./assistant-dialog";
import { AssistantIcon } from "./assistant-icon";
import { getCapabilities } from "./data";
import { testConnection } from "./mock-service";
import { useAssistant } from "./provider";
import type { Capability, CapabilityKind, ConnectorConfig, ConnectorStatus } from "./types";
import styles from "./catalog.module.css";

const labels: Record<CapabilityKind, { title: string; description: string; unit: string }> = {
  tool: { title: "工具库", description: "选择系统示例工具，在聊天中使用。", unit: "工具" },
  skill: {
    title: "技能库",
    description: "浏览系统示例技能，或导入自己的 Markdown 技能。",
    unit: "技能",
  },
  mcp: {
    title: "连接器中心",
    description: "配置和体验模拟连接，所有状态均为演示数据。",
    unit: "连接器",
  },
  agent: { title: "智能体中心", description: "选择智能体示例，体验不同任务场景。", unit: "智能体" },
};
const statusLabels: Record<ConnectorStatus, string> = {
  connected: "已连接",
  disconnected: "已断开",
  unconfigured: "待配置",
  connecting: "连接中",
  error: "失败",
  unauthorized: "待授权",
};
const makeId = () => `skill-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

export function CatalogPage({ kind }: { kind: CapabilityKind }) {
  const { state, dispatch } = useAssistant();
  const latestState = useRef(state);
  latestState.current = state;
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const [connectorPickerOpen, setConnectorPickerOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("全部");
  const [selected, setSelected] = useState<Capability | null>(null);
  const [favoritesOpen, setFavoritesOpen] = useState(false);
  const [config, setConfig] = useState<ConnectorConfig | null>(null);
  const [simulateFailure, setSimulateFailure] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<Capability | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const items = useMemo(
    () => getCapabilities(state).filter((item) => item.kind === kind),
    [state, kind],
  );
  const categories =
    kind === "mcp"
      ? ["全部", "已连接", "待配置", "待授权", "失败"]
      : ["全部", ...Array.from(new Set(items.map((item) => item.category)))];
  const sourceLabel = (item: Capability) =>
    item.source === "personal" ? "个人导入" : item.source === "managed" ? "平台发布" : "系统示例";
  const connectorFor = (item: Capability): ConnectorConfig =>
    state.connectors.find((connector) => connector.id === item.id) ?? {
      id: item.id,
      name: item.name,
      url: "",
      status: "unconfigured",
    };
  const visible = items.filter((item) => {
    const connector = connectorFor(item);
    const matches =
      `${item.name} ${item.description} ${item.category} ${kind === "mcp" ? connector.name : ""}`
        .toLowerCase()
        .includes(query.toLowerCase().trim());
    const category =
      kind === "mcp"
        ? filter === "待配置"
          ? ["unconfigured", "disconnected"].includes(connector.status)
          : statusLabels[connector.status] === filter
        : item.category === filter;
    return matches && (filter === "全部" || category);
  });
  const toggleFavorite = (id: string) => dispatch({ type: "TOGGLE_FAVORITE", id });
  const importSkill = async (file?: File) => {
    setError("");
    if (!file) return;
    if (!/\.md$/i.test(file.name)) {
      setError("请选择 .md 格式的技能文件。");
      return;
    }
    if (file.size > 256 * 1024) {
      setError("技能文件不能超过 256 KiB。");
      return;
    }
    try {
      const content = await file.text();
      if (!content.trim()) {
        setError("技能正文不能为空。");
        return;
      }
      const title = content.match(/^\s*#\s+(.+)$/m)?.[1]?.trim() || file.name.replace(/\.md$/i, "");
      if (!title || title.length > 80) {
        setError("技能名称须为 1 至 80 个字符。");
        return;
      }
      const description =
        content
          .replace(/^\s*#+\s+.*$/gm, "")
          .trim()
          .replace(/\s+/g, " ")
          .slice(0, 120) || "个人导入的技能示例。";
      dispatch({
        type: "IMPORT_SKILL",
        skill: {
          id: makeId(),
          kind: "skill",
          name: title,
          description,
          category: "个人技能",
          icon: "skill",
          source: "personal",
          steps: ["理解任务", "参考技能内容", "整理模拟结果"],
          content,
        },
      });
      setNotice(`已导入技能“${title}”。`);
    } catch {
      setError("读取技能文件失败，请重试。");
    }
  };
  const saveConfig = () => {
    if (!config) return;
    if (!config.name.trim() || !config.url.trim()) {
      setError("请填写连接名称和地址。");
      return;
    }
    const name = config.name.trim();
    const url = config.url.trim();
    if (name.length > 80 || url.length > 2000) {
      setError("名称不能超过 80 个字符，地址不能超过 2000 个字符。");
      return;
    }
    try {
      const parsed = new URL(url);
      if (!["http:", "https:"].includes(parsed.protocol) || !parsed.hostname) throw new Error();
    } catch {
      setError("请输入有效的 HTTP 或 HTTPS 地址。");
      return;
    }
    dispatch({
      type: "UPSERT_CONNECTOR",
      connector: { ...config, name, url, status: "disconnected", lastError: undefined },
    });
    setConfig(null);
    setError("");
    setNotice("连接配置已保存，可进行模拟测试。");
  };
  const runTest = async (connector: ConnectorConfig) => {
    const current = { ...connector, status: "connecting" as const, lastError: undefined };
    dispatch({ type: "UPSERT_CONNECTOR", connector: current });
    const result = await testConnection(current, simulateFailure);
    if (
      !mounted.current ||
      latestState.current.connectors.find((item) => item.id === current.id) !== current
    )
      return;
    dispatch({ type: "UPSERT_CONNECTOR", connector: result });
    setNotice(
      result.status === "connected" ? "模拟连接成功。" : result.lastError || "模拟连接失败。",
    );
  };
  return (
    <section className={styles.page}>
      <div className={styles.heading}>
        <div>
          <p className={styles.eyebrow}>交互原型 · 模拟数据</p>
          <h1>{labels[kind].title}</h1>
          <p>{labels[kind].description}</p>
        </div>
        <div className={styles.headingActions}>
          {kind === "skill" && (
            <label className={styles.secondary}>
              导入技能
              <input
                aria-label="导入技能文件"
                className={styles.hiddenInput}
                type="file"
                accept=".md,text/markdown"
                onChange={(event) => {
                  void importSkill(event.target.files?.[0]);
                  event.target.value = "";
                }}
              />
            </label>
          )}
          {kind === "mcp" && (
            <button className={styles.secondary} onClick={() => setConnectorPickerOpen(true)}>
              连接设置
            </button>
          )}
          <button className={styles.outline} onClick={() => setFavoritesOpen(true)}>
            管理常用
          </button>
        </div>
      </div>
      {notice && (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      )}
      {error && !config && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      <label className={styles.search}>
        <AssistantIcon name="search" size={20} />
        <span className={styles.srOnly}>搜索{labels[kind].unit}</span>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={`搜索${labels[kind].unit}名称或能力…`}
        />
      </label>
      <div className={styles.filterRow}>
        <div className={styles.chips}>
          {categories.map((category) => (
            <button
              key={category}
              className={filter === category ? styles.activeChip : styles.chip}
              aria-pressed={filter === category}
              onClick={() => setFilter(category)}
            >
              {category}
            </button>
          ))}
        </div>
        <span>
          共 {visible.length} 个{labels[kind].unit}
        </span>
      </div>
      {visible.length === 0 ? (
        <p className={styles.empty}>没有找到符合条件的{labels[kind].unit}。</p>
      ) : (
        <div className={styles.grid}>
          {visible.map((item, index) => {
            const connector = connectorFor(item);
            return (
              <article className={styles.card} key={item.id}>
                <button className={styles.cardMain} onClick={() => setSelected(item)}>
                  <span className={`${styles.iconBox} ${styles[`tone${index % 4}`]}`}>
                    <AssistantIcon name={item.icon || kind} size={30} />
                  </span>
                  <span>
                    <strong>{kind === "mcp" ? connector.name : item.name}</strong>
                    <span className={styles.description}>{item.description}</span>
                  </span>
                </button>
                <div className={styles.cardBottom}>
                  <span className={styles.badge}>
                    {kind === "mcp" && (
                      <span
                        aria-hidden="true"
                        className={`${styles.statusDot} ${connector.status === "connected" ? styles.statusConnected : connector.status === "error" ? styles.statusError : ""}`}
                      />
                    )}
                    {kind === "mcp"
                      ? `${statusLabels[connector.status]} · ${item.tools?.length ?? 0} 个工具`
                      : kind === "skill"
                        ? `${item.steps.length} 个步骤 · ${sourceLabel(item)}`
                        : kind === "agent"
                          ? `${item.tools?.length ?? 0} 个工具 · 多步执行`
                            : sourceLabel(item)}
                  </span>
                  <button
                    className={styles.smallButton}
                    aria-label={`${state.favorites.includes(item.id) ? "移出" : "添加"}常用：${item.name}`}
                    onClick={() => toggleFavorite(item.id)}
                  >
                    {state.favorites.includes(item.id) ? "✓ 已添加" : "添加常用"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
      {connectorPickerOpen && (
        <AssistantDialog title="选择连接器" onClose={() => setConnectorPickerOpen(false)}>
          <p className={styles.dialogHint}>选择需要配置的连接器。</p>
          <div className={styles.list}>
            {items.map((item) => (
              <button
                className={styles.listItem}
                key={item.id}
                onClick={() => {
                  setError("");
                  setConfig(connectorFor(item));
                  setConnectorPickerOpen(false);
                }}
              >
                {connectorFor(item).name}{" "}
                <span className={styles.muted}>{statusLabels[connectorFor(item).status]}</span>
              </button>
            ))}
          </div>
        </AssistantDialog>
      )}
      {favoritesOpen && (
        <AssistantDialog title="管理常用" onClose={() => setFavoritesOpen(false)}>
          <p className={styles.dialogHint}>选择聊天中经常使用的{labels[kind].unit}。</p>
          <div className={styles.list}>
            {items.map((item) => (
              <label key={item.id} className={styles.listItem}>
                <input
                  type="checkbox"
                  checked={state.favorites.includes(item.id)}
                  onChange={() => toggleFavorite(item.id)}
                />
                {item.name}
              </label>
            ))}
          </div>
          <div className={styles.dialogActions}>
            <button className={styles.primary} onClick={() => setFavoritesOpen(false)}>
              完成
            </button>
          </div>
        </AssistantDialog>
      )}
      {selected && (
        <AssistantDialog
          title={kind === "mcp" ? connectorFor(selected).name : selected.name}
          onClose={() => setSelected(null)}
        >
          <p className={styles.dialogHint}>{selected.description}</p>
          <p className={styles.muted}>
            {sourceLabel(selected)} ·
            交互原型，操作结果为模拟数据
          </p>
          <h3>使用步骤</h3>
          <ol>
            {selected.steps.map((step, index) => (
              <li key={`${step}-${index}`}>{step}</li>
            ))}
          </ol>
          {selected.tools && <p>示例工具：{selected.tools.join("、")}</p>}
          {selected.content !== undefined && (
            <>
              <h3>技能正文</h3>
              <pre className={styles.content}>{selected.content}</pre>
            </>
          )}
          {kind === "mcp" && (
            <div className={styles.connector}>
              <p>状态：{statusLabels[connectorFor(selected).status]}</p>
              {connectorFor(selected).lastError && (
                <p className={styles.error} role="alert">
                  {connectorFor(selected).lastError}
                </p>
              )}
              <label>
                <input
                  type="checkbox"
                  checked={simulateFailure}
                  onChange={(event) => setSimulateFailure(event.target.checked)}
                />{" "}
                模拟连接失败
              </label>
              <div className={styles.dialogActions}>
                <button
                  className={styles.secondary}
                  onClick={() => {
                    setError("");
                    setConfig(connectorFor(selected));
                    setSelected(null);
                  }}
                >
                  连接设置
                </button>
                <button
                  className={styles.secondary}
                  disabled={connectorFor(selected).status === "connecting"}
                  onClick={() => void runTest(connectorFor(selected))}
                >
                  {connectorFor(selected).status === "error" ? "重试连接" : "测试连接"}
                </button>
                {connectorFor(selected).status === "connected" && (
                  <button
                    className={styles.secondary}
                    onClick={() => {
                      dispatch({
                        type: "UPSERT_CONNECTOR",
                        connector: { ...connectorFor(selected), status: "disconnected" },
                      });
                      setNotice("已断开模拟连接。");
                    }}
                  >
                    断开连接
                  </button>
                )}
              </div>
            </div>
          )}
          <div className={styles.dialogActions}>
            {selected.source === "personal" && (
              <button
                className={styles.danger}
                onClick={() => {
                  setConfirmDelete(selected);
                  setSelected(null);
                }}
              >
                删除技能
              </button>
            )}
            <button
              className={styles.primary}
              onClick={() => {
                dispatch({
                  type: "SET_DRAFT",
                  patch: {
                    capability: {
                      id: selected.id,
                      kind: selected.kind,
                      name: kind === "mcp" ? connectorFor(selected).name : selected.name,
                    },
                  },
                });
                setSelected(null);
                setNotice("已选择，可在下方输入框中使用。");
              }}
            >
              用于聊天
            </button>
          </div>
        </AssistantDialog>
      )}
      {config && (
        <AssistantDialog
          title="连接设置"
          onClose={() => {
            setConfig(null);
            setError("");
          }}
        >
          <div className={styles.form}>
            <label>
              连接名称
              <input
                maxLength={80}
                value={config.name}
                onChange={(event) => setConfig({ ...config, name: event.target.value })}
              />
            </label>
            <label>
              连接地址
              <input
                type="url"
                maxLength={2000}
                value={config.url}
                onChange={(event) => setConfig({ ...config, url: event.target.value })}
                placeholder="https://example.com/mcp"
              />
            </label>
            <p className={styles.muted}>配置仅保存在本地，测试为模拟操作。</p>
            {error && (
              <p className={styles.error} role="alert">
                {error}
              </p>
            )}
            <div className={styles.dialogActions}>
              <button className={styles.secondary} onClick={() => setConfig(null)}>
                取消
              </button>
              <button className={styles.primary} onClick={saveConfig}>
                保存配置
              </button>
            </div>
          </div>
        </AssistantDialog>
      )}
      {confirmDelete && (
        <AssistantDialog title="删除个人技能" onClose={() => setConfirmDelete(null)}>
          <p>确定删除“{confirmDelete.name}”吗？</p>
          <div className={styles.dialogActions}>
            <button className={styles.secondary} onClick={() => setConfirmDelete(null)}>
              取消
            </button>
            <button
              className={styles.danger}
              onClick={() => {
                dispatch({ type: "DELETE_SKILL", id: confirmDelete.id });
                setConfirmDelete(null);
                setNotice("个人技能已删除。");
              }}
            >
              确认删除
            </button>
          </div>
        </AssistantDialog>
      )}
    </section>
  );
}
