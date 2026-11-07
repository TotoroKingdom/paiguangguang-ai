"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AssistantIcon } from "@/features/assistant/assistant-icon";
import type { CapabilityKind } from "@/features/assistant/types";
import {
  disableCapability,
  getCapability,
  publishCapability,
  updateCapabilityDraft,
  type CapabilityDetail,
  type CapabilityDraftInput,
  type CapabilitySnapshot,
} from "./api";
import {
  AdminPageHeader,
  EmptyState,
  InlineError,
  InlineNotice,
  LoadingBlock,
  StatusBadge,
  formatDate,
  kindLabels,
  kindRoutes,
  statusLabel,
} from "./admin-ui";

type DraftForm = CapabilityDraftInput;

function formFromSnapshot(snapshot: CapabilitySnapshot): DraftForm {
  return {
    name: snapshot.name,
    description: snapshot.description,
    category: snapshot.category,
    icon: snapshot.icon,
    steps: snapshot.steps,
    tools: snapshot.tools,
    content: snapshot.content,
    config: snapshot.config,
  };
}

function parseConfig(value: string): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(value);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    return parsed as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function AdminCapabilityDetail({
  capabilityId,
  kind,
}: {
  capabilityId: string;
  kind?: CapabilityKind;
}) {
  const [detail, setDetail] = useState<CapabilityDetail | null>(null);
  const [form, setForm] = useState<DraftForm | null>(null);
  const [configText, setConfigText] = useState("{}");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"save" | "publish" | "disable" | null>(null);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [confirmDisable, setConfirmDisable] = useState(false);

  const applyDetail = (next: CapabilityDetail) => {
    setDetail(next);
    const source = next.draft?.snapshot ?? next.published?.snapshot;
    if (source) {
      setForm(formFromSnapshot(source));
      setConfigText(JSON.stringify(source.config ?? {}, null, 2));
    }
    setDirty(false);
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    void getCapability(capabilityId)
      .then((next) => {
        if (!active) return;
        applyDetail(next);
        setError("");
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "能力详情加载失败。");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // The ID is the resource boundary; other state is derived from the response.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [capabilityId]);

  const config = useMemo(() => parseConfig(configText), [configText]);

  const updateForm = (patch: Partial<DraftForm>) => {
    setForm((current) => (current ? { ...current, ...patch } : current));
    setDirty(true);
    setNotice("");
  };

  const updateConfig = (key: string, value: unknown) => {
    const current = parseConfig(configText) ?? {};
    setConfigText(JSON.stringify({ ...current, [key]: value }, null, 2));
    setDirty(true);
    setNotice("");
  };

  const saveDraft = async (): Promise<CapabilityDetail | null> => {
    if (!detail || !form) return null;
    if (!config) {
      setError("配置 JSON 格式无效，请修正后再保存。");
      return null;
    }
    setBusy("save");
    setError("");
    try {
      const saved = await updateCapabilityDraft(
        detail.id,
        detail.draft?.id ?? null,
        { ...form, config },
      );
      applyDetail(saved);
      setNotice("草稿已保存。已发布版本保持不变。");
      return saved;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "草稿保存失败。");
      return null;
    } finally {
      setBusy(null);
    }
  };

  const publish = async () => {
    if (!detail?.draft || dirty) return;
    setBusy("publish");
    setError("");
    try {
      const published = await publishCapability(detail.id, detail.draft.id);
      applyDetail(published);
      setNotice(`版本 v${published.publishedVersion} 已发布到用户工作台。`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "版本发布失败。");
    } finally {
      setBusy(null);
    }
  };

  const disable = async () => {
    if (!detail) return;
    setBusy("disable");
    setError("");
    try {
      const disabled = await disableCapability(detail.id);
      applyDetail(disabled);
      setConfirmDisable(false);
      setNotice("能力已停用；新的用户目录和新调用将不再包含该能力。");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "能力停用失败。");
    } finally {
      setBusy(null);
    }
  };

  if (loading) {
    return (
      <div className="admin-page">
        <LoadingBlock label="正在加载能力详情…" />
      </div>
    );
  }

  if (!detail || !form) {
    const fallbackKind = kind ?? "tool";
    return (
      <div className="admin-page">
        <InlineError>{error || "找不到这项能力。"}</InlineError>
        <Link className="admin-secondary-button" href={kindRoutes[fallbackKind]}>
          返回{kindLabels[fallbackKind]}管理
        </Link>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <AdminPageHeader
        eyebrow={`${detail.kind.toUpperCase()} / VERSION ${detail.publishedVersion ?? detail.draftVersion ?? "—"}`}
        title={detail.name}
        description={`${detail.category} · ${
          detail.source === "demo" ? "系统演示能力" : "管理端创建能力"
        } · 当前状态：${statusLabel(detail.status)}`}
        actions={
          <>
            <Link className="admin-secondary-button" href={kindRoutes[detail.kind]}>
              返回列表
            </Link>
            <button
              className="admin-primary-button"
              onClick={() => void saveDraft()}
              disabled={busy !== null}
            >
              {busy === "save" ? "正在保存…" : "保存草稿"}
            </button>
          </>
        }
      />
      {error && <InlineError>{error}</InlineError>}
      {notice && <InlineNotice>{notice}</InlineNotice>}

      <section className="admin-detail-grid">
        <div className="admin-panel admin-form-panel">
          <div className="admin-panel-heading">
            <div>
              <p className="admin-eyebrow">DRAFT EDITOR</p>
              <h2>{detail.draft ? `编辑草稿 v${detail.draft.version}` : "创建新的编辑草稿"}</h2>
            </div>
            <span className={dirty ? "admin-dirty" : "admin-muted"}>
              {dirty ? "有未保存修改" : "已同步"}
            </span>
          </div>
          {!detail.draft && (
            <p className="admin-form-note">
              当前能力已发布。保存后会创建新的草稿版本，不会覆盖 v
              {detail.publishedVersion} 的发布快照。
            </p>
          )}
          <div className="admin-form-grid">
            <label>
              能力名称
              <input
                value={form.name}
                onChange={(event) => updateForm({ name: event.target.value })}
                maxLength={120}
              />
            </label>
            <label>
              分类
              <input
                value={form.category}
                onChange={(event) => updateForm({ category: event.target.value })}
                maxLength={80}
              />
            </label>
          </div>
          <label>
            描述
            <textarea
              value={form.description}
              onChange={(event) => updateForm({ description: event.target.value })}
              maxLength={2000}
              rows={3}
            />
          </label>
          <div className="admin-form-grid">
            <label>
              图标
              <select
                value={form.icon}
                onChange={(event) => updateForm({ icon: event.target.value })}
              >
                <option value={detail.kind}>{kindLabels[detail.kind]}</option>
                <option value="search">搜索</option>
                <option value="database">数据库</option>
                <option value="code">代码</option>
                <option value="globe">网页</option>
                <option value="chart">图表</option>
                <option value="file">文件</option>
                <option value="spark">Spark</option>
              </select>
            </label>
            <label>
              工具 / 依赖名称（逗号分隔）
              <input
                value={form.tools.join(", ")}
                onChange={(event) =>
                  updateForm({
                    tools: event.target.value
                      .split(",")
                      .map((item) => item.trim())
                      .filter(Boolean),
                  })
                }
                placeholder="知识搜索, 文件读取"
              />
            </label>
          </div>
          <label>
            执行步骤（每行一个）
            <textarea
              value={form.steps.join("\n")}
              onChange={(event) =>
                updateForm({
                  steps: event.target.value
                    .split("\n")
                    .map((item) => item.trim())
                    .filter(Boolean),
                })
              }
              rows={5}
            />
          </label>

          {detail.kind === "skill" && (
            <label>
              Markdown 技能正文
              <textarea
                className="admin-code-input"
                value={form.content ?? ""}
                onChange={(event) => updateForm({ content: event.target.value })}
                rows={12}
                placeholder="# 技能名称&#10;&#10;说明技能如何处理任务…"
              />
            </label>
          )}

          {detail.kind === "tool" && (
            <>
              <div className="admin-form-grid">
                <label>
                  执行器
                  <select
                    value={String(config?.executor ?? "http")}
                    onChange={(event) => updateConfig("executor", event.target.value)}
                  >
                    <option value="http">HTTP 执行器（未接入）</option>
                    <option value="builtin">内置执行器（未接入）</option>
                    <option value="demo">演示执行器</option>
                  </select>
                </label>
                <label>
                  超时（秒）
                  <input
                    type="number"
                    min={1}
                    max={600}
                    value={Number(config?.timeoutSeconds ?? 30)}
                    onChange={(event) =>
                      updateConfig("timeoutSeconds", Number(event.target.value))
                    }
                  />
                </label>
              </div>
              <label>
                执行器端点
                <input
                  value={String(config?.endpoint ?? "")}
                  onChange={(event) => updateConfig("endpoint", event.target.value)}
                  placeholder="https://internal.example/tool"
                />
              </label>
            </>
          )}

          {detail.kind === "mcp" && (
            <>
              <label>
                MCP 服务端点
                <input
                  value={String(config?.endpoint ?? "")}
                  onChange={(event) => updateConfig("endpoint", event.target.value)}
                  placeholder="https://mcp.example.com/sse"
                />
              </label>
              <div className="admin-form-grid">
                <label>
                  认证方式
                  <select
                    value={String(config?.authType ?? "none")}
                    onChange={(event) => updateConfig("authType", event.target.value)}
                  >
                    <option value="none">无需认证</option>
                    <option value="bearer">Bearer（仅保存引用）</option>
                    <option value="header">自定义 Header（仅保存引用）</option>
                  </select>
                </label>
                <label>
                  凭据引用
                  <input
                    value={String(config?.credentialRef ?? "")}
                    onChange={(event) => updateConfig("credentialRef", event.target.value)}
                    placeholder="vault://mcp/knowledge"
                  />
                </label>
              </div>
              <p className="admin-form-note">
                控制台只保存凭据引用，不保存明文密钥。连接测试与工具发现将在后续阶段接入。
              </p>
            </>
          )}

          {detail.kind === "agent" && (
            <>
              <label>
                模型
                <input
                  value={String(config?.model ?? "")}
                  onChange={(event) => updateConfig("model", event.target.value)}
                  placeholder="尚未接入真实模型"
                />
              </label>
              <label>
                System Prompt
                <textarea
                  className="admin-code-input"
                  value={String(config?.systemPrompt ?? "")}
                  onChange={(event) => updateConfig("systemPrompt", event.target.value)}
                  rows={6}
                />
              </label>
            </>
          )}

          <label>
            高级配置 JSON
            <textarea
              className="admin-code-input"
              value={configText}
              onChange={(event) => {
                setConfigText(event.target.value);
                setDirty(true);
                setNotice("");
              }}
              rows={9}
              aria-label="高级配置 JSON"
            />
          </label>
          {!config && <InlineError>配置 JSON 格式无效。</InlineError>}
          <div className="admin-form-actions">
            <button
              className="admin-primary-button"
              onClick={() => void saveDraft()}
              disabled={busy !== null}
            >
              {busy === "save" ? "正在保存…" : "保存草稿"}
            </button>
            {detail.draft && (
              <button
                className="admin-secondary-button"
                onClick={() => void publish()}
                disabled={busy !== null || dirty || !config}
                title={dirty ? "请先保存草稿" : undefined}
              >
                {busy === "publish" ? "正在发布…" : `发布 v${detail.draft.version}`}
              </button>
            )}
            {detail.status === "published" && (
              <button
                className="admin-danger-button"
                onClick={() => setConfirmDisable(true)}
                disabled={busy !== null}
              >
                停用能力
              </button>
            )}
          </div>
        </div>

        <aside className="admin-detail-side">
          <section className="admin-panel">
            <p className="admin-eyebrow">PUBLICATION</p>
            <h2>发布状态</h2>
            <dl className="admin-definition-list">
              <div>
                <dt>定义状态</dt>
                <dd>
                  <StatusBadge status={detail.status} />
                </dd>
              </div>
              <div>
                <dt>已发布版本</dt>
                <dd>{detail.publishedVersion ? `v${detail.publishedVersion}` : "尚未发布"}</dd>
              </div>
              <div>
                <dt>当前草稿</dt>
                <dd>{detail.draftVersion ? `v${detail.draftVersion}` : "无"}</dd>
              </div>
              <div>
                <dt>执行模式</dt>
                <dd>{detail.executionMode === "demo" ? "演示执行" : "模拟执行"}</dd>
              </div>
              <div>
                <dt>能力 ID</dt>
                <dd>
                  <code>{detail.id}</code>
                </dd>
              </div>
            </dl>
            <p className="admin-form-note">
              发布操作会原子地切换当前已发布版本，并将编辑草稿固定为不可变快照。
            </p>
          </section>

          <section className="admin-panel">
            <div className="admin-panel-heading">
              <div>
                <p className="admin-eyebrow">HISTORY</p>
                <h2>版本历史</h2>
              </div>
              <span>{detail.versions.length} 个版本</span>
            </div>
            {detail.versions.length === 0 ? (
              <EmptyState title="暂无版本" description="保存草稿后这里会出现版本记录。" />
            ) : (
              <ol className="admin-version-list">
                {detail.versions.map((version) => (
                  <li key={version.id}>
                    <span>v{version.version}</span>
                    <div>
                      <strong>{version.snapshot.name}</strong>
                      <small>{version.changelog || "无变更说明"}</small>
                      <small>
                        {version.status === "published"
                          ? `发布于 ${formatDate(version.publishedAt)}`
                          : version.status === "retired"
                            ? `停用于 ${formatDate(version.retiredAt)}`
                            : `创建于 ${formatDate(version.createdAt)}`}
                      </small>
                    </div>
                    <StatusBadge status={version.status} />
                  </li>
                ))}
              </ol>
            )}
          </section>
        </aside>
      </section>

      {confirmDisable && (
        <div className="admin-modal-layer" role="presentation">
          <button
            className="admin-modal-backdrop"
            aria-label="取消停用"
            onClick={() => setConfirmDisable(false)}
          />
          <section className="admin-modal admin-modal--small" role="dialog" aria-modal="true">
            <p className="admin-eyebrow">CONFIRM DISABLE</p>
            <h2>停用“{detail.name}”？</h2>
            <p>
              停用后，该能力会立即从用户工作台的可用目录中移除，新的调用也会被服务端拒绝。历史版本与审计记录会保留。
            </p>
            <div className="admin-modal-actions">
              <button
                className="admin-secondary-button"
                onClick={() => setConfirmDisable(false)}
              >
                取消
              </button>
              <button
                className="admin-danger-button"
                onClick={() => void disable()}
                disabled={busy === "disable"}
              >
                {busy === "disable" ? "正在停用…" : "确认停用"}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
