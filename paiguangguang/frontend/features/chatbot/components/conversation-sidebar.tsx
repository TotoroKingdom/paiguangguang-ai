"use client";

import Link from "next/link";
import { useMemo } from "react";

import type {
  ConversationData,
  ConversationStatus,
} from "../types/conversation";
import { ChatbotMark } from "./chatbot-mark";

type ConversationSidebarProps = {
  selectedStatus: ConversationStatus;
  selectedConversationId: string | null;
  conversations: ConversationData[];
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  onChangeStatus: (status: ConversationStatus) => void | Promise<void>;
  onSelectConversation: (conversationId: string) => void | Promise<void>;
  onLoadMore: () => void | Promise<void>;
  onCreateConversation: () => void | Promise<void>;
  onRenameConversation: (conversation: ConversationData) => void | Promise<void>;
  onArchiveConversation: (conversation: ConversationData) => void | Promise<void>;
  onRestoreConversation: (conversation: ConversationData) => void | Promise<void>;
  onDeleteConversation: (conversation: ConversationData) => void | Promise<void>;
  onRefresh: () => void | Promise<void>;
};

const STATUS_LABELS: Record<ConversationStatus, string> = {
  active: "Active",
  archived: "Archived",
};

type ConversationGroup = {
  key: string;
  label: string;
  items: ConversationData[];
};

function formatTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown time";
  }
  return date.toLocaleString();
}

function toStartOfDay(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function classifyConversation(value: string, now = new Date()) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return { key: "older", label: "更早", order: 3 };
  }

  const diffDays = Math.floor((toStartOfDay(now).getTime() - toStartOfDay(date).getTime()) / 86_400_000);

  if (diffDays <= 0) {
    return { key: "today", label: "今天", order: 0 };
  }

  if (diffDays === 1) {
    return { key: "yesterday", label: "昨天", order: 1 };
  }

  if (diffDays <= 7) {
    return { key: "week", label: "7天内", order: 2 };
  }

  return { key: "older", label: "更早", order: 3 };
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="none">
      <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M16.5 16.5L20 20"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function LayoutIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="none">
      <rect x="4" y="4" width="7" height="16" rx="2.5" stroke="currentColor" strokeWidth="1.8" />
      <rect x="13" y="4" width="7" height="16" rx="2.5" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function ConversationItem({
  conversation,
  selected,
  onSelectConversation,
  onRenameConversation,
  onArchiveConversation,
  onRestoreConversation,
  onDeleteConversation,
}: {
  conversation: ConversationData;
  selected: boolean;
  onSelectConversation: (conversationId: string) => void | Promise<void>;
  onRenameConversation: (conversation: ConversationData) => void | Promise<void>;
  onArchiveConversation: (conversation: ConversationData) => void | Promise<void>;
  onRestoreConversation: (conversation: ConversationData) => void | Promise<void>;
  onDeleteConversation: (conversation: ConversationData) => void | Promise<void>;
}) {
  return (
    <article
      className={[
        "group rounded-[18px] px-3 py-3 transition",
        selected ? "bg-white shadow-[0_1px_2px_rgba(15,23,42,0.06)]" : "hover:bg-white/80",
      ].join(" ")}
    >
      <button
        type="button"
        onClick={() => void onSelectConversation(conversation.id)}
        className="block w-full text-left"
      >
        <div className="min-w-0">
          <h3 className="truncate text-[15px] font-medium leading-6 text-ink">{conversation.title}</h3>
          <p className="mt-1 truncate text-xs text-ink/45">{conversation.model}</p>
        </div>
        <p className="mt-2 text-xs text-ink/40">{formatTimestamp(conversation.last_message_at)}</p>
      </button>

      <div className="mt-2 flex flex-wrap gap-2 opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100">
        <button
          type="button"
          onClick={() => void onRenameConversation(conversation)}
          className="rounded-full border border-ink/10 bg-paper px-3 py-1.5 text-xs font-medium text-ink/65 transition hover:border-tide/30 hover:bg-white hover:text-ink"
        >
          Rename
        </button>
        {conversation.status === "active" ? (
          <button
            type="button"
            onClick={() => void onArchiveConversation(conversation)}
            className="rounded-full border border-ink/10 bg-paper px-3 py-1.5 text-xs font-medium text-ink/65 transition hover:border-tide/30 hover:bg-white hover:text-ink"
          >
            Archive
          </button>
        ) : null}
        {conversation.status === "archived" ? (
          <button
            type="button"
            onClick={() => void onRestoreConversation(conversation)}
            className="rounded-full border border-ink/10 bg-paper px-3 py-1.5 text-xs font-medium text-ink/65 transition hover:border-tide/30 hover:bg-white hover:text-ink"
          >
            Restore
          </button>
        ) : null}
        <button
          type="button"
          onClick={() => void onDeleteConversation(conversation)}
          className="rounded-full border border-clay/20 bg-clay/5 px-3 py-1.5 text-xs font-medium text-clay transition hover:border-clay/40 hover:bg-clay/10"
        >
          Delete
        </button>
      </div>
    </article>
  );
}

