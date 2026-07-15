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
    <div className="border-t border-ink/8 bg-white/55 px-4 py-3">
      <div className="flex flex-wrap gap-2">
        <Link
          href="/"
          onClick={onClose}
          className="rounded-full border border-ink/10 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/40 hover:bg-paper"
        >
          Home
        </Link>
        <button
          type="button"
          onClick={() => {
            onClose();
            logout();
          }}
          className="rounded-full border border-ink/10 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/40 hover:bg-paper"
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
      <aside className="hidden h-full min-h-0 w-[320px] shrink-0 border-r border-ink/10 bg-[rgb(var(--color-background))] lg:flex">
        <SidebarContent {...props} onClose={onClose} />
      </aside>

      {open ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Close conversations"
            className="absolute inset-0 bg-black/28"
            onClick={onClose}
          />
          <aside className="absolute left-0 top-0 z-10 h-full w-[min(88vw,340px)] border-r border-ink/10 bg-[rgb(var(--color-background))] shadow-[0_20px_50px_rgba(15,23,42,0.18)]">
            <SidebarContent {...props} onClose={onClose} />
          </aside>
        </div>
      ) : null}
    </>
  );
}
