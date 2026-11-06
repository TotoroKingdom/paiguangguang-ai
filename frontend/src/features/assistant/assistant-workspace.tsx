"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useAssistant } from "./provider";
import { AssistantIcon } from "./assistant-icon";
import { AssistantDialog } from "./assistant-dialog";
import { AssistantComposer } from "./assistant-composer";
import type { Conversation } from "./types";

const navigation = [
  { href: "/assistant", name: "新建聊天", icon: "plus" },
  { href: "/assistant/files", name: "文件库", icon: "file" },
  { href: "/assistant/tools", name: "工具 Tool", icon: "tool" },
  { href: "/assistant/skills", name: "技能 Skill", icon: "skill" },
  { href: "/assistant/mcp", name: "连接器 MCP", icon: "mcp" },
  { href: "/assistant/agents", name: "智能体 Agent", icon: "agent" },
];

export function AssistantWorkspace({ children }: { children: ReactNode }) {
  const { state, ready, storageNotice, dispatch, resetDemo, stopGeneration } = useAssistant();
  const pathname = usePathname();
  const router = useRouter();
  const sidebar = useRef<HTMLElement>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [modal, setModal] = useState<"search" | "settings" | "conversation" | null>(null);
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<Conversation | null>(null);
  const [title, setTitle] = useState("");
  const [resetConfirm, setResetConfirm] = useState(false);
  useEffect(() => {
    if (ready)
      dispatch({
        type: "ACTIVATE_DRAFT",
        key: pathname.startsWith("/assistant/chat/") ? pathname.split("/").pop()! : "new",
      });
  }, [pathname, ready, dispatch]);
  useEffect(() => {
    if (!mobileOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    const elements = () =>
      Array.from(
        sidebar.current?.querySelectorAll<HTMLElement>("a[href],button:not([disabled])") ?? [],
      ).filter((el) => getComputedStyle(el).display !== "none");
    elements()[0]?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setMobileOpen(false);
      }
      if (event.key === "Tab") {
        const list = elements();
        const first = list[0];
        const last = list[list.length - 1];
        if (!first) return;
        if (!sidebar.current?.contains(document.activeElement)) {
          event.preventDefault();
          first.focus();
        } else if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      if (previous?.isConnected) previous.focus();
    };
  }, [mobileOpen]);
  const activeConversation = state.conversations.find(
    (c) => pathname === `/assistant/chat/${c.id}`,
  );
  const pageName =
    activeConversation?.title ??
    (pathname === "/assistant/tools"
      ? "工具库"
      : pathname === "/assistant/skills"
        ? "技能库"
        : pathname === "/assistant/mcp"
          ? "连接器中心"
          : pathname === "/assistant/agents"
            ? "智能体中心"
            : pathname === "/assistant/files"
              ? "文件库"
              : pathname.startsWith("/assistant/chat/")
                ? "聊天"
                : "新建聊天");
  const editConversation = (conversation: Conversation) => {
    setMobileOpen(false);
    setEditing(conversation);
    setTitle(conversation.title);
    setModal("conversation");
  };
  return (
    <div className={`assistant-app${collapsed ? " assistant-app--collapsed" : ""}`}>
      {mobileOpen && (
        <button
          className="as-sidebar-backdrop"
          aria-label="关闭导航遮罩"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        ref={sidebar}
        role={mobileOpen ? "dialog" : undefined}
        aria-modal={mobileOpen ? true : undefined}
        className={`as-sidebar${mobileOpen ? " as-sidebar--open" : ""}`}
        aria-label="助手侧栏"
      >
        <div className="as-sidebar-brand">
          <Link href="/assistant" className="as-wordmark" aria-label="智能助手首页">
            <span className="as-brand-symbol">
              <AssistantIcon name="spark" size={20} />
            </span>
            <strong className="as-sidebar-label">智能助手</strong>
          </Link>
          <div className="as-sidebar-actions">
            <button
              className="as-icon-button"
              aria-label="搜索聊天"
              onClick={() => {
                setMobileOpen(false);
                setQuery("");
                setModal("search");
              }}
            >
              <AssistantIcon name="search" size={19} />
            </button>
            <button
              className="as-icon-button as-collapse-button"
              aria-label={collapsed ? "展开侧栏" : "收起侧栏"}
              onClick={() => {
                setCollapsed(!collapsed);
                setMobileOpen(false);
              }}
            >
              <AssistantIcon name="chevron" size={18} />
            </button>
            <button
              className="as-icon-button as-mobile-close"
              aria-label="关闭导航"
              onClick={() => setMobileOpen(false)}
            >
              <AssistantIcon name="close" />
            </button>
          </div>
        </div>
        <nav className="as-nav" aria-label="助手导航">
          {navigation.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              title={item.name}
              className={`as-nav-link${pathname === item.href ? " as-nav-link--active" : ""}`}
              aria-current={pathname === item.href ? "page" : undefined}
              onClick={() => {
                setMobileOpen(false);
              }}
            >
              <AssistantIcon name={item.icon} size={21} />
              <span className="as-sidebar-label">{item.name}</span>
            </Link>
          ))}
        </nav>
        <div className="as-recent as-sidebar-label">
          <div className="as-recent-heading">
            <span>最近的聊天</span>
            <span>{state.conversations.length}</span>
          </div>
          <div className="as-recent-list">
            {state.conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`as-recent-row${activeConversation?.id === conversation.id ? " as-recent-row--active" : ""}`}
              >
                <Link
                  href={`/assistant/chat/${conversation.id}`}
                  onClick={() => setMobileOpen(false)}
                >
                  <AssistantIcon name="chat" size={17} />
                  <span>{conversation.title}</span>
                </Link>
                <button
                  className="as-icon-button"
                  aria-label={`管理聊天：${conversation.title}`}
                  onClick={() => editConversation(conversation)}
                >
                  <AssistantIcon name="more" size={17} />
                </button>
              </div>
            ))}
          </div>
        </div>
        <div className="as-sidebar-bottom">
          <Link href="/" className="as-return">
            <AssistantIcon name="arrow" size={17} />
            <span className="as-sidebar-label">返回网站</span>
          </Link>
          <button
            className="as-profile"
            onClick={() => {
              setMobileOpen(false);
              setResetConfirm(false);
              setModal("settings");
            }}
            aria-label="演示设置"
          >
            <span className="as-avatar">派</span>
            <span className="as-sidebar-label">
              <strong>派广广</strong>
              <small>本地演示空间</small>
            </span>
            <AssistantIcon name="settings" size={19} />
          </button>
        </div>
      </aside>
      <div className="as-main">
        <header className="as-topbar">
          <div className="as-topbar-title">
            <button
              className="as-icon-button as-mobile-menu"
              aria-label="打开导航"
              onClick={() => setMobileOpen(true)}
            >
              <AssistantIcon name="menu" />
            </button>
            <span>{pageName}</span>
          </div>
          <div className="as-topbar-end">
            <span className="as-demo-label">
              <i />
              交互原型 · 模拟数据
            </span>
            {activeConversation && (
              <button
                className="as-icon-button"
                aria-label="管理当前聊天"
                onClick={() => editConversation(activeConversation)}
              >
                <AssistantIcon name="more" />
              </button>
            )}
          </div>
        </header>
        {storageNotice && (
          <div role="status" className="as-storage-notice">
            {storageNotice}
          </div>
        )}
        <main className="as-content" id="assistant-main">
          {ready ? (
            children
          ) : (
            <div className="as-loading" role="status">
              正在恢复本地演示空间…
            </div>
          )}
        </main>
        {ready && <AssistantComposer />}
      </div>
      {modal === "search" && (
        <AssistantDialog title="搜索聊天" onClose={() => setModal(null)}>
          <label className="as-field">
            聊天名称
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索最近的聊天…"
            />
          </label>
          <div className="as-dialog-list">
            {state.conversations
              .filter((c) => c.title.toLowerCase().includes(query.toLowerCase()))
              .map((c) => (
                <Link
                  href={`/assistant/chat/${c.id}`}
                  key={c.id}
                  onClick={() => {
                    setModal(null);
                    setMobileOpen(false);
                  }}
                >
                  <AssistantIcon name="chat" size={18} />
                  {c.title}
                  <AssistantIcon name="arrow" size={17} />
                </Link>
              ))}
            {!state.conversations.some((c) =>
              c.title.toLowerCase().includes(query.toLowerCase()),
            ) && <p className="as-muted">没有匹配的聊天。</p>}
          </div>
        </AssistantDialog>
      )}
      {modal === "conversation" && editing && (
        <AssistantDialog title="管理聊天" onClose={() => setModal(null)}>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (title.trim()) {
                dispatch({ type: "RENAME_CONVERSATION", id: editing.id, title: title.trim() });
                setModal(null);
              }
            }}
          >
            <label className="as-field">
              聊天名称
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={80}
                required
              />
            </label>
            <div className="as-dialog-actions">
              <button
                type="button"
                className="as-button as-button--danger"
                onClick={() => {
                  stopGeneration(editing.id);
                  dispatch({ type: "DELETE_CONVERSATION", id: editing.id });
                  if (activeConversation?.id === editing.id) router.push("/assistant");
                  setModal(null);
                }}
              >
                删除这条聊天
              </button>
              <button className="as-button as-button--primary" type="submit">
                保存名称
              </button>
            </div>
            <p className="as-muted">删除后将从当前浏览器移除这条聊天记录。</p>
          </form>
        </AssistantDialog>
      )}
      {modal === "settings" && (
        <AssistantDialog
          title={resetConfirm ? "重置演示数据" : "演示设置"}
          onClose={() => setModal(null)}
        >
          {resetConfirm ? (
            <>
              <p>确认清除本地聊天、个人技能、文件记录、常用项和连接配置，恢复初始样例？</p>
              <div className="as-dialog-actions">
                <button className="as-button" onClick={() => setResetConfirm(false)}>
                  取消
                </button>
                <button
                  className="as-button as-button--danger"
                  onClick={() => {
                    resetDemo();
                    router.push("/assistant");
                    setModal(null);
                  }}
                >
                  确认重置
                </button>
              </div>
            </>
          ) : (
            <>
              <p>
                这是使用模拟数据的前端交互原型。数据仅保存在当前浏览器，工具、技能、连接器和智能体不会执行真实任务。
              </p>
              <p className="as-muted">文件库保存文件元信息；技能导入保存 Markdown 文本。</p>
              <button className="as-button as-button--danger" onClick={() => setResetConfirm(true)}>
                重置演示数据
              </button>
            </>
          )}
        </AssistantDialog>
      )}
    </div>
  );
}
