"use client";

import { PanelLeftOpen, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

type ChatHeaderProps = {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
};

export function ChatHeader({ sidebarOpen, onToggleSidebar }: ChatHeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200 bg-white/95 px-3 backdrop-blur">
      <div className="flex items-center gap-2">
        {!sidebarOpen ? (
          <Button
            aria-label="Open sidebar"
            className="text-zinc-700 hover:bg-zinc-100 hover:text-zinc-950 md:hidden"
            size="icon"
            variant="ghost"
            onClick={onToggleSidebar}
          >
            <PanelLeftOpen />
          </Button>
        ) : null}
        <div className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium text-zinc-950">
          <Sparkles className="size-4 text-emerald-500" />
          GPT Chat
        </div>
      </div>

      <Button
        className="border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-100"
        size="sm"
        variant="outline"
      >
        Streaming
      </Button>
    </header>
  );
}
