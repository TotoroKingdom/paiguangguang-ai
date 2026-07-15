"use client";

import Link from "next/link";
import { useEffect } from "react";

import { useAuth } from "@/components/auth-provider";

import type { ConversationData, ConversationStatus } from "../types/conversation";
import { ConversationSidebar } from "./conversation-sidebar";

type ChatbotSidebarProps = {
  open: boolean;
  onClose: () => void;
  selectedStatus: ConversationStatus;
  selectedConversationId: string | null;
  conversations: ConversationData[];
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  onChangeStatus: (status: ConversationStatus) => void | Promise<void>;
  onSelectConversation: (conversationId: string) => void | Promise<void>;
  onLoadMore: () => void | Promise<void>;
  onCreateConversation: () => void | Promise<void>;
  onRenameConversation: (conversation: ConversationData) => void | Promise<void>;
  onArchiveConversation: (conversation: ConversationData) => void | Promise<void>;
  onRestoreConversation: (conversation: ConversationData) => void | Promise<void>;
  onDeleteConversation: (conversation: ConversationData) => void | Promise<void>;
  onRefresh: () => void | Promise<void>;
};

type SidebarContentProps = Omit<ChatbotSidebarProps, "open">;

function SidebarFooter({ onClose }: { onClose: () => void }) {
  const { logout } = useAuth();

  return (
    <div className="border-t border-[var(--chat-border)] bg-white/65 px-4 py-3">
      <div className="flex w-full items-center justify-between gap-2">
        <Link
          href="/"
          onClick={onClose}
          className="inline-flex h-9 items-center rounded-full border border-[var(--chat-border)] bg-white px-4 text-sm font-semibold text-ink/85 shadow-[0_1px_3px_rgba(18,24,35,0.04)] transition hover:border-tide/30 hover:text-ink"
        >
          Home
        </Link>
        <button
          type="button"
          onClick={() => {
            onClose();
            logout();
          }}
          className="inline-flex h-9 items-center rounded-full border border-[var(--chat-border)] bg-white px-4 text-sm font-semibold text-ink/85 shadow-[0_1px_3px_rgba(18,24,35,0.04)] transition hover:border-tide/30 hover:text-ink"
        >
          Logout
        </button>
      </div>
    </div>
  );
}

function SidebarContent({ onClose, ...props }: SidebarContentProps) {
  const wrapAction = <Args extends unknown[]>(action: (...args: Args) => void | Promise<void>) => {
    return async (...args: Args) => {
      onClose();
      await action(...args);
    };
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-transparent">
      <div className="min-h-0 flex-1 overflow-hidden">
        <ConversationSidebar
          {...props}
          onChangeStatus={wrapAction(props.onChangeStatus)}
          onSelectConversation={wrapAction(props.onSelectConversation)}
          onCreateConversation={wrapAction(props.onCreateConversation)}
        />
      </div>
      <SidebarFooter onClose={onClose} />
    </div>
  );
}

export function ChatbotSidebar({ open, onClose, ...props }: ChatbotSidebarProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open]);

  return (
    <>
      <aside className="hidden h-full min-h-0 w-[316px] shrink-0 border-r border-[var(--chat-border)] bg-[var(--chat-sidebar)] lg:flex">
        <SidebarContent {...props} onClose={onClose} />
      </aside>

      {open ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Close conversations"
            className="absolute inset-0 bg-black/14 backdrop-blur-[1px]"
            onClick={onClose}
          />
          <aside className="absolute left-0 top-0 z-10 h-full w-[min(88vw,320px)] border-r border-[var(--chat-border)] bg-[var(--chat-sidebar)] shadow-[0_20px_50px_rgba(18,24,35,0.12)]">
            <SidebarContent {...props} onClose={onClose} />
          </aside>
        </div>
      ) : null}
    </>
  );
}
