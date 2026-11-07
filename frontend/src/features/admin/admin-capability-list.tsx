"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { AssistantIcon } from "@/features/assistant/assistant-icon";
import type { CapabilityKind } from "@/features/assistant/types";
import {
  createCapability,
  listAdminCapabilities,
  type CapabilityDraftInput,
  type CapabilitySummary,
} from "./api";
import {
  AdminPageHeader,
  EmptyState,
  InlineError,
  LoadingBlock,
  StatusBadge,
  formatDate,
  kindLabels,
} from "./admin-ui";

const descriptions: Record<CapabilityKind, string> = {
  tool: "管理工具定义、执行器配置、输入输出约束与发布状态。",
  skill: "管理 Markdown 技能、资源与依赖声明，并控制可用版本。",
  mcp: "管理 MCP 服务端点、认证引用、工具授权与连接状态。",
  agent: "管理模型、System Prompt、能力依赖与调试发布流程。",
};

const statusFilters = [
  { value: "", label: "全部状态" },
  { value: "published", label: "已发布" },
  { value: "draft", label: "草稿" },
  { value: "disabled", label: "已停用" },
];

function emptyDraft(kind: CapabilityKind): CapabilityDraftInput {
  return {
    name: "",
    description: "",
    category: "未分类",
    icon: kind,
    steps: [],
    tools: [],
    content: kind === "skill" ? "" : null,
    config:
      kind === "tool"
        ? { executor: "http", endpoint: "", timeoutSeconds: 30, permissions: [] }
        : kind === "skill"
          ? { dependencies: [] }
          : kind === "mcp"
            ? { endpoint: "", authType: "none", credentialRef: "", discoverTools: true }
            : { model: "", systemPrompt: "", dependencies: [] },
  };
}

