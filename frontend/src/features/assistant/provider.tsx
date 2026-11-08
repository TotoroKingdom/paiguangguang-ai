"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createInitialState, getCapabilities } from "./data";
import {
  AssistantApiError,
  apiMessageToChatMessage,
  createConversation as apiCreateConversation,
  createTurn as apiCreateTurn,
  deleteConversation as apiDeleteConversation,
  getConversation as apiGetConversation,
  listCapabilities as apiListCapabilities,
  listConversations as apiListConversations,
  patchMessage as apiPatchMessage,
  renameConversation as apiRenameConversation,
  cancelRun as apiCancelRun,
  streamRun as apiStreamRun,
  toConversation,
} from "./api";
import { getSession as getAccountSession } from "@/features/auth/api";
import { createMockReply } from "./mock-service";
import {
  demoReducer,
  LOCAL_STORAGE_KEY,
  MIGRATION_STORAGE_KEY,
  restoreLocalState,
  restoreState,
  serializeLocalState,
  STORAGE_KEY,
} from "./store";
import type { ChatMessage, Conversation, DemoAction, DemoState, SendMessageInput } from "./types";

type AssistantContextValue = {
  state: DemoState;
  ready: boolean;
  storageNotice: string | null;
  sessionBusy: boolean;
  dispatch: (action: DemoAction) => void;
  createConversation: () => Promise<string | null>;
  loadConversation: (conversationId: string) => Promise<"loaded" | "missing" | "error">;
  searchConversations: (query: string) => Promise<Conversation[]>;
  renameConversation: (conversationId: string, title: string) => Promise<boolean>;
  deleteConversation: (conversationId: string) => Promise<boolean>;
  sendMessage: (input: SendMessageInput) => Promise<string | null>;
  stopGeneration: (conversationId: string) => void;
  retryMessage: (conversationId: string, messageId?: string) => void;
  resetDemo: () => void;
};
const AssistantContext = createContext<AssistantContextValue | null>(null);
const makeId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const seedIds = new Set(createInitialState().conversations.map((conversation) => conversation.id));

function isNotFoundError(error: unknown): boolean {
  if (typeof error !== "object" || error === null || !("status" in error)) return false;
  return Number(error.status) === 404;
}

function patchFor(message: ChatMessage) {
  return {
    content: message.content,
    status: message.status,
    steps: message.steps ?? [],
    request: message.request ?? null,
  } as const;
}

function legacyRequest(message: ChatMessage, conversationId: string): SendMessageInput {
  return {
    conversationId,
    text: message.request?.text || message.content,
    capability: message.request?.capability ?? message.capability ?? null,
    fileIds: message.request?.fileIds ?? [],
    simulateFailure: false,
  };
}

