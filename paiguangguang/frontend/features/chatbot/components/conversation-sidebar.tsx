"use client";

import type {
  ConversationData,
  ConversationStatus,
} from "../types/conversation";

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
  deleted: "Trash",
};

function formatTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown time";
  }
  return date.toLocaleString();
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
  return (
    <aside className="flex h-full flex-col border border-ink/10 bg-white/80 shadow-sm">
      <div className="border-b border-ink/10 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Conversations</p>
            <h2 className="mt-1 text-lg font-semibold text-ink">Chatbot sidebar</h2>
          </div>
          <button
            type="button"
            onClick={() => void onCreateConversation()}
            className="border border-tide/40 bg-tide px-3 py-2 text-sm font-semibold text-paper transition hover:bg-tide/90"
          >
            New chat
          </button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {(Object.keys(STATUS_LABELS) as ConversationStatus[]).map((status) => (
            <button
              key={status}
              type="button"
              aria-pressed={selectedStatus === status}
              onClick={() => void onChangeStatus(status)}
              className={[
                "border px-3 py-2 text-sm font-medium transition",
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

      <div className="flex items-center justify-between gap-3 border-b border-ink/10 px-4 py-3">
        <div className="text-xs font-medium uppercase tracking-wide text-ink/50">
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

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {error ? (
          <div className="m-2 border border-clay/30 bg-clay/10 p-4 text-sm text-ink">
            <p className="font-semibold text-clay">Unable to load conversations</p>
            <p className="mt-2 leading-6">{error}</p>
            <button
              type="button"
              onClick={() => void onRefresh()}
              className="mt-3 border border-clay/30 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-paper"
            >
              Retry
            </button>
          </div>
        ) : null}

        {!error && !loading && conversations.length === 0 ? (
          <div className="m-2 border border-dashed border-ink/15 bg-paper/55 p-5 text-sm leading-7 text-ink/65">
            <p className="font-semibold text-ink">No conversations yet</p>
            <p className="mt-2">Create a new conversation to start a session.</p>
          </div>
        ) : null}

        {conversations.map((conversation) => {
          const isSelected = selectedConversationId === conversation.id;
          const isDeleted = conversation.status === "deleted";
          return (
            <article
              key={conversation.id}
              className={[
                "m-2 border p-3 transition",
                isSelected
                  ? "border-tide/45 bg-tide/5 shadow-sm"
                  : "border-ink/10 bg-white hover:border-tide/30",
              ].join(" ")}
            >
              <button
                type="button"
                onClick={() => void onSelectConversation(conversation.id)}
                className="block w-full text-left"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="truncate text-sm font-semibold text-ink">{conversation.title}</h3>
                    <p className="mt-1 text-xs text-ink/55">{conversation.model}</p>
                  </div>
                  <span className="shrink-0 border border-ink/10 bg-paper px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-ink/60">
                    {conversation.status}
                  </span>
                </div>
                <p className="mt-3 line-clamp-2 text-sm leading-6 text-ink/70">
                  Last updated {formatTimestamp(conversation.last_message_at)}
                </p>
              </button>

              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void onRenameConversation(conversation)}
                  className="border border-ink/10 bg-paper px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-tide/40 hover:bg-white"
                >
                  Rename
                </button>
                {conversation.status === "active" ? (
                  <button
                    type="button"
                    onClick={() => void onArchiveConversation(conversation)}
                    className="border border-ink/10 bg-paper px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-tide/40 hover:bg-white"
                  >
                    Archive
                  </button>
                ) : null}
                {conversation.status === "archived" || conversation.status === "deleted" ? (
                  <button
                    type="button"
                    onClick={() => void onRestoreConversation(conversation)}
                    className="border border-ink/10 bg-paper px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-tide/40 hover:bg-white"
                  >
                    Restore
                  </button>
                ) : null}
                {!isDeleted ? (
                  <button
                    type="button"
                    onClick={() => void onDeleteConversation(conversation)}
                    className="border border-clay/20 bg-clay/5 px-3 py-1.5 text-xs font-semibold text-clay transition hover:border-clay/40 hover:bg-clay/10"
                  >
                    Delete
                  </button>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>

      {hasMore ? (
        <div className="border-t border-ink/10 p-4">
          <button
            type="button"
            onClick={() => void onLoadMore()}
            className="w-full border border-ink/10 bg-paper px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-tide/35 hover:bg-white"
          >
            Load more
          </button>
        </div>
      ) : null}
    </aside>
  );
}

