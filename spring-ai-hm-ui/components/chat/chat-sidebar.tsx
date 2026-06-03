"use client";

import { MessageSquare, PanelLeftClose, Plus, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { Conversation } from "@/types/chat";

type ChatSidebarProps = {
  activeConversationId: string;
  conversations: Conversation[];
  isOpen: boolean;
  onNewChat: () => void;
  onSelectConversation: (conversationId: string) => void;
  onToggle: () => void;
};

export function ChatSidebar({
  activeConversationId,
  conversations,
  isOpen,
  onNewChat,
  onSelectConversation,
  onToggle,
}: ChatSidebarProps) {
  return (
    <>
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-[18rem] flex-col border-r border-zinc-200 bg-[#f9f9f9] transition-transform duration-200 ease-out md:static md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full md:hidden",
        )}
      >
        <div className="flex h-14 items-center gap-2 px-3">
          <Button
            className="flex-1 justify-start border-zinc-200 bg-white text-zinc-900 hover:bg-zinc-100"
            variant="outline"
            onClick={onNewChat}
          >
            <Plus />
            New chat
          </Button>
          <Button
            aria-label="Collapse sidebar"
            className="text-zinc-600 hover:bg-zinc-200 hover:text-zinc-950"
            size="icon"
            variant="ghost"
            onClick={onToggle}
          >
            <PanelLeftClose />
          </Button>
        </div>

        <div className="px-3 pb-3">
          <div className="flex h-9 items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 text-sm text-zinc-500">
            <Search className="size-4 shrink-0" />
            <span className="truncate">Search chats</span>
          </div>
        </div>

        <ScrollArea className="min-h-0 flex-1 px-2 pb-3">
          <div className="space-y-1">
            {conversations.map((conversation) => {
              const isActive = conversation.id === activeConversationId;

              return (
                <button
                  key={conversation.id}
                  className={cn(
                    "group flex w-full items-start gap-3 rounded-md px-3 py-3 text-left text-sm transition-colors",
                    isActive
                      ? "bg-zinc-200 text-zinc-950"
                      : "text-zinc-700 hover:bg-zinc-100 hover:text-zinc-950",
                  )}
                  type="button"
                  onClick={() => onSelectConversation(conversation.id)}
                >
                  <MessageSquare className="mt-0.5 size-4 shrink-0 text-zinc-500 group-hover:text-zinc-700" />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">
                        {conversation.title}
                      </span>
                      <span className="shrink-0 text-xs text-zinc-500">
                        {conversation.updatedAt}
                      </span>
                    </span>
                    <span className="mt-1 block truncate text-xs leading-5 text-zinc-500">
                      {conversation.preview}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </ScrollArea>
      </aside>

      {isOpen ? (
        <button
          aria-label="Close sidebar overlay"
          className="fixed inset-0 z-30 bg-black/60 md:hidden"
          type="button"
          onClick={onToggle}
        />
      ) : null}
    </>
  );
}
