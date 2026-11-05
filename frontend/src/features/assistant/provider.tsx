"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createInitialState, getCapabilities } from "./data";
import { createMockReply } from "./mock-service";
import { demoReducer, restoreState, STORAGE_KEY } from "./store";
import type { ChatMessage, DemoAction, DemoState, SendMessageInput } from "./types";

type AssistantContextValue = {
  state: DemoState;
  ready: boolean;
  storageNotice: string | null;
  dispatch: (action: DemoAction) => void;
  sendMessage: (input: SendMessageInput) => string;
  stopGeneration: (conversationId: string) => void;
  retryMessage: (conversationId: string, messageId?: string) => void;
  resetDemo: () => void;
};
const AssistantContext = createContext<AssistantContextValue | null>(null);
const id = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
export function AssistantProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DemoState>(createInitialState);
  const stateRef = useRef(state);
  const [ready, setReady] = useState(false);
  const [storageNotice, setStorageNotice] = useState<string | null>(null);
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>());
  const dispatch = useCallback((action: DemoAction) => {
    const next = demoReducer(stateRef.current, action);
    stateRef.current = next;
    setState(next);
  }, []);
  useEffect(() => {
    try {
      const restored = restoreState(window.localStorage.getItem(STORAGE_KEY));
      stateRef.current = restored;
      setState(restored);
    } catch {
      setStorageNotice("本地存储不可用，当前数据仅保存在内存中。");
    }
    setReady(true);
    const activeTimers = timers.current;
    return () => {
      activeTimers.forEach(clearTimeout);
      activeTimers.clear();
    };
  }, []);
  useEffect(() => {
    if (!ready) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      setStorageNotice("本地存储不可用，当前数据仅保存在内存中。");
    }
  }, [state, ready]);
  const stopGeneration = useCallback(
    (conversationId: string) => {
      const timer = timers.current.get(conversationId);
      if (timer) clearTimeout(timer);
      timers.current.delete(conversationId);
      const conversation = stateRef.current.conversations.find((c) => c.id === conversationId);
      conversation?.messages
        .filter((m) => m.role === "assistant" && m.status === "generating")
        .forEach((m) =>
          dispatch({
            type: "UPDATE_MESSAGE",
            conversationId,
            messageId: m.id,
            patch: { status: "stopped" },
          }),
        );
    },
    [dispatch],
  );
  const start = useCallback(
    (conversationId: string, messageId: string, input: SendMessageInput, notice = "") => {
      const result = createMockReply(
        input,
        stateRef.current.files,
        getCapabilities(stateRef.current),
      );
      const reply = notice ? `${notice}\n\n${result.reply}` : result.reply;
      const { steps } = result;
      let index = 0;
      const tick = () => {
        if (input.simulateFailure && index === 1) {
          dispatch({
            type: "UPDATE_MESSAGE",
            conversationId,
            messageId,
            patch: { status: "error", content: "模拟生成失败，请重试。", steps: steps.slice(0, 1) },
          });
          timers.current.delete(conversationId);
          return;
        }
        index += 1;
        const finished = index >= 3;
        dispatch({
          type: "UPDATE_MESSAGE",
          conversationId,
          messageId,
          patch: {
            content: reply.slice(0, Math.ceil((reply.length * index) / 3)),
            steps: finished ? steps : steps.slice(0, Math.ceil((steps.length * index) / 3)),
            status: finished ? "complete" : "generating",
          },
        });
        if (finished) timers.current.delete(conversationId);
        else timers.current.set(conversationId, setTimeout(tick, 400));
      };
      timers.current.set(conversationId, setTimeout(tick, 400));
    },
    [dispatch],
  );
  const sendMessage = useCallback(
    (input: SendMessageInput): string => {
      const existing =
        input.conversationId &&
        stateRef.current.conversations.some((c) => c.id === input.conversationId);
      const conversationId = existing ? input.conversationId! : id();
      stopGeneration(conversationId);
      if (!existing) {
        const now = new Date().toISOString();
        dispatch({
          type: "CREATE_CONVERSATION",
          conversation: {
            id: conversationId,
            title: input.text.trim().slice(0, 24) || "新对话",
            createdAt: now,
            updatedAt: now,
            messages: [],
          },
        });
      }
      const attachments = stateRef.current.files
        .filter((f) => input.fileIds.includes(f.id))
        .map(({ id: fileId, name }) => ({ id: fileId, name }));
      const request = { ...input, conversationId, fileIds: [...input.fileIds] };
      const assistant: ChatMessage = {
        id: id(),
        role: "assistant",
        content: "",
        status: "generating",
        steps: [],
        request,
      };
      dispatch({
        type: "APPEND_MESSAGES",
        conversationId,
        messages: [
          {
            id: id(),
            role: "user",
            content: input.text,
            status: "complete",
            capability: input.capability ?? null,
            attachments,
          },
          assistant,
        ],
      });
      start(conversationId, assistant.id, request);
      return conversationId;
    },
    [dispatch, start, stopGeneration],
  );
  const retryMessage = useCallback(
    (conversationId: string, messageId?: string) => {
      const conversation = stateRef.current.conversations.find((c) => c.id === conversationId);
      if (conversation?.messages.some((m) => m.status === "generating")) return;
      const message = [...(conversation?.messages ?? [])]
        .reverse()
        .find(
          (m) =>
            (messageId === undefined || m.id === messageId) &&
            m.role === "assistant" &&
            (m.status === "error" || m.status === "stopped") &&
            m.request,
        );
      if (!message?.request) return;
      const original = message.request;
      if (
        original.capability?.kind === "mcp" &&
        !stateRef.current.connectors.some(
          (connector) =>
            connector.id === original.capability?.id && connector.status === "connected",
        )
      ) {
        dispatch({
          type: "UPDATE_MESSAGE",
          conversationId,
          messageId: message.id,
          patch: { status: "error", content: "连接器未完成模拟连接，请先配置", steps: [] },
        });
        return;
      }
      const capability =
        original.capability &&
        getCapabilities(stateRef.current).find(
          (item) => item.id === original.capability?.id && item.kind === original.capability?.kind,
        );
      const fileIds = original.fileIds.filter((fileId) =>
        stateRef.current.files.some((file) => file.id === fileId),
      );
      const notices = [
        original.capability && !capability ? "原能力已不可用，本次使用普通对话模拟。" : "",
        fileIds.length !== original.fileIds.length
          ? "部分原附件已删除，本次仅使用仍可用的附件元信息。"
          : "",
      ].filter(Boolean);
      const request = {
        ...original,
        capability: capability
          ? { id: capability.id, kind: capability.kind, name: capability.name }
          : null,
        fileIds,
        simulateFailure: false,
      };
      dispatch({
        type: "UPDATE_MESSAGE",
        conversationId,
        messageId: message.id,
        patch: { content: "", status: "generating", steps: [] },
      });
      start(conversationId, message.id, request, notices.join(" "));
    },
    [dispatch, start],
  );
  const resetDemo = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current.clear();
    dispatch({ type: "RESET", state: createInitialState() });
  }, [dispatch]);
  return (
    <AssistantContext.Provider
      value={{
        state,
        ready,
        storageNotice,
        dispatch,
        sendMessage,
        stopGeneration,
        retryMessage,
        resetDemo,
      }}
    >
      {children}
    </AssistantContext.Provider>
  );
}
export function useAssistant(): AssistantContextValue {
  const context = useContext(AssistantContext);
  if (!context) throw new Error("useAssistant must be used within AssistantProvider");
  return context;
}
