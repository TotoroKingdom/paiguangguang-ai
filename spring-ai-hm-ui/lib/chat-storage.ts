import { mockConversations } from "@/lib/mock-data";
import type { Conversation, Message } from "@/types/chat";

const CHAT_STORAGE_KEY = "spring-ai-hm-ui:conversations";
const NEW_CONVERSATION_TITLE = "New chat";

export function createConversation(messages: Message[] = []): Conversation {
  return refreshConversationSummary({
    id: `conv-${crypto.randomUUID()}`,
    messages,
    preview: "No messages yet",
    title: NEW_CONVERSATION_TITLE,
    updatedAt: "Just now",
  });
}

export function createInitialConversations() {
  return mockConversations.map((conversation) => ({ ...conversation }));
}

export function getConversationTitle(prompt: string) {
  const compactPrompt = prompt.replace(/\s+/g, " ").trim();

  if (!compactPrompt) {
    return NEW_CONVERSATION_TITLE;
  }

  return compactPrompt.length > 42
    ? `${compactPrompt.slice(0, 42).trim()}...`
    : compactPrompt;
}

export function loadConversations() {
  if (typeof window === "undefined") {
    return createInitialConversations();
  }

  try {
    const storedValue = window.localStorage.getItem(CHAT_STORAGE_KEY);

    if (!storedValue) {
      return createInitialConversations();
    }

    const parsedValue = JSON.parse(storedValue) as unknown;

    if (!Array.isArray(parsedValue)) {
      return createInitialConversations();
    }

    const conversations = parsedValue
      .filter(isStoredConversation)
      .map((conversation) => refreshConversationSummary(conversation));

    return conversations.length > 0 ? conversations : createInitialConversations();
  } catch {
    return createInitialConversations();
  }
}

export function saveConversations(conversations: Conversation[]) {
  window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(conversations));
}

export function refreshConversationSummary(
  conversation: Conversation,
  options: { renameFromFirstUser?: boolean } = {},
) {
  const lastMessage = [...conversation.messages]
    .reverse()
    .find((message) => message.content.trim());
  const firstUserMessage = conversation.messages.find(
    (message) => message.role === "user",
  );

  return {
    ...conversation,
    preview: lastMessage?.content.trim().replace(/\s+/g, " ").slice(0, 72) ||
      "No messages yet",
    title:
      options.renameFromFirstUser && firstUserMessage
        ? getConversationTitle(firstUserMessage.content)
        : conversation.title,
    updatedAt: "Just now",
  };
}

function isStoredConversation(value: unknown): value is Conversation {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<Conversation>;

  return (
    typeof candidate.id === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.preview === "string" &&
    typeof candidate.updatedAt === "string" &&
    Array.isArray(candidate.messages)
  );
}
