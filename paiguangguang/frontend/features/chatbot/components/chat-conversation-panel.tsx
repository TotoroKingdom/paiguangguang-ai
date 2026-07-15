"use client";

import { useMemo } from "react";

import type { ConversationData, ConversationStatus } from "../types/conversation";
import { ChatbotMark } from "./chatbot-mark";
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
  const conversationStatus = conversation?.status ?? "active";
  const messages = useMessages({
    token,
    conversationId,
    conversationStatus,
    pageSize: 50,
  });

  const headerTitle = useMemo(() => conversation?.title ?? "No conversation selected", [conversation?.title]);

  if (!conversation) {
    return (
      <section className="flex h-full min-h-0 flex-col">
        <div className="flex flex-1 items-center justify-center px-4 py-10">
          <div className="w-full max-w-3xl text-center">
            <ChatbotMark className="mx-auto h-14 w-14 text-tide" />
            <h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-ink sm:text-4xl">
              使用暖心助手开始对话
            </h2>
            <p className="mt-3 text-sm leading-7 text-ink/45">
              从左侧选择一个会话，或点击“开启新对话”创建新的对话。
            </p>
          </div>
        </div>

        <div className="mx-auto w-full max-w-[68rem] px-4 pb-4 lg:px-6">
          <ChatComposer
            value={messages.draft}
            disabled={true}
            sending={false}
            error={null}
            model={null}
            onChange={messages.setDraft}
            onSubmit={(content) => void messages.sendMessage(content)}
          />
        </div>
      </section>
    );
  }

  const canSend = conversation.status === "active";
  const showStreamingStop = messages.streamPhase === "streaming";

  return (
    <section className="flex h-full min-h-0 flex-col">
      <div className="mx-auto flex w-full max-w-[68rem] min-h-0 flex-1 flex-col px-4 py-4 lg:px-6">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-[18px] font-semibold tracking-[-0.02em] text-ink">
              {headerTitle}
            </h2>
            <p className="mt-1 text-sm text-ink/45">Status {statusLabel(conversation.status)}</p>
            {activeGeneration ? (
              <p className="mt-2 text-sm leading-6 text-tide">
                Active generation {activeGeneration.status}
                {activeGeneration.started_at ? ` · started ${activeGeneration.started_at}` : ""}
              </p>
            ) : null}
          </div>

        </div>

        {messages.streamError ? (
          <p className="mb-3 rounded-2xl border border-clay/20 bg-clay/8 px-4 py-3 text-sm leading-6 text-ink">
            {messages.streamError}
          </p>
        ) : null}
        {messages.controlError ? (
          <p className="mb-3 rounded-2xl border border-clay/20 bg-clay/8 px-4 py-3 text-sm leading-6 text-ink">
            {messages.controlError}
          </p>
        ) : null}

        <div className="min-h-0 flex-1">
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
        </div>

        <div className="pt-4">
          <ChatComposer
            value={messages.draft}
            disabled={!canSend}
            sending={messages.sending}
            error={conversation.status !== "active" ? "Only active conversations can send new messages." : messages.streamError}
            model={conversation.model}
            onChange={messages.setDraft}
            onSubmit={(content) => void messages.sendMessage(content)}
            onStop={
              showStreamingStop ? () => void messages.stopGeneration(messages.streamingMessageId) : undefined
            }
            stopping={messages.stoppingMessageId === messages.streamingMessageId && showStreamingStop}
          />
        </div>
      </div>
    </section>
  );
}
