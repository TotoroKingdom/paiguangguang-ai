"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { getCapabilities } from "./data";
import { useAssistant } from "./provider";
import { AssistantIcon } from "./assistant-icon";
import { AssistantDialog } from "./assistant-dialog";
import type { CapabilityRef } from "./types";

export function AssistantComposer() {
  const { state, dispatch, sendMessage, stopGeneration, sessionBusy } = useAssistant();
  const router = useRouter();
  const pathname = usePathname();
  const [picker, setPicker] = useState<"capability" | "files" | "scenario" | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [simulateFailure, setSimulateFailure] = useState(false);
  const capabilities = getCapabilities(state);
  const conversation = state.conversations.find((c) => pathname === `/assistant/chat/${c.id}`);
  const generating =
    conversation?.messages.some((message) => message.status === "generating") ?? false;
  const draft = state.draft;
  const textarea = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const input = textarea.current;
    if (!input) return;
    input.style.height = "0px";
    input.style.height = `${Math.min(input.scrollHeight, 200)}px`;
    input.style.overflowY = input.scrollHeight > 200 ? "auto" : "hidden";
  }, [draft.text]);
  const attachments = state.files.filter((file) => draft.fileIds.includes(file.id));
  const match = draft.text.match(/(?:^|\s)@([^\s@]*)$/);
  const suggestions = match
    ? capabilities.filter((c) => c.name.toLowerCase().includes(match[1].toLowerCase())).slice(0, 6)
    : [];
  const selectCapability = (capability: CapabilityRef) => {
    dispatch({
      type: "SET_DRAFT",
      patch: {
        capability: { id: capability.id, name: capability.name, kind: capability.kind },
        ...(match ? { text: draft.text.slice(0, draft.text.lastIndexOf("@")) } : {}),
      },
    });
    setPicker(null);
    setError("");
  };
  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    if (generating || sessionBusy || (!draft.text.trim() && attachments.length === 0)) return;
    if (
      draft.capability?.kind === "mcp" &&
      state.connectors.find((c) => c.id === draft.capability?.id)?.status !== "connected"
    ) {
      setError("该连接器尚未完成模拟连接，请先到连接器中心配置。");
      return;
    }
    void (async () => {
      const id = await sendMessage({
        conversationId: conversation?.id,
        text: draft.text.trim() || "请根据这些附件内容整理要点。",
        capability: draft.capability,
        fileIds: attachments.map((file) => file.id),
        simulateFailure,
      });
      if (!id) return;
      dispatch({ type: "SET_DRAFT", patch: { text: "", capability: null, fileIds: [] } });
      setSimulateFailure(false);
      setError("");
      router.push(`/assistant/chat/${id}`);
    })();
  };
  return (
    <footer className="as-composer-area">
      <form className="as-composer" onSubmit={submit} aria-label="聊天输入区">
        {suggestions.length > 0 && (
          <div className="as-mention-list" role="listbox" aria-label="匹配能力">
            {suggestions.map((capability) => (
              <button
                key={capability.id}
                type="button"
                role="option"
                aria-selected={false}
                onClick={() => selectCapability(capability)}
              >
                <AssistantIcon name={capability.kind} size={18} />
                {capability.name}
                <small>{capability.kind.toUpperCase()}</small>
              </button>
            ))}
          </div>
        )}
        {(draft.capability || attachments.length > 0) && (
          <div className="as-draft-chips">
            {draft.capability && (
              <span className="as-draft-chip as-draft-chip--capability">
                <AssistantIcon name={draft.capability.kind} size={16} />@{draft.capability.name}
                <button
                  type="button"
                  aria-label="移除所选能力"
                  onClick={() => dispatch({ type: "SET_DRAFT", patch: { capability: null } })}
                >
                  <AssistantIcon name="close" size={13} />
                </button>
              </span>
            )}
            {attachments.map((file) => (
              <span className="as-draft-chip" key={file.id}>
                <AssistantIcon name="file" size={14} />
                {file.name}
                <button
                  type="button"
                  aria-label={`移除附件：${file.name}`}
                  onClick={() =>
                    dispatch({
                      type: "SET_DRAFT",
                      patch: { fileIds: draft.fileIds.filter((id) => id !== file.id) },
                    })
                  }
                >
                  <AssistantIcon name="close" size={13} />
                </button>
              </span>
            ))}
          </div>
        )}
        <label className="as-sr-only" htmlFor="assistant-message">
          询问任何问题
        </label>
        <textarea
          ref={textarea}
          id="assistant-message"
          value={draft.text}
          rows={1}
          maxLength={6000}
          placeholder="询问任何问题，或输入 @ 选择能力…"
          onChange={(event) => {
            dispatch({ type: "SET_DRAFT", patch: { text: event.target.value } });
            setError("");
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              submit();
            }
          }}
        />
        <div className="as-composer-toolbar">
          <div className="as-composer-tools">
            <button
              type="button"
              className="as-icon-button as-attach-button"
              aria-label="选择附件"
              onClick={() => setPicker("files")}
            >
              <AssistantIcon name="plus" size={22} />
            </button>
            <button
              type="button"
              className="as-text-button"
              aria-label="选择能力"
              onClick={() => {
                setSearch("");
                setPicker("capability");
              }}
            >
              <span className="as-at">@</span>
              <span>选择能力</span>
            </button>
            <button
              type="button"
              className={`as-text-button as-scenario${simulateFailure ? " as-scenario--failure" : ""}`}
              onClick={() => setPicker("scenario")}
            >
              {simulateFailure ? "失败演示已开启" : "演示场景"}
            </button>
          </div>
          {generating ? (
            <button
              type="button"
              className="as-send-button"
              aria-label="停止生成"
              onClick={() => conversation && stopGeneration(conversation.id)}
            >
              <AssistantIcon name="stop" size={18} />
            </button>
          ) : (
            <button
              type="submit"
              className="as-send-button"
              aria-label="发送消息"
              disabled={sessionBusy || (!draft.text.trim() && attachments.length === 0)}
            >
              <AssistantIcon name="send" size={23} />
            </button>
          )}
        </div>
        {error && (
          <p role="alert" className="as-composer-error">
            {error} <Link href="/assistant/mcp">去配置 →</Link>
          </p>
        )}
      </form>
      <p className="as-composer-caption">回复仍为模拟内容 · 会话保存在服务端并按浏览器隔离</p>
      {picker === "capability" && (
        <AssistantDialog title="选择聊天能力" onClose={() => setPicker(null)}>
          <label className="as-field">
            搜索能力
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索工具、技能、连接器或智能体"
            />
          </label>
          <p className="as-muted">每条消息使用一种能力，可同时附带多个文件。</p>
          <div className="as-capability-picker">
            {capabilities
              .filter((c) => c.name.toLowerCase().includes(search.toLowerCase()))
              .map((c) => (
                <button type="button" key={c.id} onClick={() => selectCapability(c)}>
                  <span className={`as-mini-icon as-tone-${c.kind}`}>
                    <AssistantIcon name={c.kind} />
                  </span>
                  <span>
                    <strong>{c.name}</strong>
                    <small>{c.description}</small>
                  </span>
                  {state.favorites.includes(c.id) && <small>常用</small>}
                </button>
              ))}
            {!capabilities.some((c) => c.name.toLowerCase().includes(search.toLowerCase())) && (
              <p className="as-muted">没有匹配的能力。</p>
            )}
          </div>
        </AssistantDialog>
      )}
      {picker === "files" && (
        <AssistantDialog title="选择聊天附件" onClose={() => setPicker(null)}>
          <p className="as-muted">附件使用元信息进行模拟问答，不读取文件正文。</p>
          <div className="as-file-picker">
            {state.files.map((file) => (
              <label key={file.id}>
                <input
                  type="checkbox"
                  checked={draft.fileIds.includes(file.id)}
                  onChange={() =>
                    dispatch({
                      type: "SET_DRAFT",
                      patch: {
                        fileIds: draft.fileIds.includes(file.id)
                          ? draft.fileIds.filter((id) => id !== file.id)
                          : [...draft.fileIds, file.id],
                      },
                    })
                  }
                />
                <AssistantIcon name="file" size={21} />
                <span>
                  {file.name}
                  <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                </span>
              </label>
            ))}
          </div>
          <div className="as-dialog-actions">
            <Link href="/assistant/files" className="as-button" onClick={() => setPicker(null)}>
              管理文件
            </Link>
            <button className="as-button as-button--primary" onClick={() => setPicker(null)}>
              完成选择
            </button>
          </div>
        </AssistantDialog>
      )}
      {picker === "scenario" && (
        <AssistantDialog title="聊天演示场景" onClose={() => setPicker(null)}>
          <p className="as-muted">选择下一条消息的模拟结果，用于体验失败后的重试。</p>
          <label className="as-radio-row">
            <input
              type="radio"
              name="scenario"
              checked={!simulateFailure}
              onChange={() => setSimulateFailure(false)}
            />
            正常生成
          </label>
          <label className="as-radio-row">
            <input
              type="radio"
              name="scenario"
              checked={simulateFailure}
              onChange={() => setSimulateFailure(true)}
            />
            模拟生成失败
          </label>
          <div className="as-dialog-actions">
            <button className="as-button as-button--primary" onClick={() => setPicker(null)}>
              应用场景
            </button>
          </div>
        </AssistantDialog>
      )}
    </footer>
  );
}
