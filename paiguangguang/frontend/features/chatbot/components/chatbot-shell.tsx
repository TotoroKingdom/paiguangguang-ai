"use client";

import { ChatBotPanel } from "@/features/chat-bot/chat-bot-panel";
import { useAuth } from "@/components/auth-provider";

import { chatbotApiClient } from "../api/client";
import { ConversationSidebar } from "./conversation-sidebar";
import { ChatbotStoreProvider } from "../stores/chatbot-store";
import { useConversations } from "../hooks/use-conversations";

function ChatbotShellContent() {
  const { token, user } = useAuth();
  const conversations = useConversations({
    token,
    client: chatbotApiClient,
    pageSize: 20,
  });

  return (
    <div className="grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
      <ConversationSidebar
        selectedStatus={conversations.selectedStatus}
        selectedConversationId={conversations.selectedConversationId}
        conversations={conversations.conversations}
        loading={conversations.loading}
        error={conversations.error}
        hasMore={conversations.hasMore}
        onChangeStatus={conversations.selectStatus}
        onSelectConversation={conversations.selectConversation}
        onLoadMore={conversations.loadMore}
        onCreateConversation={conversations.createConversation}
        onRenameConversation={conversations.renameConversation}
        onArchiveConversation={conversations.archiveConversation}
        onRestoreConversation={conversations.restoreConversation}
        onDeleteConversation={conversations.deleteConversation}
        onRefresh={conversations.refreshCurrentStatus}
      />

      <div className="space-y-6">
        <section className="border border-ink/10 bg-white/80 p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-clay">Selected session</p>
          <h2 className="mt-2 text-2xl font-semibold text-ink">
            {conversations.selectedConversation?.title ?? "No conversation selected"}
          </h2>
          <div className="mt-3 flex flex-wrap gap-2 text-sm text-ink/65">
            <span className="border border-ink/10 bg-paper px-3 py-1.5">
              Status: {conversations.selectedConversation?.status ?? "unknown"}
            </span>
            <span className="border border-ink/10 bg-paper px-3 py-1.5">
              User: {user?.email ?? "unknown"}
            </span>
            <span className="border border-ink/10 bg-paper px-3 py-1.5">
              Detail: {conversations.detailLoading ? "loading" : "ready"}
            </span>
          </div>
          {conversations.detailError ? (
            <p className="mt-3 text-sm leading-6 text-clay">{conversations.detailError}</p>
          ) : null}
        </section>

        <ChatBotPanel />
      </div>
    </div>
  );
}

export function ChatbotShell() {
  const { user } = useAuth();
  const storageKey = user ? `paiguangguang.chatbot:${user.id}` : "paiguangguang.chatbot:anonymous";

  return (
    <ChatbotStoreProvider storageKey={storageKey}>
      <ChatbotShellContent />
    </ChatbotStoreProvider>
  );
}