export function AssistantProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DemoState>(() => createInitialState(false));
  const stateRef = useRef(state);
  const [ready, setReady] = useState(false);
  const [storageNotice, setStorageNotice] = useState<string | null>(null);
  const [sessionBusy, setSessionBusy] = useState(false);
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>());
  const activeRuns = useRef(new Map<string, string>());
  const loading = useRef(new Map<string, Promise<"loaded" | "missing" | "error">>());
  const mounted = useRef(true);

  const dispatch = useCallback((action: DemoAction) => {
    const next = demoReducer(stateRef.current, action);
    stateRef.current = next;
    setState(next);
  }, []);
  const reportError = useCallback((error: unknown, fallback: string) => {
    setStorageNotice(error instanceof AssistantApiError ? error.message : fallback);
  }, []);

  const loadList = useCallback(async () => {
    try {
      const incoming = await apiListConversations();
      const loaded = new Map(stateRef.current.conversations.map((item) => [item.id, item]));
      dispatch({
        type: "SET_CONVERSATIONS",
        conversations: incoming.map((item) => {
          const previous = loaded.get(item.id);
          return previous?.loaded ? { ...item, loaded: true, messages: previous.messages } : item;
        }),
      });
    } catch (error) {
      reportError(error, "无法加载已保存聊天，请检查网络后重试。");
    }
  }, [dispatch, reportError]);

  const loadCatalog = useCallback(async () => {
    try {
      const catalog = await apiListCapabilities();
      dispatch({
        type: "SET_CATALOG",
        catalog: catalog.map((item) => ({
          id: item.id,
          kind: item.kind,
          name: item.name,
          description: item.description,
          category: item.category,
          icon: item.icon,
          source: item.source,
          steps: item.steps,
          tools: item.tools,
          ...(item.content !== null ? { content: item.content } : {}),
          version: item.version,
          versionId: item.versionId,
          executionMode: item.executionMode,
        })),
      });
    } catch (error) {
      reportError(error, "能力目录加载失败，当前显示内置演示目录。");
    }
  }, [dispatch, reportError]);

  const importLegacy = useCallback(
    async (raw: string | null) => {
      let migrationComplete = false;
      try {
        migrationComplete =
          window.localStorage.getItem(MIGRATION_STORAGE_KEY) === "complete";
      } catch {
        migrationComplete = true;
      }
      if (!raw || migrationComplete) return;
      const legacy = restoreState(raw);
      const conversations = legacy.conversations.filter((item) => !seedIds.has(item.id));
      try {
        for (const item of conversations) {
          const remote = await apiCreateConversation(item.title, `legacy:${item.id}`);
          for (let index = 0; index < item.messages.length; index += 1) {
            const user = item.messages[index];
            if (user.role !== "user") continue;
            const assistant = item.messages[index + 1]?.role === "assistant" ? item.messages[index + 1] : null;
            const request = legacyRequest(user, remote.id);
            const turn = await apiCreateTurn(
              remote.id,
              request,
              user.attachments ?? [],
              `legacy:${item.id}:${user.id}`,
            );
            if (assistant) {
              await apiPatchMessage(remote.id, turn.assistantMessage.id, {
                content: assistant.content,
                status: assistant.status === "generating" ? "stopped" : assistant.status,
                steps: assistant.steps ?? [],
              });
            }
          }
        }
        try {
          window.localStorage.setItem(MIGRATION_STORAGE_KEY, "complete");
        } catch {
          /* The in-memory session remains usable when storage is unavailable. */
        }
      } catch (error) {
        reportError(error, "旧浏览器聊天迁移未完成，原始数据仍保留；请重试。");
      }
    },
    [reportError],
  );

  useEffect(() => {
    mounted.current = true;
    let localRaw: string | null = null;
    let legacyRaw: string | null = null;
    try {
      localRaw = window.localStorage.getItem(LOCAL_STORAGE_KEY);
      legacyRaw = window.localStorage.getItem(STORAGE_KEY);
      const restored = restoreLocalState(localRaw ?? legacyRaw);
      stateRef.current = restored;
      setState(restored);
    } catch {
      setStorageNotice("本地配置不可用，当前仅使用内存中的草稿和能力设置。");
    }
    void (async () => {
      await importLegacy(legacyRaw);
      if (mounted.current) await Promise.all([loadList(), loadCatalog()]);
      if (mounted.current) setReady(true);
    })();
    const activeTimers = timers.current;
    return () => {
      mounted.current = false;
      activeTimers.forEach(clearTimeout);
      activeTimers.clear();
    };
  }, [importLegacy, loadCatalog, loadList]);

  useEffect(() => {
    if (!ready) return;
    try {
      window.localStorage.setItem(LOCAL_STORAGE_KEY, serializeLocalState(state));
    } catch {
      setStorageNotice("本地配置不可用，当前仅使用内存中的草稿和能力设置。");
    }
  }, [state, ready]);

  useEffect(() => {
    if (!ready) return;
    const refresh = () => void loadCatalog();
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [loadCatalog, ready]);

  const persistFinal = useCallback(
    async (conversationId: string, messageId: string, message: ChatMessage) => {
      try {
        const saved = await apiPatchMessage(conversationId, messageId, patchFor(message));
        dispatch({
          type: "UPDATE_MESSAGE",
          conversationId,
          messageId,
          patch: apiMessageToChatMessage(saved),
        });
      } catch (error) {
        reportError(error, "回复已生成，但保存失败；请重试。");
        dispatch({
          type: "UPDATE_MESSAGE",
          conversationId,
          messageId,
          patch: { status: "error", error: "最终回复保存失败，请重试。" },
        });
      }
    },
    [dispatch, reportError],
  );

  const stopGeneration = useCallback(
    (conversationId: string) => {
      const runId = activeRuns.current.get(conversationId);
      if (runId) {
        activeRuns.current.delete(conversationId);
        void apiCancelRun(runId);
        const conversation = stateRef.current.conversations.find((item) => item.id === conversationId);
        conversation?.messages
          .filter((message) => message.role === "assistant" && message.status === "generating")
          .forEach((message) =>
            dispatch({
              type: "UPDATE_MESSAGE",
              conversationId,
              messageId: message.id,
              patch: { status: "stopped" },
            }),
          );
        return;
      }
      const timer = timers.current.get(conversationId);
      if (timer) clearTimeout(timer);
      timers.current.delete(conversationId);
      const conversation = stateRef.current.conversations.find((item) => item.id === conversationId);
      conversation?.messages
        .filter((message) => message.role === "assistant" && message.status === "generating")
        .forEach((message) => {
          const stopped = { ...message, status: "stopped" as const };
          dispatch({ type: "UPDATE_MESSAGE", conversationId, messageId: message.id, patch: { status: "stopped" } });
          void persistFinal(conversationId, message.id, stopped);
        });
    },
    [dispatch, persistFinal],
  );

  const start = useCallback(
    (conversationId: string, messageId: string, input: SendMessageInput, notice = "") => {
      const result = createMockReply(input, stateRef.current.files, getCapabilities(stateRef.current));
      const reply = notice ? `${notice}\n\n${result.reply}` : result.reply;
      let index = 0;
      const tick = () => {
        const conversation = stateRef.current.conversations.find((item) => item.id === conversationId);
        const current = conversation?.messages.find((message) => message.id === messageId);
        if (!current) return;
        if (input.simulateFailure && index === 1) {
          const failed = { ...current, content: "模拟生成失败，请重试。", status: "error" as const, steps: result.steps.slice(0, 1) };
          timers.current.delete(conversationId);
          void persistFinal(conversationId, messageId, failed);
          return;
        }
        index += 1;
        const finished = index >= 3;
        const next = {
          ...current,
          content: reply.slice(0, Math.ceil((reply.length * index) / 3)),
          steps: finished ? result.steps : result.steps.slice(0, Math.ceil((result.steps.length * index) / 3)),
          status: (finished ? "complete" : "generating") as ChatMessage["status"],
        };
        if (finished) {
          timers.current.delete(conversationId);
          void persistFinal(conversationId, messageId, next);
        } else {
          dispatch({ type: "UPDATE_MESSAGE", conversationId, messageId, patch: { content: next.content, steps: next.steps, status: next.status } });
          timers.current.set(conversationId, setTimeout(tick, 400));
        }
      };
      timers.current.set(conversationId, setTimeout(tick, 400));
    },
    [dispatch, persistFinal],
  );

  const createConversation = useCallback(async () => {
    try {
      const conversation = await apiCreateConversation();
      dispatch({ type: "CREATE_CONVERSATION", conversation });
      return conversation.id;
    } catch (error) {
      reportError(error, "无法创建聊天，请检查网络后重试。");
      return null;
    }
  }, [dispatch, reportError]);

  const loadConversation = useCallback(async (conversationId: string): Promise<"loaded" | "missing" | "error"> => {
    const current = stateRef.current.conversations.find((item) => item.id === conversationId);
    if (current?.loaded) return "loaded";
    const inFlight = loading.current.get(conversationId);
    if (inFlight) return inFlight;
    const request = (async () => {
      try {
        dispatch({ type: "UPSERT_CONVERSATION", conversation: await apiGetConversation(conversationId) });
        return "loaded" as const;
      } catch (error) {
        reportError(error, "无法加载聊天内容，请刷新后重试。");
        return isNotFoundError(error) ? "missing" as const : "error" as const;
      } finally {
        loading.current.delete(conversationId);
      }
    })();
    loading.current.set(conversationId, request);
    return request;
  }, [dispatch, reportError]);

  const searchConversations = useCallback(async (query: string) => {
    try {
      return await apiListConversations(query);
    } catch (error) {
      reportError(error, "搜索聊天失败，请重试。");
      return [];
    }
  }, [reportError]);

  const renameConversation = useCallback(async (conversationId: string, title: string) => {
    const conversation = stateRef.current.conversations.find((item) => item.id === conversationId);
    if (!conversation) return false;
    try {
      const renamed = await apiRenameConversation(conversationId, title, conversation.version ?? 1);
      dispatch({
        type: "UPSERT_CONVERSATION",
        conversation: { ...renamed, loaded: conversation.loaded, messages: conversation.messages },
      });
      return true;
    } catch (error) {
      reportError(error, "聊天名称保存失败，请刷新后重试。");
      await loadList();
      return false;
    }
  }, [dispatch, loadList, reportError]);

  const deleteConversation = useCallback(async (conversationId: string) => {
    try {
      await apiDeleteConversation(conversationId);
      const timer = timers.current.get(conversationId);
      if (timer) clearTimeout(timer);
      timers.current.delete(conversationId);
      dispatch({ type: "DELETE_CONVERSATION", id: conversationId });
      return true;
    } catch (error) {
      reportError(error, "聊天删除失败，请重试。");
      return false;
    }
  }, [dispatch, reportError]);

  const sendMessage = useCallback(async (input: SendMessageInput) => {
    const existing = input.conversationId
      ? stateRef.current.conversations.find((item) => item.id === input.conversationId)
      : undefined;
    if (existing?.messages.some((message) => message.status === "generating")) return null;
    setSessionBusy(true);
    try {
      const account = await getAccountSession().catch(() => null);
      const canUseReal =
        account?.user.status === "ACTIVE" && account.session.scope === "FULL";
      if (canUseReal) {
        let conversation = existing ?? (await apiCreateConversation());
        if (!existing) dispatch({ type: "CREATE_CONVERSATION", conversation });
        const clientTurnId = input.clientTurnId ?? makeId();
        let assistantId = "";
        await apiStreamRun(
          {
            conversationId: conversation.id,
            clientTurnId,
            text: input.text,
            capability: input.capability ?? null,
            fileIds: input.fileIds,
          },
          (event) => {
            if (event.type === "run") {
              activeRuns.current.set(conversation.id, event.runId);
              return;
            }
            if (event.type === "start") {
              assistantId = event.assistantMessage.id;
              const current = stateRef.current.conversations.find(
                (item) => item.id === conversation.id,
              );
              dispatch({
                type: "UPSERT_CONVERSATION",
                conversation: {
                  ...toConversation(event.conversation),
                  loaded: true,
                  messages: [
                    ...(current?.messages ?? []),
                    apiMessageToChatMessage(event.userMessage),
                    apiMessageToChatMessage(event.assistantMessage),
                  ],
                },
              });
              return;
            }
            if (event.type === "chunk" && assistantId) {
              const current = stateRef.current.conversations.find(
                (item) => item.id === conversation.id,
              );
              const message = current?.messages.find((item) => item.id === assistantId);
              dispatch({
                type: "UPDATE_MESSAGE",
                conversationId: conversation.id,
                messageId: assistantId,
                patch: { content: `${message?.content ?? ""}${event.content}`, status: "generating" },
              });
              return;
            }
            if (event.type === "tool" && assistantId) {
              const current = stateRef.current.conversations.find(
                (item) => item.id === conversation.id,
              );
              const message = current?.messages.find((item) => item.id === assistantId);
              dispatch({
                type: "UPDATE_MESSAGE",
                conversationId: conversation.id,
                messageId: assistantId,
                patch: {
                  steps: [
                    ...(message?.steps ?? []),
                    { title: `工具 ${event.name}`, detail: "服务端只读工具已执行" },
                  ],
                },
              });
              return;
            }
            if (event.type === "done") {
              activeRuns.current.delete(conversation.id);
              const status =
                event.status === "completed"
                  ? "complete"
                  : event.status === "cancelled"
                    ? "stopped"
                    : "error";
              if (assistantId) {
                dispatch({
                  type: "UPDATE_MESSAGE",
                  conversationId: conversation.id,
                  messageId: assistantId,
                  patch: { status },
                });
              }
              return;
            }
            if (event.type === "error") {
              activeRuns.current.delete(conversation.id);
              if (assistantId) {
                dispatch({
                  type: "UPDATE_MESSAGE",
                  conversationId: conversation.id,
                  messageId: assistantId,
                  patch: {
                    status: "error",
                    content: event.message ?? "真实执行失败，请稍后重试。",
                    error: event.code,
                  },
                });
              }
            }
          },
        );
        return conversation.id;
      }
      let conversation = existing ?? (await apiCreateConversation());
      if (!existing) dispatch({ type: "CREATE_CONVERSATION", conversation });
      if (existing && !existing.loaded) {
        conversation = await apiGetConversation(existing.id);
        dispatch({ type: "UPSERT_CONVERSATION", conversation });
      }
      const clientTurnId = input.clientTurnId ?? makeId();
      const request = { ...input, conversationId: conversation.id, clientTurnId };
      const attachments = stateRef.current.files
        .filter((file) => input.fileIds.includes(file.id))
        .map(({ id: fileId, name }) => ({ id: fileId, name }));
      const turn = await apiCreateTurn(conversation.id, request, attachments, clientTurnId);
      const current = stateRef.current.conversations.find((item) => item.id === conversation.id);
      dispatch({
        type: "UPSERT_CONVERSATION",
        conversation: {
          ...toConversation(turn.conversation),
          loaded: true,
          messages: [...(current?.messages ?? []), apiMessageToChatMessage(turn.userMessage), apiMessageToChatMessage(turn.assistantMessage)],
        },
      });
      start(conversation.id, turn.assistantMessage.id, request);
      return conversation.id;
    } catch (error) {
      reportError(error, "消息未保存，请检查网络后重试。");
      return null;
    } finally {
      setSessionBusy(false);
    }
  }, [dispatch, reportError, start]);

  const retryMessage = useCallback((conversationId: string, messageId?: string) => {
    const conversation = stateRef.current.conversations.find((item) => item.id === conversationId);
    if (!conversation || conversation.messages.some((message) => message.status === "generating")) return;
    const message = [...conversation.messages].reverse().find((item) =>
      (messageId === undefined || item.id === messageId) && item.role === "assistant" &&
      (item.status === "error" || item.status === "stopped") && item.request,
    );
    if (!message?.request) return;
    const original = message.request;
    if (original.capability?.kind === "mcp" && !stateRef.current.connectors.some(
      (connector) => connector.id === original.capability?.id && connector.status === "connected",
    )) {
      dispatch({ type: "UPDATE_MESSAGE", conversationId, messageId: message.id, patch: { status: "error", content: "连接器未完成模拟连接，请先配置", steps: [] } });
      return;
    }
    const capability = original.capability && getCapabilities(stateRef.current).find(
      (item) => item.id === original.capability?.id && item.kind === original.capability?.kind,
    );
    const fileIds = original.fileIds.filter((fileId) => stateRef.current.files.some((file) => file.id === fileId));
    const notices = [
      original.capability && !capability ? "原能力已不可用，本次使用普通对话模拟。" : "",
      fileIds.length !== original.fileIds.length ? "部分原附件已删除，本次仅使用仍可用的附件元信息。" : "",
    ].filter(Boolean);
    const request = { ...original, capability: capability ? { id: capability.id, kind: capability.kind, name: capability.name } : null, fileIds, simulateFailure: false };
    const generating = { ...message, content: "", status: "generating" as const, steps: [], request };
    dispatch({ type: "UPDATE_MESSAGE", conversationId, messageId: message.id, patch: { content: "", status: "generating", steps: [], request } });
    void apiPatchMessage(conversationId, message.id, patchFor(generating))
      .then(() => start(conversationId, message.id, request, notices.join(" ")))
      .catch((error) => {
        reportError(error, "无法重新开始生成，请重试。");
        dispatch({ type: "UPDATE_MESSAGE", conversationId, messageId: message.id, patch: { status: "error", error: "重试状态保存失败，请再次重试。" } });
      });
  }, [dispatch, reportError, start]);

  const resetDemo = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current.clear();
    dispatch({ type: "RESET", state: { ...createInitialState(false), conversations: stateRef.current.conversations } });
    void loadList();
  }, [dispatch, loadList]);

  return <AssistantContext.Provider value={{ state, ready, storageNotice, sessionBusy, dispatch, createConversation, loadConversation, searchConversations, renameConversation, deleteConversation, sendMessage, stopGeneration, retryMessage, resetDemo }}>{children}</AssistantContext.Provider>;
}

export function useAssistant(): AssistantContextValue {
  const context = useContext(AssistantContext);
  if (!context) throw new Error("useAssistant must be used within AssistantProvider");
  return context;
}
