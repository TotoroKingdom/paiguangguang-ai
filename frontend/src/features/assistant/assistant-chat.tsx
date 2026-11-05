"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { useAssistant } from "./provider";
import { capabilityCatalog } from "./data";
import { AssistantIcon } from "./assistant-icon";

const entries = [
  {
    kind: "tool",
    title: "工具 Tool",
    text: "调用工具，完成操作",
    href: "/assistant/tools",
    orbit: "检索 · 计算 · 处理",
  },
  {
    kind: "skill",
    title: "技能 Skill",
    text: "复用成熟的专业流程",
    href: "/assistant/skills",
    orbit: "分析 · 编写 · 审查",
  },
  {
    kind: "mcp",
    title: "连接器 MCP",
    text: "连接外部应用与数据",
    href: "/assistant/mcp",
    orbit: "知识 · 数据 · 协作",
  },
  {
    kind: "agent",
    title: "智能体 Agent",
    text: "自主规划并执行任务",
    href: "/assistant/agents",
    orbit: "规划 · 调用 · 总结",
  },
];
const examples = [
  { label: "搜索 Agent 最新进展", text: "查一下最近一周的 AI Agent 新闻", capabilityId: "tool-1" },
  {
    label: "整理一份产品需求",
    text: "把智能助手的需求整理成可评审的 PRD",
    capabilityId: "skill-2",
  },
  {
    label: "分析知识治理问题",
    text: "梳理最近一周的知识治理问题与改进建议",
    capabilityId: "agent-3",
  },
];
export function AssistantChat({ conversationId }: { conversationId?: string }) {
  const { state, dispatch, retryMessage } = useAssistant();
  const conversation = state.conversations.find((c) => c.id === conversationId);
  const end = useRef<HTMLDivElement>(null);
  const last = conversation?.messages[conversation.messages.length - 1];
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end", behavior: "instant" as ScrollBehavior });
  }, [last?.content, last?.status, conversationId]);
  if (conversationId && !conversation)
    return (
      <section className="as-not-found">
        <AssistantIcon name="chat" size={45} />
        <h1>找不到这条聊天</h1>
        <p>这条记录可能已删除，或属于另一个浏览器。</p>
        <Link className="as-button as-button--primary" href="/assistant">
          开始新聊天
        </Link>
      </section>
    );
  if (!conversation || conversation.messages.length === 0)
    return (
      <section className="as-welcome">
        <div className="as-welcome-kicker">
          <span />
          从一个想法，到一次行动
        </div>
        <h1>今天想做点什么？</h1>
        <p className="as-welcome-description">选择一种能力开始，或直接输入你的问题。</p>
        <div className="as-entry-grid">
          {entries.map((entry) => (
            <Link className={`as-entry as-entry--${entry.kind}`} href={entry.href} key={entry.kind}>
              <div className="as-entry-art">
                <span className="as-art-circle as-art-circle--one" />
                <span className="as-art-circle as-art-circle--two" />
                <span className="as-art-icon">
                  <AssistantIcon name={entry.kind} size={57} />
                </span>
                <span className="as-art-dot">
                  <AssistantIcon name="spark" size={17} />
                </span>
              </div>
              <h2>{entry.title}</h2>
              <p>{entry.text}</p>
              <small>
                {entry.orbit}
                <AssistantIcon name="arrow" size={15} />
              </small>
            </Link>
          ))}
        </div>
        <div className="as-starters">
          <span>试试这些</span>
          {examples.map((example) => (
            <button
              type="button"
              key={example.capabilityId}
              onClick={() => {
                const c = capabilityCatalog.find(
                  (capability) => capability.id === example.capabilityId,
                );
                dispatch({
                  type: "SET_DRAFT",
                  patch: {
                    text: example.text,
                    capability: c ? { id: c.id, kind: c.kind, name: c.name } : null,
                  },
                });
                document.getElementById("assistant-message")?.focus();
              }}
            >
              {example.label}
              <AssistantIcon name="arrow" size={14} />
            </button>
          ))}
        </div>
      </section>
    );
  return (
    <section className="as-chat-thread" aria-label="聊天记录">
      <div className="as-thread-heading">
        <span className="as-section-kicker">LOCAL WORKSPACE / 本地演示</span>
        <h1>{conversation.title}</h1>
      </div>
      {conversation.messages.map((message) => (
        <article
          className={`as-message as-message--${message.role}`}
          aria-label={message.role === "user" ? "用户消息" : "助手消息"}
          key={message.id}
        >
          <div className="as-message-avatar">
            {message.role === "user" ? "派" : <AssistantIcon name="spark" size={19} />}
          </div>
          <div className="as-message-body">
            <div className="as-message-author">
              {message.role === "user" ? "你" : "智能助手"}
              {message.role === "assistant" && <span>模拟回复</span>}
            </div>
            {message.capability && (
              <div className="as-message-capability">
                <AssistantIcon name={message.capability.kind} size={15} />@{message.capability.name}
              </div>
            )}
            {message.attachments && message.attachments.length > 0 && (
              <div className="as-message-attachments">
                {message.attachments.map((file) => (
                  <span key={file.id}>
                    <AssistantIcon name="file" size={15} />
                    {file.name}
                  </span>
                ))}
              </div>
            )}
            {message.steps && message.steps.length > 0 && (
              <details className="as-execution" open>
                <summary>模拟执行过程 · {message.steps.length} 个步骤</summary>
                <ol>
                  {message.steps.map((step, index) => (
                    <li key={`${index}-${step.title}`}>
                      <span>{index + 1}</span>
                      <div>
                        <strong>{step.title}</strong>
                        <p>{step.detail}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              </details>
            )}
            <div className="as-markdown">
              <ReactMarkdown>
                {message.content || (message.status === "generating" ? "正在准备模拟回复…" : "")}
              </ReactMarkdown>
            </div>
            {message.status === "generating" && (
              <p className="as-message-status" role="status">
                <i className="as-pulse" />
                正在模拟生成…
              </p>
            )}
            {message.status === "stopped" && (
              <div className="as-message-status">
                <span>已停止生成</span>
                <button
                  className="as-text-button"
                  disabled={conversation.messages.some((m) => m.status === "generating")}
                  onClick={() => retryMessage(conversation.id, message.id)}
                >
                  <AssistantIcon name="retry" size={15} />
                  重新生成回复
                </button>
              </div>
            )}
            {message.status === "error" && (
              <div className="as-message-error" role="alert">
                <span>模拟生成失败，内容仍保留。</span>
                {message.request?.capability?.kind === "mcp" &&
                  state.connectors.find((c) => c.id === message.request?.capability?.id)?.status !==
                    "connected" && (
                    <Link className="as-button" href="/assistant/mcp">
                      去配置连接器
                    </Link>
                  )}
                <button
                  className="as-button"
                  disabled={conversation.messages.some((m) => m.status === "generating")}
                  onClick={() => retryMessage(conversation.id, message.id)}
                >
                  <AssistantIcon name="retry" size={15} />
                  重试回复
                </button>
              </div>
            )}
          </div>
        </article>
      ))}
      <div ref={end} />
    </section>
  );
}
