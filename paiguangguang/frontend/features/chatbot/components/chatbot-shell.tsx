"use client";

import { useCallback, useState } from "react";
import type { ReactNode } from "react";

import { useAuth } from "@/components/auth-provider";

import { chatbotApiClient } from "../api/client";
import { useConversations } from "../hooks/use-conversations";
import { ChatbotStoreProvider } from "../stores/chatbot-store";
import { ChatbotHeader } from "./chatbot-header";
import { ChatbotSidebar } from "./chatbot-sidebar";
import { ChatConversationPanel } from "./chat-conversation-panel";
import { MemoryPanel } from "./memory-panel";

type ChatbotView = "chat" | "memories";

function ChatbotShellFrame({ children }: { children: ReactNode }) {
  return (
    <div
      data-testid="chatbot-shell"
      className="chatbot-theme flex h-full min-h-0 overflow-hidden bg-paper text-ink"
    >
      {children}
    </div>
  );
}

function ChatbotShellSkeleton() {
  return (
    <div
      data-testid="chatbot-shell-skeleton"
      className="flex h-full min-h-0 w-full overflow-hidden"
    >
      <div className="hidden h-full min-h-0 w-[280px] shrink-0 border-r border-ink/10 bg-white/75 lg:block">
        <div className="space-y-3 p-4">
          <div className="h-4 w-28 rounded bg-ink/5" />
          <div className="h-9 rounded-xl bg-ink/5" />
          <div className="h-9 rounded-xl bg-ink/5" />
          <div className="h-9 rounded-xl bg-ink/5" />
          <div className="mt-6 h-4 w-24 rounded bg-ink/5" />
          <div className="h-24 rounded-2xl bg-ink/5" />
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-14 items-center gap-3 border-b border-ink/10 bg-white/80 px-4">
          <div className="h-9 w-9 rounded-lg bg-ink/5 lg:hidden" />
          <div className="min-w-0 flex-1">
            <div className="h-3 w-28 rounded bg-ink/5" />
            <div className="mt-2 h-5 w-40 rounded bg-ink/5" />
          </div>
          <div className="flex gap-2">
            <div className="h-9 w-20 rounded-full bg-ink/5" />
            <div className="h-9 w-24 rounded-full bg-ink/5" />
          </div>
        </div>
        <div className="flex min-h-0 flex-1 items-center justify-center p-6">
          <div className="w-full max-w-3xl space-y-4">
            <div className="h-8 w-44 rounded bg-ink/5" />
            <div className="h-56 rounded-3xl bg-ink/5" />
            <div className="h-32 rounded-3xl bg-ink/5" />
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatbotShellContent() {
  const { token } = useAuth();
  const [view, setView] = useState<ChatbotView>("chat");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const conversations = useConversations({
    token,
    client: chatbotApiClient,
    pageSize: 20,
  });

  const openChatView = useCallback(() => {
    setView("chat");
    setSidebarOpen(false);
  }, []);

  const openMemoriesView = useCallback(() => {
    setView("memories");
    setSidebarOpen(false);
  }, []);

  const openConversation = useCallback(
    async (conversationId: string) => {
      openChatView();
      await conversations.selectConversation(conversationId);
    },
    [conversations, openChatView]
  );

  const changeStatus = useCallback(
    async (status: "active" | "archived") => {
      openChatView();
      await conversations.selectStatus(status);
    },
    [conversations, openChatView]
  );

  const createConversation = useCallback(async () => {
    openChatView();
    await conversations.createConversation();
  }, [conversations, openChatView]);

  const renameConversation = useCallback(
    async (conversation: Parameters<typeof conversations.renameConversation>[0]) => {
      await conversations.renameConversation(conversation);
    },
    [conversations]
  );

  const archiveConversation = useCallback(
    async (conversation: Parameters<typeof conversations.archiveConversation>[0]) => {
      await conversations.archiveConversation(conversation);
    },
    [conversations]
  );

  const restoreConversation = useCallback(
    async (conversation: Parameters<typeof conversations.restoreConversation>[0]) => {
      await conversations.restoreConversation(conversation);
    },
    [conversations]
  );

  const deleteConversation = useCallback(
    async (conversation: Parameters<typeof conversations.deleteConversation>[0]) => {
      await conversations.deleteConversation(conversation);
    },
    [conversations]
  );

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-1 overflow-hidden">
      <ChatbotSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        selectedStatus={conversations.selectedStatus}
        selectedConversationId={conversations.selectedConversationId}
        conversations={conversations.conversations}
        loading={conversations.loading}
        error={conversations.error}
        hasMore={conversations.hasMore}
        onChangeStatus={changeStatus}
        onSelectConversation={openConversation}
        onLoadMore={() => void conversations.loadMore()}
        onCreateConversation={createConversation}
        onRenameConversation={renameConversation}
        onArchiveConversation={archiveConversation}
        onRestoreConversation={restoreConversation}
        onDeleteConversation={deleteConversation}
        onRefresh={() => void conversations.refreshCurrentStatus()}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <ChatbotHeader
          view={view}
          onChangeView={(nextView) => {
            if (nextView === "chat") {
              openChatView();
              return;
            }
            openMemoriesView();
          }}
          onOpenSidebar={() => setSidebarOpen(true)}
        />

        <div className="flex min-h-0 min-w-0 flex-1">
          <div className={view === "chat" ? "flex min-h-0 min-w-0 flex-1 flex-col" : "hidden"}>
            <ChatConversationPanel
              token={token}
              conversation={conversations.selectedConversation}
              activeGeneration={conversations.selectedConversationDetail?.active_generation ?? null}
            />
          </div>

          <div className={view === "memories" ? "flex min-h-0 min-w-0 flex-1 flex-col" : "hidden"}>
            <MemoryPanel token={token} conversationId={conversations.selectedConversation?.id ?? null} />
          </div>
        </div>
      </div>
    </div>
  );
}

export function ChatbotShell() {
  const { user } = useAuth();
  const storageKey = user ? `paiguangguang.chatbot:${user.id}` : null;

  return (
    <ChatbotStoreProvider storageKey={storageKey} fallback={<ChatbotShellFrame><ChatbotShellSkeleton /></ChatbotShellFrame>}>
      <ChatbotShellFrame>
        <ChatbotShellContent />
      </ChatbotShellFrame>
    </ChatbotStoreProvider>
  );
}
