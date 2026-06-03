"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { PanelLeftOpen } from "lucide-react";

import { ChatComposer } from "@/components/chat/chat-composer";
import { ChatHeader } from "@/components/chat/chat-header";
import { ChatMessages } from "@/components/chat/chat-messages";
import { ChatSidebar } from "@/components/chat/chat-sidebar";
import { Button } from "@/components/ui/button";
import {
  createConversation,
  createInitialConversations,
  loadConversations,
  refreshConversationSummary,
  saveConversations,
} from "@/lib/chat-storage";
import type { Conversation, Message } from "@/types/chat";

type ActiveStream = {
  assistantId: string;
  controller: AbortController;
  conversationId: string;
  prompt: string;
};

const initialConversations = createInitialConversations();

export function ChatLayout() {
  const abortControllerRef = useRef<ActiveStream | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [hasHydratedStorage, setHasHydratedStorage] = useState(false);
  const [conversations, setConversations] =
    useState<Conversation[]>(initialConversations);
  const [activeConversationId, setActiveConversationId] = useState(
    initialConversations[0]?.id ?? "",
  );
  const [isLoading, setIsLoading] = useState(false);

  const activeConversation = useMemo(
    () =>
      conversations.find(
        (conversation) => conversation.id === activeConversationId,
      ) ?? conversations[0],
    [activeConversationId, conversations],
  );
  const messages = activeConversation?.messages ?? [];

  useEffect(() => {
    const storedConversations = loadConversations();
    setConversations(storedConversations);
    setActiveConversationId(storedConversations[0]?.id ?? "");
    setHasHydratedStorage(true);
  }, []);

  useEffect(() => {
    if (hasHydratedStorage) {
      saveConversations(conversations);
    }
  }, [conversations, hasHydratedStorage]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 768px)");
    const syncSidebar = () => setSidebarOpen(mediaQuery.matches);

    syncSidebar();
    mediaQuery.addEventListener("change", syncSidebar);

    return () => mediaQuery.removeEventListener("change", syncSidebar);
  }, []);

  useEffect(() => {
    return () => abortControllerRef.current?.controller.abort();
  }, []);

  function updateConversationMessages(
    conversationId: string,
    updateMessages: (messages: Message[]) => Message[],
    options: { renameFromFirstUser?: boolean } = {},
  ) {
    setConversations((currentConversations) =>
      currentConversations.map((conversation) => {
        if (conversation.id !== conversationId) {
          return conversation;
        }

        return refreshConversationSummary(
          {
            ...conversation,
            messages: updateMessages(conversation.messages),
          },
          options,
        );
      }),
    );
  }

  function updateMessage(
    conversationId: string,
    messageId: string,
    updates: Partial<Message>,
  ) {
    updateConversationMessages(conversationId, (currentMessages) =>
      currentMessages.map((message) =>
        message.id === messageId ? { ...message, ...updates } : message,
      ),
    );
  }

  async function streamAssistantResponse(
    conversationId: string,
    prompt: string,
    assistantId: string,
  ) {
    const abortController = new AbortController();
    abortControllerRef.current = {
      assistantId,
      controller: abortController,
      conversationId,
      prompt,
    };
    setIsLoading(true);

    let streamedContent = "";

    try {
      const response = await fetch(
        `/api/chat/stream?prompt=${encodeURIComponent(prompt)}`,
        {
          cache: "no-store",
          signal: abortController.signal,
        },
      );

      if (!response.ok) {
        const message = await response.text().catch(() => "");
        throw new Error(message || "The chat service returned an error.");
      }

      if (!response.body) {
        throw new Error("The chat service returned an empty stream.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        streamedContent += decoder.decode(value, { stream: true });
        updateMessage(conversationId, assistantId, {
          content: streamedContent,
          status: "streaming",
        });
      }

      const finalChunk = decoder.decode();

      if (finalChunk) {
        streamedContent += finalChunk;
      }

      updateMessage(conversationId, assistantId, {
        content: streamedContent || "The chat service returned no text.",
        status: "complete",
      });
    } catch (error) {
      if (abortController.signal.aborted) {
        updateMessage(conversationId, assistantId, {
          content: streamedContent || "Generation stopped.",
          prompt,
          status: "stopped",
        });
        return;
      }

      const message =
        error instanceof Error
          ? error.message
          : "Something went wrong while streaming the response.";

      updateMessage(conversationId, assistantId, {
        content: message,
        prompt,
        status: "error",
      });
    } finally {
      if (abortControllerRef.current?.controller === abortController) {
        abortControllerRef.current = null;
      }

      setIsLoading(false);
    }
  }

  function handleSend(content: string) {
    if (isLoading) {
      return;
    }

    let conversationId = activeConversation?.id;

    if (!conversationId) {
      const conversation = createConversation();
      conversationId = conversation.id;
      setConversations((current) => [conversation, ...current]);
      setActiveConversationId(conversation.id);
    }

    const currentConversation = conversations.find(
      (conversation) => conversation.id === conversationId,
    );
    const shouldRename = !currentConversation?.messages.some(
      (message) => message.role === "user",
    );
    const userMessage: Message = {
      id: `msg-${crypto.randomUUID()}`,
      role: "user",
      content,
      createdAt: "Just now",
      status: "complete",
    };
    const assistantMessage: Message = {
      id: `msg-${crypto.randomUUID()}`,
      role: "assistant",
      content: "",
      createdAt: "Just now",
      prompt: content,
      status: "streaming",
    };

    updateConversationMessages(
      conversationId,
      (currentMessages) => [...currentMessages, userMessage, assistantMessage],
      { renameFromFirstUser: shouldRename },
    );
    void streamAssistantResponse(conversationId, content, assistantMessage.id);
  }

  function handleRegenerate(prompt: string, assistantId: string) {
    if (!activeConversation || isLoading) {
      return;
    }

    updateMessage(activeConversation.id, assistantId, {
      content: "",
      prompt,
      status: "streaming",
    });
    void streamAssistantResponse(activeConversation.id, prompt, assistantId);
  }

  function handleStopGenerating() {
    abortControllerRef.current?.controller.abort();
  }

  function handleNewChat() {
    handleStopGenerating();

    const conversation = createConversation();
    setConversations((current) => [conversation, ...current]);
    setActiveConversationId(conversation.id);
    setIsLoading(false);
  }

  function handleSelectConversation(conversationId: string) {
    setActiveConversationId(conversationId);
    setSidebarOpen(false);
  }

  return (
    <main className="flex h-dvh overflow-hidden bg-background text-foreground">
      <ChatSidebar
        activeConversationId={activeConversation?.id ?? ""}
        conversations={conversations}
        isOpen={sidebarOpen}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onToggle={() => setSidebarOpen((open) => !open)}
      />

      <section className="flex min-w-0 flex-1 flex-col bg-white">
        <ChatHeader
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((open) => !open)}
        />

        {!sidebarOpen ? (
          <Button
            aria-label="Open sidebar"
            className="fixed left-3 top-3 z-30 hidden border-zinc-200 bg-white text-zinc-700 shadow-lg hover:bg-zinc-50 md:inline-flex"
            size="icon"
            variant="outline"
            onClick={() => setSidebarOpen(true)}
          >
            <PanelLeftOpen />
          </Button>
        ) : null}

        <ChatMessages
          isLoading={isLoading}
          messages={messages}
          onRegenerate={handleRegenerate}
        />
        <ChatComposer
          isLoading={isLoading}
          onSend={handleSend}
          onStop={handleStopGenerating}
        />
      </section>
    </main>
  );
}
