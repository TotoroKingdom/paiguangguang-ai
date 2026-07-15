"use client";

import { useMemo } from "react";

import type { ConversationData, ConversationStatus } from "../types/conversation";
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

const APP_TITLE = "\u804a\u5929\u673a\u5668\u4eba";
const CREATE_CONVERSATION_LABEL = "\u5f00\u542f\u65b0\u5bf9\u8bdd";
const TODAY_LABEL = "\u4eca\u5929";
const YESTERDAY_LABEL = "\u6628\u5929";
const WEEK_LABEL = "7\u5929\u5185";
const OLDER_LABEL = "\u66f4\u65e9";

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
    return { key: "older", label: OLDER_LABEL, order: 3 };
  }

  const diffDays = Math.floor((toStartOfDay(now).getTime() - toStartOfDay(date).getTime()) / 86_400_000);

  if (diffDays <= 0) {
    return { key: "today", label: TODAY_LABEL, order: 0 };
  }

  if (diffDays === 1) {
    return { key: "yesterday", label: YESTERDAY_LABEL, order: 1 };
  }

  if (diffDays <= 7) {
    return { key: "week", label: WEEK_LABEL, order: 2 };
  }

  return { key: "older", label: OLDER_LABEL, order: 3 };
}

function RefreshIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4" fill="none">
      <path
        d="M20 12a8 8 0 1 1-2.4-5.7"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M17.2 4.8v4.2h-4.2"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
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
        "group rounded-[18px] border px-3 py-2.5 transition",
        selected
          ? "border-tide/30 bg-white shadow-[0_1px_2px_rgba(18,24,35,0.04)]"
          : "border-transparent hover:border-[var(--chat-border)] hover:bg-white/80",
      ].join(" ")}
    >
      <button
        type="button"
        onClick={() => void onSelectConversation(conversation.id)}
        className="block w-full text-left"
      >
        <div className="min-w-0">
          <h3 className="truncate text-[15px] font-medium leading-6 text-ink">{conversation.title}</h3>
          <div className="mt-1 flex min-w-0 items-center gap-2 text-[12px] text-ink/45">
            <span className="truncate">{conversation.model}</span>
            <span className="h-1 w-1 shrink-0 rounded-full bg-current opacity-35" />
            <span className="truncate">{formatTimestamp(conversation.last_message_at)}</span>
          </div>
        </div>
      </button>

      <div className="max-h-0 overflow-hidden opacity-0 transition-all duration-150 group-hover:mt-2 group-hover:max-h-16 group-hover:opacity-100 group-focus-within:mt-2 group-focus-within:max-h-16 group-focus-within:opacity-100">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void onRenameConversation(conversation)}
            className="rounded-full border border-[var(--chat-border)] bg-white px-3 py-1.5 text-xs font-medium text-ink/70 transition hover:border-tide/30 hover:text-ink"
          >
            Rename
          </button>
          {conversation.status === "active" ? (
            <button
              type="button"
              onClick={() => void onArchiveConversation(conversation)}
              className="rounded-full border border-[var(--chat-border)] bg-white px-3 py-1.5 text-xs font-medium text-ink/70 transition hover:border-tide/30 hover:text-ink"
            >
              Archive
            </button>
          ) : null}
          {conversation.status === "archived" ? (
            <button
              type="button"
              onClick={() => void onRestoreConversation(conversation)}
              className="rounded-full border border-[var(--chat-border)] bg-white px-3 py-1.5 text-xs font-medium text-ink/70 transition hover:border-tide/30 hover:text-ink"
            >
              Restore
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => void onDeleteConversation(conversation)}
            className="rounded-full border border-clay/20 bg-clay/5 px-3 py-1.5 text-xs font-medium text-clay transition hover:border-clay/35 hover:bg-clay/10"
          >
            Delete
          </button>
        </div>
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
      <div className="border-b border-[var(--chat-border)] px-4 pb-4 pt-4">
        <div className="flex items-center gap-2">
          <ChatbotMark className="h-8 w-8 shrink-0 text-tide" />
          <span className="text-[26px] font-semibold tracking-[-0.05em] text-tide">{APP_TITLE}</span>
        </div>

        <button
          type="button"
          onClick={() => void onCreateConversation()}
          className="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded-full border border-[var(--chat-border)] bg-white px-4 text-sm font-medium text-ink shadow-[0_1px_3px_rgba(18,24,35,0.04)] transition hover:border-tide/25 hover:bg-white"
        >
          <span aria-hidden="true" className="flex h-5 w-5 items-center justify-center rounded-full border border-current text-base leading-none">
            +
          </span>
          {CREATE_CONVERSATION_LABEL}
        </button>

        <div className="mt-4 flex items-center gap-2">
          {(Object.keys(STATUS_LABELS) as ConversationStatus[]).map((status) => (
            <button
              key={status}
              type="button"
              aria-pressed={selectedStatus === status}
              onClick={() => void onChangeStatus(status)}
              className={[
                "rounded-full border px-3 py-2 text-sm font-medium transition",
                status === "archived" ? "ml-auto" : "",
                selectedStatus === status
                  ? "border-tide/55 bg-tide text-paper shadow-sm"
                  : "border-[var(--chat-border)] bg-white/75 text-ink hover:border-tide/35 hover:bg-white",
              ].join(" ")}
            >
              {STATUS_LABELS[status]}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 border-b border-[var(--chat-border)] px-4 py-3">
        <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-ink/45">
          {loading ? "Loading conversations" : `${conversations.length} conversations`}
        </div>
        <button
          type="button"
          onClick={() => void onRefresh()}
          aria-label="Refresh"
          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-[var(--chat-border)] bg-white text-ink/55 transition hover:border-tide/30 hover:text-tide"
        >
          <RefreshIcon />
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
          <div className="m-1 rounded-[18px] border border-dashed border-[var(--chat-border)] bg-white/70 p-5 text-sm leading-7 text-ink/65">
            <p className="font-semibold text-ink">No conversations yet</p>
            <p className="mt-2">Create a new conversation to start a session.</p>
          </div>
        ) : null}

        <div className="space-y-4">
          {sections.map((section) => (
            <section key={section.key}>
              <h3 className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-ink/45">
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
        <div className="border-t border-[var(--chat-border)] p-4">
          <button
            type="button"
            onClick={() => void onLoadMore()}
            className="w-full rounded-full border border-[var(--chat-border)] bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-tide/35 hover:bg-white"
          >
            Load more
          </button>
        </div>
      ) : null}
    </aside>
  );
}
