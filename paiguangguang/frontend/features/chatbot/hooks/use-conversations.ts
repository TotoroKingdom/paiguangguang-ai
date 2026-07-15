"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ApiError } from "@/lib/api";

import {
  type ChatbotApiClient,
  chatbotApiClient,
} from "../api/client";
import { useChatbotStore, type ChatbotStoreState } from "../stores/chatbot-store";
import type {
  ConversationCreateRequest,
  ConversationData,
  ConversationDetailData,
  ConversationStatus,
} from "../types/conversation";

type LoadOptions = {
  append?: boolean;
  force?: boolean;
};

type UseConversationsOptions = {
  token: string | null;
  client?: ChatbotApiClient;
  pageSize?: number;
};

type StatusFlags = Record<ConversationStatus, boolean>;
type ErrorFlags = Record<ConversationStatus, string | null>;

function createStatusFlags(value: boolean): StatusFlags {
  return {
    active: value,
    archived: value,
  };
}

function createErrorFlags(value: string | null): ErrorFlags {
  return {
    active: value,
    archived: value,
  };
}

function conversationDetailToSummary(detail: ConversationDetailData): ConversationData {
  const { active_generation: _activeGeneration, ...conversation } = detail;
  return conversation;
}

function normalizeErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed";
}

function buildConversationHref(pathname: string, searchParams: URLSearchParams, conversationId: string | null) {
  const params = new URLSearchParams(searchParams.toString());
  if (conversationId) {
    params.set("conversation", conversationId);
  } else {
    params.delete("conversation");
  }
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

function findConversationById(state: ChatbotStoreState, conversationId: string) {
  for (const status of ["active", "archived"] as const) {
    const found = state.pages[status].items.find((item) => item.id === conversationId);
    if (found) {
      return found;
    }
  }
  return null;
}

export function useConversations({ token, client = chatbotApiClient, pageSize = 20 }: UseConversationsOptions) {
  const { state, dispatch } = useChatbotStore();
  const router = useRouter();
  const pathname = usePathname() || "/chat-bot";
  const searchParams = useSearchParams();
  const urlConversationId = searchParams.get("conversation");

  const [loading, setLoading] = useState<StatusFlags>(createStatusFlags(false));
  const [errors, setErrors] = useState<ErrorFlags>(createErrorFlags(null));
  const [selectedConversationDetail, setSelectedConversationDetail] = useState<ConversationDetailData | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const allowAutoSelectRef = useRef(true);
  const detailRequestVersionRef = useRef(0);

  const setStatusLoading = useCallback((status: ConversationStatus, next: boolean) => {
    setLoading((current) => ({ ...current, [status]: next }));
  }, []);

  const setStatusError = useCallback((status: ConversationStatus, message: string | null) => {
    setErrors((current) => ({ ...current, [status]: message }));
  }, []);

  const clearUrl = useCallback(() => {
    router.replace(pathname);
  }, [pathname, router]);

  const pushUrl = useCallback(
    (conversationId: string | null) => {
      router.push(buildConversationHref(pathname, new URLSearchParams(searchParams.toString()), conversationId));
    },
    [pathname, router, searchParams]
  );

  useEffect(() => {
    detailRequestVersionRef.current += 1;
    setDetailLoading(false);
    setDetailError(null);
  }, [token]);

  useEffect(() => {
    return () => {
      detailRequestVersionRef.current += 1;
    };
  }, []);

  const loadPage = useCallback(
    async (status: ConversationStatus, options: LoadOptions = {}) => {
      if (!token) {
        return null;
      }

      const page = state.pages[status];
      if (!options.force && !options.append && page.loaded) {
        return page;
      }

      setStatusLoading(status, true);
      setStatusError(status, null);
      try {
        const pageData = await client.listConversations({
          token,
          status,
          cursor: options.append ? page.nextCursor : null,
          limit: pageSize,
        });
        dispatch({
          type: options.append ? "append_page" : "replace_page",
          status,
          page: {
            items: pageData.items,
            nextCursor: pageData.next_cursor,
            hasMore: pageData.has_more,
            loaded: true,
          },
        });
        return pageData;
      } catch (error) {
        setStatusError(status, normalizeErrorMessage(error));
        return null;
      } finally {
        setStatusLoading(status, false);
      }
    },
    [dispatch, pageSize, setStatusError, setStatusLoading, state.pages, token]
  );

  const openConversation = useCallback(
    async (conversationId: string, options: { syncUrl?: boolean } = {}) => {
      if (!token) {
        return null;
      }
      allowAutoSelectRef.current = true;
      const requestVersion = detailRequestVersionRef.current + 1;
      detailRequestVersionRef.current = requestVersion;
      const ownsRequest = () => detailRequestVersionRef.current === requestVersion;

      setDetailLoading(true);
      setDetailError(null);
      try {
        const detail = await client.getConversation({ token, conversationId });
        if (!ownsRequest()) {
          return null;
        }
        const summary = conversationDetailToSummary(detail);
        dispatch({ type: "upsert_conversation", conversation: summary });
        dispatch({ type: "set_selected_status", status: summary.status });
        dispatch({ type: "set_selected_conversation_id", conversationId: summary.id });
        setSelectedConversationDetail(detail);
        if (options.syncUrl !== false) {
          pushUrl(summary.id);
        }
        return detail;
      } catch (error) {
        if (!ownsRequest()) {
          return null;
        }
        if (error instanceof ApiError && error.status === 404) {
          dispatch({ type: "set_selected_conversation_id", conversationId: null });
          dispatch({ type: "set_selected_status", status: "active" });
          setSelectedConversationDetail(null);
          clearUrl();
          return null;
        }
        setDetailError(normalizeErrorMessage(error));
        return null;
      } finally {
        if (ownsRequest()) {
          setDetailLoading(false);
        }
      }
    },
    [clearUrl, dispatch, pushUrl, token]
  );

  const selectStatus = useCallback(
    async (status: ConversationStatus) => {
      dispatch({ type: "set_selected_status", status });
      const page = state.pages[status];
      if (!page.loaded) {
        await loadPage(status, { force: true });
      }
    },
    [dispatch, loadPage, state.pages]
  );

  const createConversation = useCallback(
    async (request: ConversationCreateRequest = {}) => {
      if (!token) {
        return null;
      }

      setDetailLoading(true);
      setDetailError(null);
      try {
        const created = await client.createConversation({ token }, request);
        allowAutoSelectRef.current = true;
        dispatch({ type: "upsert_conversation", conversation: created });
        dispatch({ type: "set_selected_status", status: created.status });
        dispatch({ type: "set_selected_conversation_id", conversationId: created.id });
        setSelectedConversationDetail({
          ...created,
          active_generation: null,
        });
        pushUrl(created.id);
        return created;
      } catch (error) {
        setDetailError(normalizeErrorMessage(error));
        return null;
      } finally {
        setDetailLoading(false);
      }
    },
    [dispatch, pushUrl, token]
  );

  const renameConversation = useCallback(
    async (conversation: ConversationData, nextTitle?: string | null) => {
      if (!token) {
        return null;
      }

      const requestedTitle = nextTitle ?? window.prompt("Rename conversation", conversation.title);
      if (requestedTitle === null) {
        return null;
      }

      const title = requestedTitle.trim();
      if (!title) {
        return null;
      }

      try {
        const updated = await client.updateConversation(
          { token, conversationId: conversation.id },
          { title }
        );
        dispatch({ type: "upsert_conversation", conversation: updated });
        if (state.selectedConversationId === conversation.id && selectedConversationDetail) {
          setSelectedConversationDetail({ ...selectedConversationDetail, ...updated });
        }
        return updated;
      } catch (error) {
        setDetailError(normalizeErrorMessage(error));
        return null;
      }
    },
    [dispatch, selectedConversationDetail, state.selectedConversationId, token]
  );

  const archiveConversation = useCallback(
    async (conversation: ConversationData) => {
      if (!token) {
        return null;
      }

      try {
        const updated = await client.archiveConversation({ token, conversationId: conversation.id });
        dispatch({ type: "upsert_conversation", conversation: updated });
        dispatch({ type: "set_selected_status", status: updated.status });
        dispatch({ type: "set_selected_conversation_id", conversationId: updated.id });
        setSelectedConversationDetail({ ...updated, active_generation: null });
        return updated;
      } catch (error) {
        setDetailError(normalizeErrorMessage(error));
        return null;
      }
    },
    [dispatch, token]
  );

  const restoreConversation = useCallback(
    async (conversation: ConversationData) => {
      if (!token) {
        return null;
      }

      try {
        const updated = await client.restoreConversation({ token, conversationId: conversation.id });
        dispatch({ type: "upsert_conversation", conversation: updated });
        dispatch({ type: "set_selected_status", status: updated.status });
        dispatch({ type: "set_selected_conversation_id", conversationId: updated.id });
        setSelectedConversationDetail({ ...updated, active_generation: null });
        return updated;
      } catch (error) {
        setDetailError(normalizeErrorMessage(error));
        return null;
      }
    },
    [dispatch, token]
  );

  const deleteConversation = useCallback(
    async (conversation: ConversationData) => {
      if (!token) {
        return null;
      }

      const proceed = window.confirm(`Delete conversation "${conversation.title}"?`);
      if (!proceed) {
        return null;
      }

      const wasSelected = state.selectedConversationId === conversation.id;
      const previousStatus = state.selectedStatus;
      const selectedDetailSnapshot =
        wasSelected &&
        selectedConversationDetail &&
        selectedConversationDetail.id === conversation.id
          ? selectedConversationDetail
          : null;

      dispatch({ type: "remove_conversation", conversationId: conversation.id });
      if (wasSelected) {
        allowAutoSelectRef.current = false;
        dispatch({ type: "set_selected_conversation_id", conversationId: null });
        dispatch({ type: "set_selected_status", status: "active" });
        setSelectedConversationDetail(null);
        clearUrl();
      }

      try {
        await client.deleteConversation({ token, conversationId: conversation.id });
        return conversation.id;
      } catch (error) {
        dispatch({ type: "upsert_conversation", conversation });
        if (wasSelected) {
          dispatch({ type: "set_selected_status", status: previousStatus });
          dispatch({ type: "set_selected_conversation_id", conversationId: conversation.id });
          setSelectedConversationDetail(selectedDetailSnapshot);
          pushUrl(conversation.id);
          allowAutoSelectRef.current = true;
        }
        setDetailError(normalizeErrorMessage(error));
        return null;
      }
    },
    [clearUrl, dispatch, pushUrl, selectedConversationDetail, state.selectedConversationId, state.selectedStatus, token]
  );

  const refreshCurrentStatus = useCallback(async () => {
    await loadPage(state.selectedStatus, { force: true });
    if (state.selectedConversationId) {
      await openConversation(state.selectedConversationId, { syncUrl: false });
    }
  }, [loadPage, openConversation, state.selectedConversationId, state.selectedStatus]);

  const loadMore = useCallback(async () => {
    const page = state.pages[state.selectedStatus];
    if (!page.hasMore || !page.nextCursor) {
      return null;
    }
    return loadPage(state.selectedStatus, { append: true, force: true });
  }, [loadPage, state.pages, state.selectedStatus]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const page = state.pages[state.selectedStatus];
    if (!page.loaded && !loading[state.selectedStatus] && !errors[state.selectedStatus]) {
      void loadPage(state.selectedStatus, { force: true });
    }
  }, [errors, loadPage, loading, state.pages, state.selectedStatus, token]);

  useEffect(() => {
    if (!token) {
      return;
    }

    if (urlConversationId && urlConversationId !== state.selectedConversationId) {
      void openConversation(urlConversationId, { syncUrl: false });
      return;
    }

    if (!urlConversationId && !state.selectedConversationId) {
      if (!allowAutoSelectRef.current) {
        return;
      }
      const firstConversation = state.pages[state.selectedStatus].items[0];
      if (firstConversation) {
        void openConversation(firstConversation.id, { syncUrl: true });
      }
    }
  }, [
    openConversation,
    state.pages,
    state.selectedConversationId,
    state.selectedStatus,
    token,
    urlConversationId,
  ]);

  const selectedConversation = useMemo(() => {
    if (selectedConversationDetail) {
      return conversationDetailToSummary(selectedConversationDetail);
    }
    if (state.selectedConversationId) {
      return findConversationById(state, state.selectedConversationId);
    }
    return null;
  }, [selectedConversationDetail, state]);

  return {
    selectedStatus: state.selectedStatus,
    selectedConversationId: state.selectedConversationId,
    selectedConversation,
    conversations: state.pages[state.selectedStatus].items,
    pages: state.pages,
    hasMore: state.pages[state.selectedStatus].hasMore,
    nextCursor: state.pages[state.selectedStatus].nextCursor,
    loading: loading[state.selectedStatus],
    error: errors[state.selectedStatus],
    detailLoading,
    detailError,
    selectedConversationDetail,
    loadPage,
    loadMore,
    selectStatus,
    openConversation,
    selectConversation: openConversation,
    createConversation,
    renameConversation,
    archiveConversation,
    restoreConversation,
    deleteConversation,
    refreshCurrentStatus,
    clearSelection: () => {
      dispatch({ type: "set_selected_conversation_id", conversationId: null });
      setSelectedConversationDetail(null);
      clearUrl();
    },
  };
}
