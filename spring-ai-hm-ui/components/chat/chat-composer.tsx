"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { SendHorizontal, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type ChatComposerProps = {
  isLoading: boolean;
  onSend: (content: string) => void;
  onStop: () => void;
};

export function ChatComposer({ isLoading, onSend, onStop }: ChatComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const textarea = textareaRef.current;

    if (!textarea) {
      return;
    }

    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }, [value]);

  function submitMessage() {
    const content = (textareaRef.current?.value ?? value).trim();

    if (!content || isLoading) {
      return;
    }

    onSend(content);
    setValue("");

    if (textareaRef.current) {
      textareaRef.current.value = "";
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitMessage();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitMessage();
    }
  }

  function handleInputValue(nextValue: string) {
    setValue(nextValue);
  }

  return (
    <div className="shrink-0 border-t border-zinc-200 bg-white px-4 pb-4 pt-3 sm:px-6">
      <form className="mx-auto max-w-3xl" onSubmit={handleSubmit}>
        <div className="flex items-end gap-2 rounded-xl border border-zinc-300 bg-white p-2 shadow-[0_12px_32px_rgba(0,0,0,0.08)] focus-within:border-zinc-500">
          <Textarea
            ref={textareaRef}
            className="max-h-[180px] min-h-11 resize-none border-0 px-3 py-2.5 text-base text-zinc-950 shadow-none placeholder:text-zinc-500 focus-visible:ring-0 sm:text-sm"
            disabled={isLoading}
            placeholder={isLoading ? "Waiting for response..." : "Message GPT"}
            rows={1}
            value={value}
            onChange={(event) => handleInputValue(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          <Button
            aria-label={isLoading ? "Stop generating" : "Send message"}
            className="size-9 shrink-0 rounded-md bg-zinc-900 text-white hover:bg-zinc-700 disabled:bg-zinc-200 disabled:text-zinc-400"
            size="icon"
            type={isLoading ? "button" : "submit"}
            onClick={isLoading ? onStop : undefined}
          >
            {isLoading ? <Square className="fill-current" /> : <SendHorizontal />}
          </Button>
        </div>
      </form>
    </div>
  );
}
