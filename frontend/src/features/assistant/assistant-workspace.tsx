"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useAssistant } from "./provider";
import { AssistantIcon } from "./assistant-icon";
import { AssistantDialog } from "./assistant-dialog";
import { AssistantComposer } from "./assistant-composer";
import type { Conversation } from "./types";
import { AdminApiError, getAdminSession, type AdminUser } from "@/features/admin/api";

const navigation = [
  { href: "/assistant", name: "新建聊天", icon: "plus" },
  { href: "/assistant/files", name: "文件库", icon: "file" },
  { href: "/assistant/tools", name: "工具 Tool", icon: "tool" },
  { href: "/assistant/skills", name: "技能 Skill", icon: "skill" },
  { href: "/assistant/mcp", name: "连接器 MCP", icon: "mcp" },
  { href: "/assistant/agents", name: "智能体 Agent", icon: "agent" },
];

export function AssistantWorkspace({ children }: { children: ReactNode }) {
  const {
    state,
    ready,
    storageNotice,
    createConversation,
    searchConversations,
    renameConversation,
    deleteConversation,
    resetDemo,
    stopGeneration,
    dispatch,
  } = useAssistant();
  const pathname = usePathname();
  const router = useRouter();
  const sidebar = useRef<HTMLElement>(null);
  const accountMenu = useRef<HTMLDivElement>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [adminUser, setAdminUser] = useState<AdminUser | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [modal, setModal] = useState<"search" | "settings" | "conversation" | null>(null);
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<Conversation | null>(null);
  const [title, setTitle] = useState("");
  const [resetConfirm, setResetConfirm] = useState(false);
  const [searchResults, setSearchResults] = useState<Conversation[]>([]);
  useEffect(() => {
    if (modal !== "search") return;
    const timer = window.setTimeout(() => void searchConversations(query).then(setSearchResults), 180);
    return () => window.clearTimeout(timer);
  }, [modal, query, searchConversations]);
  useEffect(() => {
    if (ready)
      dispatch({
        type: "ACTIVATE_DRAFT",
        key: pathname.startsWith("/assistant/chat/") ? pathname.split("/").pop()! : "new",
      });
  }, [pathname, ready, dispatch]);
  useEffect(() => {
    let active = true;
    void getAdminSession()
      .then((session) => {
        if (active) setAdminUser(session.user);
      })
      .catch((error) => {
        if (active && (!(error instanceof AdminApiError) || error.status !== 401)) {
          setAdminUser(null);
        }
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!accountOpen) return;
    const close = (event: MouseEvent) => {
      if (!accountMenu.current?.contains(event.target as Node)) setAccountOpen(false);
    };
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAccountOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", keydown);
    };
  }, [accountOpen]);
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
              onClick={(event) => {
                setMobileOpen(false);
                if (item.href === "/assistant") {
                  event.preventDefault();
                  void (async () => {
                    const conversationId = await createConversation();
                    if (conversationId) router.push(`/assistant/chat/${conversationId}`);
                  })();
                }
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
              <small>服务端会话空间</small>
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
              服务端目录 · 模拟执行
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
            <div className="as-account-menu" ref={accountMenu}>
              <button
                className="as-account-trigger"
                aria-label="账户菜单"
                aria-expanded={accountOpen}
                aria-haspopup="menu"
                onClick={() => setAccountOpen((current) => !current)}
              >
                <span>{adminUser ? adminUser.username.slice(0, 1).toUpperCase() : "派"}</span>
                <AssistantIcon name="chevron" size={14} />
              </button>
              {accountOpen && (
                <div className="as-account-popover" role="menu" aria-label="账户菜单">
                  <div className="as-account-summary">
                    <span className="as-avatar">
                      {adminUser ? adminUser.username.slice(0, 1).toUpperCase() : "派"}
                    </span>
                    <div>
                      <strong>{adminUser ? adminUser.username : "派广广"}</strong>
                      <small>{adminUser ? "管理员身份已登录" : "匿名浏览器会话"}</small>
                    </div>
                  </div>
                  {adminUser && (
                    <Link
                      href="/assistant/admin"
                      role="menuitem"
                      onClick={() => setAccountOpen(false)}
                    >
                      <AssistantIcon name="settings" size={17} />
                      管理控制台
                      <AssistantIcon name="arrow" size={14} />
                    </Link>
                  )}
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setAccountOpen(false);
                      setResetConfirm(false);
                      setModal("settings");
                    }}
                  >
                    <AssistantIcon name="settings" size={17} />
                    演示设置
                  </button>
                  <Link href="/" role="menuitem" onClick={() => setAccountOpen(false)}>
                    <AssistantIcon name="arrow" size={17} />
                    返回网站
                  </Link>
                </div>
              )}
            </div>
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
              正在加载会话空间…
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
            {searchResults.map((c) => (
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
            {searchResults.length === 0 && <p className="as-muted">没有匹配的聊天。</p>}
          </div>
        </AssistantDialog>
      )}
      {modal === "conversation" && editing && (
        <AssistantDialog title="管理聊天" onClose={() => setModal(null)}>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (!title.trim()) return;
              void (async () => {
                const saved = await renameConversation(editing.id, title.trim());
                if (saved) setModal(null);
              })();
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
                  void (async () => {
                    const deleted = await deleteConversation(editing.id);
                    if (deleted) {
                      if (activeConversation?.id === editing.id) router.push("/assistant");
                      setModal(null);
                    }
                  })();
                }}
              >
                删除这条聊天
              </button>
              <button className="as-button as-button--primary" type="submit">
                保存名称
              </button>
            </div>
            <p className="as-muted">删除后将从服务端会话库移除这条聊天记录。</p>
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
              <p>确认清除当前浏览器中的个人技能、文件记录、常用项、连接配置和草稿，恢复初始样例？服务端会话不会被删除。</p>
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
                会话和消息保存在服务端 SQLite 中，并按当前浏览器隔离；这不是登录认证，也不提供跨设备同步。工具、技能、连接器和智能体不会执行真实任务。
              </p>
              <p className="as-muted">文件库、技能、连接器和草稿仍保存在当前浏览器；会话记录保存在服务端。</p>
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