export function AdminCapabilityList({ kind }: { kind: CapabilityKind }) {
  const router = useRouter();
  const [items, setItems] = useState<CapabilitySummary[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<CapabilityDraftInput>(() => emptyDraft(kind));

  useEffect(() => {
    setDraft(emptyDraft(kind));
  }, [kind]);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      void listAdminCapabilities({ kind, status, q: query })
        .then((data) => {
          if (!active) return;
          setItems(data);
          setError("");
        })
        .catch((reason: unknown) => {
          if (!active) return;
          setError(reason instanceof Error ? reason.message : "能力列表加载失败。");
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 180);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [kind, query, status]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!draft.name.trim() || creating) return;
    setCreating(true);
    setError("");
    try {
      const created = await createCapability(kind, draft);
      setCreateOpen(false);
      router.push(`/assistant/admin/capabilities/${created.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "创建能力失败。");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="admin-page">
      <AdminPageHeader
        eyebrow={`CAPABILITIES / ${kind.toUpperCase()}`}
        title={`${kindLabels[kind]}管理`}
        description={descriptions[kind]}
        actions={
          <button className="admin-primary-button" onClick={() => setCreateOpen(true)}>
            <AssistantIcon name="plus" size={17} />
            新建{kindLabels[kind]}
          </button>
        }
      />
      <section className="admin-toolbar" aria-label="能力筛选">
        <label className="admin-search">
          <AssistantIcon name="search" size={18} />
          <span className="admin-sr-only">搜索{kindLabels[kind]}管理</span>
          <input
            aria-label={`搜索${kindLabels[kind]}管理`}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索名称、描述或分类…"
          />
        </label>
        <div className="admin-filter-row">
          {statusFilters.map((item) => (
            <button
              key={item.value}
              className={status === item.value ? "admin-chip admin-chip--active" : "admin-chip"}
              aria-pressed={status === item.value}
              onClick={() => setStatus(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <span className="admin-result-count">共 {items.length} 项</span>
      </section>
      {error && <InlineError>{error}</InlineError>}
      {loading && items.length === 0 ? (
        <LoadingBlock label="正在读取能力数据…" />
      ) : items.length === 0 ? (
        <EmptyState
          title={`还没有${kindLabels[kind]}`}
          description="创建草稿并完成基础配置后，可在详情页发布到用户工作台。"
          action={
            <button className="admin-secondary-button" onClick={() => setCreateOpen(true)}>
              创建第一个草稿
            </button>
          }
        />
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>状态</th>
                <th>版本</th>
                <th>来源</th>
                <th>更新时间</th>
                <th aria-label="操作" />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link
                      className="admin-resource-name"
                      href={`/assistant/admin/capabilities/${item.id}`}
                    >
                      <span>
                        <AssistantIcon name={item.icon || item.kind} size={19} />
                      </span>
                      <div>
                        <strong>{item.name}</strong>
                        <small>
                          {item.category} · {item.description || "尚未填写描述"}
                        </small>
                      </div>
                    </Link>
                  </td>
                  <td>
                    <div className="admin-status-stack">
                      <StatusBadge status={item.status} />
                      {item.hasDraft && item.status === "published" && (
                        <small>有新草稿 v{item.draftVersion}</small>
                      )}
                    </div>
                  </td>
                  <td>
                    <strong className="admin-version">
                      {item.publishedVersion ? `v${item.publishedVersion}` : "—"}
                    </strong>
                    {item.draftVersion && !item.publishedVersion && (
                      <small className="admin-muted">草稿 v{item.draftVersion}</small>
                    )}
                  </td>
                  <td>
                    <span className="admin-source">
                      {item.source === "demo" ? "演示能力" : "管理端创建"}
                    </span>
                  </td>
                  <td>{formatDate(item.updatedAt)}</td>
                  <td>
                    <Link
                      className="admin-row-link"
                      href={`/assistant/admin/capabilities/${item.id}`}
                      aria-label={`查看${item.name}详情`}
                    >
                      详情
                      <AssistantIcon name="arrow" size={15} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createOpen && (
        <div className="admin-modal-layer" role="presentation">
          <button
            className="admin-modal-backdrop"
            aria-label="关闭新建能力"
            onClick={() => setCreateOpen(false)}
          />
          <section className="admin-modal" role="dialog" aria-modal="true" aria-label="新建能力">
            <div className="admin-modal-heading">
              <div>
                <p className="admin-eyebrow">NEW DRAFT</p>
                <h2>新建{kindLabels[kind]}草稿</h2>
              </div>
              <button aria-label="关闭" onClick={() => setCreateOpen(false)}>
                <AssistantIcon name="close" size={18} />
              </button>
            </div>
            <form onSubmit={submit}>
              <label>
                能力名称
                <input
                  autoFocus
                  value={draft.name}
                  onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                  maxLength={120}
                  required
                />
              </label>
              <label>
                描述
                <textarea
                  value={draft.description}
                  onChange={(event) =>
                    setDraft({ ...draft, description: event.target.value })
                  }
                  maxLength={2000}
                  rows={3}
                />
              </label>
              <div className="admin-form-grid">
                <label>
                  分类
                  <input
                    value={draft.category}
                    onChange={(event) => setDraft({ ...draft, category: event.target.value })}
                    maxLength={80}
                    required
                  />
                </label>
                <label>
                  图标
                  <select
                    value={draft.icon}
                    onChange={(event) => setDraft({ ...draft, icon: event.target.value })}
                  >
                    <option value={kind}>{kindLabels[kind]}</option>
                    <option value="search">搜索</option>
                    <option value="database">数据库</option>
                    <option value="code">代码</option>
                    <option value="globe">网页</option>
                    <option value="file">文件</option>
                    <option value="spark">Spark</option>
                  </select>
                </label>
              </div>
              {error && <InlineError>{error}</InlineError>}
              <div className="admin-modal-actions">
                <button
                  type="button"
                  className="admin-secondary-button"
                  onClick={() => setCreateOpen(false)}
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="admin-primary-button"
                  disabled={creating || !draft.name.trim()}
                >
                  {creating ? "正在创建…" : "创建并编辑"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
