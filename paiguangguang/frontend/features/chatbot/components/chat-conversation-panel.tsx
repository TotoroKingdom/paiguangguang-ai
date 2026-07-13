"use client";

import { useMemo } from "react";

import type { ConversationData, ConversationStatus } from "../types/conversation";
import { ChatComposer } from "./chat-composer";
import { MessageList } from "./message-list";
import { useMessages } from "../hooks/use-messages";

type ActiveGeneration = {
  assistant_message_id: string;
  status: string;
  started_at: string | null;
} | null;

type ChatConversationPanelProps = {
  token: string | null;
  conversation: ConversationData | null;
  activeGeneration?: ActiveGeneration;
};

function statusLabel(status: ConversationStatus | null) {
  if (!status) {
    return "unknown";
  }
  return status;
}

export function ChatConversationPanel({
  token,
  conversation,
  activeGeneration = null,
}: ChatConversationPanelProps) {
  const conversationId = conversation?.id ?? null;
  const conversationStatus = conversation?.status ?? "deleted";
  const messages = useMessages({
    token,
    conversationId,
    conversationStatus,
    pageSize: 50,
  });

  const headerTitle = useMemo(() => conversation?.title ?? "No conversation selected", [conversation?.title]);

  if (!conversation) {
    return (
      <section className="flex h-full min-h-[32rem] flex-col rounded-2xl border border-ink/10 bg-white/80 p-6 shadow-sm">
        <div className="border-b border-ink/10 pb-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-clay">Chat workspace</p>
          <h2 className="mt-2 text-2xl font-semibold text-ink">Select a conversation</h2>
        </div>
        <div className="flex flex-1 items-center justify-center text-sm leading-7 text-ink/60">
          Pick a conversation from the sidebar to load history and continue the thread.
        </div>
      </section>
    );
  }

  const canSend = conversation.status === "active";
  const showStreamingStop = messages.streamPhase === "streaming";

  return (
    <section className="flex h-full min-h-[32rem] flex-col gap-4">
      <div className="rounded-2xl border border-ink/10 bg-white/80 p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Chat workspace</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">{headerTitle}</h2>
            <p className="mt-2 text-sm leading-6 text-ink/60">
              Model {conversation.model} · Status {statusLabel(conversation.status)}
            </p>
            {activeGeneration ? (
              <p className="mt-2 text-sm leading-6 text-tide">
                Active generation {activeGeneration.status}
                {activeGeneration.started_at ? ` · started ${activeGeneration.started_at}` : ""}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-wide text-ink/50">
            <span className="border border-ink/10 bg-paper px-3 py-1.5">
              Messages {messages.messages.length}
            </span>
            <span className="border border-ink/10 bg-paper px-3 py-1.5">
              Stream {messages.streamPhase}
            </span>
          </div>
        </div>
        {messages.streamError ? (
          <p className="mt-3 rounded-xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm leading-6 text-ink">
            {messages.streamError}
          </p>
        ) : null}
        {messages.controlError ? (
          <p className="mt-3 rounded-xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm leading-6 text-ink">
            {messages.controlError}
          </p>
        ) : null}
      </div>

      <div className="grid min-h-0 flex-1 gap-4 xl:grid-rows-[minmax(0,1fr)_auto]">
        <MessageList
          messages={messages.messages}
          loadingHistory={messages.loadingHistory}
          historyError={messages.historyError}
          hasMore={messages.hasMore}
          onLoadMore={() => void messages.loadMore()}
          streamPhase={messages.streamPhase}
          streamingMessageId={messages.streamingMessageId}
          onStopGeneration={(messageId) => void messages.stopGeneration(messageId)}
          onRetryMessage={(messageId) => void messages.retryMessage(messageId)}
          onRegenerateMessage={(messageId) => void messages.regenerateMessage(messageId)}
          stoppingMessageId={messages.stoppingMessageId}
          actionsDisabled={messages.sending}
        />

        <ChatComposer
          value={messages.draft}
          disabled={!canSend}
          sending={messages.sending}
          error={conversation.status !== "active" ? "Only active conversations can send new messages." : messages.streamError}
          onChange={messages.setDraft}
          onSubmit={(content) => void messages.sendMessage(content)}
          onStop={
            showStreamingStop ? () => void messages.stopGeneration(messages.streamingMessageId) : undefined
          }
          stopping={messages.stoppingMessageId === messages.streamingMessageId && showStreamingStop}
        />
      </div>
    </section>
  );
}
