"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth-provider";

import { chatbotApiClient } from "../api/client";
import { ChatConversationPanel } from "./chat-conversation-panel";
import { ConversationSidebar } from "./conversation-sidebar";
import { ChatbotStoreProvider } from "../stores/chatbot-store";
import { useConversations } from "../hooks/use-conversations";
import { MemoryPanel } from "./memory-panel";

function ChatbotShellContent() {
  const { token } = useAuth();
  const [view, setView] = useState<"chat" | "memories">("chat");
  const conversations = useConversations({
    token,
    client: chatbotApiClient,
    pageSize: 20,
  });

  return (
    <div>
      <div className="mb-4 flex gap-2">
        <button type="button" aria-pressed={view === "chat"} onClick={() => setView("chat")}>
          Chat
        </button>
        <button
          type="button"
          aria-pressed={view === "memories"}
          onClick={() => setView("memories")}
        >
          Memories
        </button>
      </div>
      {view === "memories" ? (
        <MemoryPanel token={token} />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
      <ConversationSidebar
        selectedStatus={conversations.selectedStatus}
        selectedConversationId={conversations.selectedConversationId}
        conversations={conversations.conversations}
        loading={conversations.loading}
        error={conversations.error}
        hasMore={conversations.hasMore}
        onChangeStatus={(status) => void conversations.selectStatus(status)}
        onSelectConversation={(conversationId) => void conversations.selectConversation(conversationId)}
        onLoadMore={() => void conversations.loadMore()}
        onCreateConversation={() => void conversations.createConversation()}
        onRenameConversation={(conversation) => void conversations.renameConversation(conversation)}
        onArchiveConversation={(conversation) => void conversations.archiveConversation(conversation)}
        onRestoreConversation={(conversation) => void conversations.restoreConversation(conversation)}
        onDeleteConversation={(conversation) => void conversations.deleteConversation(conversation)}
        onRefresh={() => void conversations.refreshCurrentStatus()}
      />

      <ChatConversationPanel
        token={token}
        conversation={conversations.selectedConversation}
        activeGeneration={conversations.selectedConversationDetail?.active_generation ?? null}
      />
        </div>
      )}
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