export function ConversationSidebar({
  selectedStatus,
  selectedConversationId,
  conversations,
  loading,
  error,
  hasMore,
  onChangeStatus,
  onSelectConversation,
  onLoadMore,
  onCreateConversation,
  onRenameConversation,
  onArchiveConversation,
  onRestoreConversation,
  onDeleteConversation,
  onRefresh,
}: ConversationSidebarProps) {
  const sections = useMemo<ConversationGroup[]>(() => {
    const grouped = new Map<string, ConversationGroup & { order: number }>();
    for (const conversation of conversations) {
      const classification = classifyConversation(conversation.last_message_at);
      const current = grouped.get(classification.key);
      if (current) {
        current.items.push(conversation);
        continue;
      }
      grouped.set(classification.key, {
        key: classification.key,
        label: classification.label,
        order: classification.order,
        items: [conversation],
      });
    }

    return Array.from(grouped.values())
      .sort((left, right) => left.order - right.order)
      .map(({ order: _order, ...section }) => section);
  }, [conversations]);

  return (
    <aside className="flex h-full flex-col bg-transparent">
      <div className="border-b border-ink/8 px-4 pb-4 pt-4">
        <div className="flex items-center justify-between gap-3">
          <Link href="/" className="flex items-center gap-2 text-tide transition hover:opacity-90">
            <ChatbotMark className="h-8 w-8 shrink-0 text-tide" />
            <span className="text-[28px] font-semibold tracking-[-0.04em] text-tide">暖心助手</span>
          </Link>

          <div aria-hidden="true" className="flex items-center gap-3 text-ink/35">
            <SearchIcon />
            <LayoutIcon />
          </div>
        </div>

        <button
          type="button"
          onClick={() => void onCreateConversation()}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-[22px] border border-ink/10 bg-white px-4 py-3 text-sm font-medium text-ink shadow-[0_1px_4px_rgba(15,23,42,0.04)] transition hover:border-tide/25 hover:bg-paper"
        >
          <span className="flex h-5 w-5 items-center justify-center rounded-full border border-current text-base leading-none">
            +
          </span>
          开启新对话
        </button>

        <div className="mt-4 flex flex-wrap gap-2">
          {(Object.keys(STATUS_LABELS) as ConversationStatus[]).map((status) => (
            <button
              key={status}
              type="button"
              aria-pressed={selectedStatus === status}
              onClick={() => void onChangeStatus(status)}
              className={[
                "rounded-full border px-3 py-2 text-sm font-medium transition",
                selectedStatus === status
                  ? "border-tide/55 bg-tide text-paper shadow-sm"
                  : "border-ink/10 bg-paper/70 text-ink hover:border-tide/40 hover:bg-white",
              ].join(" ")}
            >
              {STATUS_LABELS[status]}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 border-b border-ink/8 px-4 py-3">
        <div className="text-xs font-medium uppercase tracking-wide text-ink/45">
          {loading ? "Loading conversations" : `${conversations.length} conversations`}
        </div>
        <button
          type="button"
          onClick={() => void onRefresh()}
          className="text-sm font-semibold text-tide transition hover:text-tide/80"
        >
          Refresh
        </button>
      </div>

      <div className="min-h-0 flex-1 overscroll-contain overflow-y-auto px-3 py-4">
        {error ? (
          <div className="m-1 rounded-[18px] border border-clay/20 bg-clay/8 p-4 text-sm text-ink">
            <p className="font-semibold text-clay">Unable to load conversations</p>
            <p className="mt-2 leading-6">{error}</p>
            <button
              type="button"
              onClick={() => void onRefresh()}
              className="mt-3 rounded-full border border-clay/25 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-paper"
            >
              Retry
            </button>
          </div>
        ) : null}

        {!error && !loading && conversations.length === 0 ? (
          <div className="m-1 rounded-[18px] border border-dashed border-ink/15 bg-paper/55 p-5 text-sm leading-7 text-ink/65">
            <p className="font-semibold text-ink">No conversations yet</p>
            <p className="mt-2">Create a new conversation to start a session.</p>
          </div>
        ) : null}

        <div className="space-y-5">
          {sections.map((section) => (
            <section key={section.key}>
              <h3 className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-ink/45">
                {section.label}
              </h3>
              <div className="space-y-1">
                {section.items.map((conversation) => (
                  <ConversationItem
                    key={conversation.id}
                    conversation={conversation}
                    selected={selectedConversationId === conversation.id}
                    onSelectConversation={onSelectConversation}
                    onRenameConversation={onRenameConversation}
                    onArchiveConversation={onArchiveConversation}
                    onRestoreConversation={onRestoreConversation}
                    onDeleteConversation={onDeleteConversation}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>

      {hasMore ? (
        <div className="border-t border-ink/8 p-4">
          <button
            type="button"
            onClick={() => void onLoadMore()}
            className="w-full rounded-full border border-ink/10 bg-paper px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-tide/35 hover:bg-white"
          >
            Load more
          </button>
        </div>
      ) : null}
    </aside>
  );
}
