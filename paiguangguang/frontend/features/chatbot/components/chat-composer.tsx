"use client";

import { useCallback, type FormEvent } from "react";

type ChatComposerProps = {
  value: string;
  disabled?: boolean;
  sending?: boolean;
  maxLength?: number;
  error?: string | null;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void | Promise<void>;
};

export function ChatComposer({
  value,
  disabled = false,
  sending = false,
  maxLength = 4000,
  error = null,
  onChange,
  onSubmit,
}: ChatComposerProps) {
  const isOverflow = value.length > maxLength;
  const canSubmit = !disabled && !sending && value.trim().length > 0 && !isOverflow;

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!canSubmit) {
        return;
      }
      void onSubmit(value);
    },
    [canSubmit, onSubmit, value]
  );

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl border border-ink/10 bg-white/80 p-4 shadow-sm">
      <label className="block">
        <span className="mb-2 block text-sm font-semibold text-ink">Message</span>
        <textarea
          value={value}
          disabled={disabled || sending}
          maxLength={maxLength}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (canSubmit) {
                void onSubmit(value);
              }
            }
          }}
          rows={5}
          placeholder="Ask about the project phases, architecture, or implementation choices."
          className="w-full resize-none rounded-xl border border-ink/15 bg-white px-4 py-3 text-sm leading-7 text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10 disabled:cursor-not-allowed disabled:bg-paper"
        />
      </label>

      <div className="mt-3 flex items-center justify-between gap-3 text-xs text-ink/50">
        <span>
          {value.length}/{maxLength}
        </span>
        <span>{sending ? "Sending…" : "Enter to send, Shift+Enter for a new line"}</span>
      </div>

      {error ? (
        <p className="mt-3 rounded-xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm leading-6 text-ink">
          {error}
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={!canSubmit}
          className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {sending ? "Sending…" : "Send message"}
        </button>
        <button
          type="button"
          onClick={() => onChange("")}
          disabled={disabled || sending || value.length === 0}
          className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink/25 hover:bg-paper disabled:cursor-not-allowed disabled:opacity-60"
        >
          Clear
        </button>
      </div>
    </form>
  );
}

