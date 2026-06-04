"use client";

import { useEffect, useRef, useState } from "react";
import {
  Bot,
  Loader2,
  RefreshCcw,
  RotateCcw,
  UserRound,
} from "lucide-react";

import { MarkdownMessage } from "@/components/chat/markdown-message";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { Message } from "@/types/chat";

type ChatMessagesProps = {
  isLoading: boolean;
  messages: Message[];
  onRegenerate: (prompt: string, messageId: string) => void;
};

export function ChatMessages({
  isLoading,
  messages,
  onRegenerate,
}: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const threshold = 80;
      const distanceFromBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight;
      setIsAtBottom(distanceFromBottom < threshold);
    };

    container.addEventListener("scroll", handleScroll);
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    if (isAtBottom && bottomRef.current) {
      bottomRef.current.scrollIntoView({
        block: "end",
        behavior: isLoading ? "auto" : "smooth",
      });
    }
  }, [messages, isAtBottom, isLoading]);

  return (
    <ScrollArea ref={scrollContainerRef} className="min-h-0 flex-1">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
        {messages.length === 0 ? (
          <div className="flex min-h-[45vh] flex-col items-center justify-center text-center">
            <div className="mb-4 flex size-10 items-center justify-center rounded-lg bg-zinc-900 text-white">
              <Bot className="size-5" />
            </div>
            <h1 className="text-2xl font-semibold text-zinc-950">
              How can I help?
            </h1>
          </div>
        ) : null}

        {messages.map((message) => {
          const canRegenerate =
            message.role === "assistant" &&
            message.status !== "streaming" &&
            Boolean(message.prompt);
          const isStreaming =
            message.role === "assistant" && message.status === "streaming";
          const isError = message.status === "error";

          return (
            <article
              key={message.id}
              className={cn(
                "flex gap-3",
                message.role === "user" ? "justify-end" : "justify-start",
              )}
            >
              {message.role === "assistant" ? (
                <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-emerald-500 text-white">
                  <Bot className="size-4" />
                </div>
              ) : null}

              <div
                className={cn(
                  "min-w-0 max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm sm:max-w-[75%]",
                  message.role === "assistant"
                    ? "rounded-tl-md bg-zinc-100 text-zinc-950"
                    : "rounded-tr-md bg-[#f4f4f4] text-zinc-950",
                  isError && "border border-red-200 bg-red-50 text-red-900",
                )}
              >
                {message.content ? (
                  <MarkdownMessage content={message.content} />
                ) : (
                  <div className="flex items-center gap-2 text-zinc-500">
                    <Loader2 className="size-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <time className="block text-xs text-zinc-500">
                    {message.createdAt}
                  </time>
                  {isStreaming && message.content ? (
                    <span className="flex items-center gap-1 text-xs text-zinc-500">
                      <Loader2 className="size-3 animate-spin" />
                      Streaming
                    </span>
                  ) : null}
                  {message.status === "stopped" ? (
                    <span className="text-xs text-zinc-500">Stopped</span>
                  ) : null}
                  {canRegenerate ? (
                    <Button
                      className={cn(
                        "h-7 bg-white px-2 text-xs",
                        isError
                          ? "border-red-200 text-red-700 hover:bg-red-50"
                          : "border-zinc-200 text-zinc-700 hover:bg-zinc-50",
                      )}
                      disabled={isLoading}
                      size="sm"
                      type="button"
                      variant="outline"
                      onClick={() => {
                        if (message.prompt) {
                          onRegenerate(message.prompt, message.id);
                        }
                      }}
                    >
                      {isError ? (
                        <RefreshCcw className="size-3" />
                      ) : (
                        <RotateCcw className="size-3" />
                      )}
                      {isError ? "Retry" : "Regenerate"}
                    </Button>
                  ) : null}
                </div>
              </div>

              {message.role === "user" ? (
                <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-zinc-800 text-white">
                  <UserRound className="size-4" />
                </div>
              ) : null}
            </article>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
