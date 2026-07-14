"use client";

import { useCallback, useLayoutEffect, useMemo, useRef, type FormEvent, type KeyboardEvent } from "react";

type ChatComposerProps = {
  value: string;
  disabled?: boolean;
  sending?: boolean;
  maxLength?: number;
  error?: string | null;
  model?: string | null;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void | Promise<void>;
  onStop?: () => void | Promise<void>;
  stopping?: boolean;
};

const MAX_VISIBLE_ROWS = 3;

function syncTextareaHeight(textarea: HTMLTextAreaElement) {
  const computed = window.getComputedStyle(textarea);
  const lineHeight = Number.parseFloat(computed.lineHeight) || 24;
  const paddingTop = Number.parseFloat(computed.paddingTop) || 0;
  const paddingBottom = Number.parseFloat(computed.paddingBottom) || 0;
  const verticalPadding = paddingTop + paddingBottom;
  const maxHeight = lineHeight * MAX_VISIBLE_ROWS + verticalPadding;
  const minHeight = lineHeight + verticalPadding;

  textarea.style.height = "auto";
  const nextHeight = Math.min(textarea.scrollHeight, maxHeight);
  textarea.style.height = `${Math.max(nextHeight, minHeight)}px`;
  textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
}

export function ChatComposer({
  value,
  disabled = false,
  sending = false,
  maxLength = 4000,
  error = null,
  model = null,
  onChange,
  onSubmit,
  onStop,
  stopping = false,
}: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const isComposingRef = useRef(false);

  const isOverflow = value.length > maxLength;
  const canSubmit = !disabled && !sending && value.trim().length > 0 && !isOverflow;
  const canStop = sending && Boolean(onStop);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    syncTextareaHeight(textarea);
  }, [value]);

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

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === "Enter" && !event.shiftKey) {
        if (isComposingRef.current || event.nativeEvent.isComposing) {
          return;
        }

        event.preventDefault();
        if (canSubmit) {
          void onSubmit(value);
        }
      }
    },
    [canSubmit, onSubmit, value]
  );

  const helperText = useMemo(() => {
    if (sending) {
      return "Sending... Press Stop to cancel the current generation.";
    }
    return "Enter to send, Shift+Enter for a new line.";
  }, [sending]);

  const primaryLabel = useMemo(() => {
    if (canStop) {
      return stopping ? "Stopping..." : "Stop generation";
    }
    if (sending) {
      return "Sending...";
    }
    return "Send message";
  }, [canStop, sending, stopping]);

  const primaryDisabled = disabled || stopping || (!canSubmit && !canStop);
  const primaryType = canStop ? "button" : "submit";

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto w-full max-w-4xl rounded-2xl border border-ink/10 bg-white/80 p-4 shadow-sm"
    >
      <label className="block">
        <span className="sr-only">Message</span>
        <textarea
          ref={textareaRef}
          value={value}
          disabled={disabled || sending}
          maxLength={maxLength}
          rows={1}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => {
            isComposingRef.current = true;
          }}
          onCompositionEnd={() => {
            isComposingRef.current = false;
          }}
          placeholder="Ask about the project phases, architecture, or implementation choices."
          className="block w-full resize-none rounded-xl border border-ink/15 bg-white px-4 py-3 text-sm leading-7 text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10 disabled:cursor-not-allowed disabled:bg-paper"
        />
      </label>

      {error ? (
        <p className="mt-3 rounded-xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm leading-6 text-ink">
          {error}
        </p>
      ) : null}

      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-col gap-1 text-xs text-ink/50">
          {model ? (
            <span className="truncate rounded-full border border-ink/10 bg-paper px-3 py-1.5 font-semibold text-ink/70">
              Model: {model}
            </span>
          ) : null}
          <span>
            {value.length}/{maxLength}
          </span>
          <span>{helperText}</span>
        </div>

        <div className="flex items-center justify-end gap-3">
          <button
            type={primaryType}
            onClick={canStop ? () => void onStop?.() : undefined}
            disabled={primaryDisabled}
            className="rounded-full border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {primaryLabel}
          </button>
          <button
            type="button"
            onClick={() => {
              onChange("");
              textareaRef.current?.focus();
            }}
            disabled={disabled || sending || value.length === 0}
            className="rounded-full border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink/25 hover:bg-paper disabled:cursor-not-allowed disabled:opacity-60"
          >
            Clear
          </button>
        </div>
      </div>
    </form>
  );
}
