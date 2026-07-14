"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useMemo,
  useReducer,
  useRef,
  type Dispatch,
  type ReactNode,
} from "react";

import type { ConversationData, ConversationStatus } from "../types/conversation";

export type ConversationPageState = {
  items: ConversationData[];
  nextCursor: string | null;
  hasMore: boolean;
  loaded: boolean;
};

export type ChatbotStoreState = {
  selectedStatus: ConversationStatus;
  selectedConversationId: string | null;
  pages: Record<ConversationStatus, ConversationPageState>;
};

type ChatbotStoreSnapshot = {
  version: 2;
  state: ChatbotStoreState;
};

type ChatbotStoreAction =
  | { type: "hydrate"; state: ChatbotStoreState }
  | { type: "set_selected_status"; status: ConversationStatus }
  | { type: "set_selected_conversation_id"; conversationId: string | null }
  | { type: "replace_page"; status: ConversationStatus; page: ConversationPageState }
  | { type: "append_page"; status: ConversationStatus; page: ConversationPageState }
  | { type: "upsert_conversation"; conversation: ConversationData }
  | { type: "remove_conversation"; conversationId: string }
  | { type: "clear_pages" };

const PAGE_TEMPLATE: ConversationPageState = {
  items: [],
  nextCursor: null,
  hasMore: false,
  loaded: false,
};

export const CONVERSATION_STATUSES: ConversationStatus[] = ["active", "archived"];

export function createInitialChatbotStoreState(): ChatbotStoreState {
  return {
    selectedStatus: "active",
    selectedConversationId: null,
    pages: {
      active: { ...PAGE_TEMPLATE, items: [] },
      archived: { ...PAGE_TEMPLATE, items: [] },
    },
  };
}

function clonePage(page: ConversationPageState): ConversationPageState {
  return {
    items: [...page.items],
    nextCursor: page.nextCursor,
    hasMore: page.hasMore,
    loaded: page.loaded,
  };
}

function cloneState(state: ChatbotStoreState): ChatbotStoreState {
  return {
    selectedStatus: state.selectedStatus,
    selectedConversationId: state.selectedConversationId,
    pages: {
      active: clonePage(state.pages.active),
      archived: clonePage(state.pages.archived),
    },
  };
}

function removeConversationFromPage(page: ConversationPageState, conversationId: string) {
  const items = page.items.filter((item) => item.id !== conversationId);
  return {
    ...page,
    items,
  };
}

function sortByRecency(items: ConversationData[]) {
  return [...items].sort((left, right) => {
    const leftTime = new Date(left.last_message_at).getTime();
    const rightTime = new Date(right.last_message_at).getTime();
    if (leftTime !== rightTime) {
      return rightTime - leftTime;
    }
    return right.id.localeCompare(left.id);
  });
}

function upsertConversation(pages: Record<ConversationStatus, ConversationPageState>, conversation: ConversationData) {
  const nextPages = {
    active: removeConversationFromPage(pages.active, conversation.id),
    archived: removeConversationFromPage(pages.archived, conversation.id),
  };
  const targetPage = nextPages[conversation.status];
  targetPage.items = sortByRecency([conversation, ...targetPage.items]);
  return nextPages;
}

function normalizeSnapshot(snapshot: unknown): ChatbotStoreState | null {
  if (!snapshot || typeof snapshot !== "object") {
    return null;
  }
  const candidate = snapshot as Partial<ChatbotStoreSnapshot>;
  if (candidate.version !== 2 || !candidate.state) {
    return null;
  }
  const state = candidate.state;
  if (!state.pages || !state.selectedStatus) {
    return null;
  }
  return state;
}

function reducer(state: ChatbotStoreState, action: ChatbotStoreAction): ChatbotStoreState {
  switch (action.type) {
    case "hydrate":
      return cloneState(action.state);
    case "set_selected_status":
      return {
        ...state,
        selectedStatus: action.status,
      };
    case "set_selected_conversation_id":
      return {
        ...state,
        selectedConversationId: action.conversationId,
      };
    case "replace_page":
      return {
        ...state,
        pages: {
          ...state.pages,
          [action.status]: {
            ...action.page,
            items: sortByRecency(action.page.items),
          },
        },
      };
    case "append_page": {
      const currentPage = state.pages[action.status];
      const merged = sortByRecency([...currentPage.items, ...action.page.items]);
      return {
        ...state,
        pages: {
          ...state.pages,
          [action.status]: {
            items: merged,
            nextCursor: action.page.nextCursor,
            hasMore: action.page.hasMore,
            loaded: true,
          },
        },
      };
    }
    case "upsert_conversation":
      return {
        ...state,
        pages: upsertConversation(state.pages, action.conversation),
      };
    case "remove_conversation":
      return {
        ...state,
        pages: {
          active: removeConversationFromPage(state.pages.active, action.conversationId),
          archived: removeConversationFromPage(state.pages.archived, action.conversationId),
        },
      };
    case "clear_pages":
      return createInitialChatbotStoreState();
    default:
      return state;
  }
}

type ChatbotStoreValue = {
  state: ChatbotStoreState;
  dispatch: Dispatch<ChatbotStoreAction>;
};

const ChatbotStoreContext = createContext<ChatbotStoreValue | null>(null);

export function ChatbotStoreProvider({
  children,
  storageKey,
}: {
  children: ReactNode;
  storageKey?: string | null;
}) {
  const normalizedStorageKey = storageKey?.trim() || null;
  const previousStorageKey = useRef(normalizedStorageKey);

  useEffect(() => {
    const previous = previousStorageKey.current;
    if (previous && !normalizedStorageKey && typeof window !== "undefined") {
      window.sessionStorage.removeItem(previous);
    }
    previousStorageKey.current = normalizedStorageKey;
  }, [normalizedStorageKey]);

  return (
    <ScopedChatbotStoreProvider key={normalizedStorageKey ?? "logged-out"} storageKey={normalizedStorageKey}>
      {children}
    </ScopedChatbotStoreProvider>
  );
}

function ScopedChatbotStoreProvider({
  children,
  storageKey,
}: {
  children: ReactNode;
  storageKey: string | null;
}) {
  const [state, dispatch] = useReducer(reducer, undefined, createInitialChatbotStoreState);
  const [isHydrated, setIsHydrated] = useState(!storageKey);

  useEffect(() => {
    if (!storageKey || typeof window === "undefined") {
      setIsHydrated(true);
      return;
    }
    const raw = window.sessionStorage.getItem(storageKey);
    if (!raw) {
      setIsHydrated(true);
      return;
    }
    try {
      const snapshot = JSON.parse(raw) as ChatbotStoreSnapshot;
      const normalized = normalizeSnapshot(snapshot);
      if (normalized) {
        dispatch({ type: "hydrate", state: normalized });
      }
    } catch {
      window.sessionStorage.removeItem(storageKey);
    } finally {
      setIsHydrated(true);
    }
  }, [storageKey]);

  useEffect(() => {
    if (!storageKey || typeof window === "undefined" || !isHydrated) {
      return;
    }
    const snapshot: ChatbotStoreSnapshot = {
      version: 2,
      state,
    };
    window.sessionStorage.setItem(storageKey, JSON.stringify(snapshot));
  }, [isHydrated, storageKey, state]);

  const value = useMemo(
    () => ({
      state,
      dispatch,
    }),
    [state]
  );

  if (!isHydrated) {
    return null;
  }

  return <ChatbotStoreContext.Provider value={value}>{children}</ChatbotStoreContext.Provider>;
}

export function useChatbotStore() {
  const context = useContext(ChatbotStoreContext);
  if (!context) {
    throw new Error("useChatbotStore must be used within ChatbotStoreProvider");
  }
  return context;
}
