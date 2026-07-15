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

const MIN_VISIBLE_ROWS = 4;
const MAX_VISIBLE_ROWS = 6;

function syncTextareaHeight(textarea: HTMLTextAreaElement) {
  const computed = window.getComputedStyle(textarea);
  const lineHeight = Number.parseFloat(computed.lineHeight) || 24;
  const paddingTop = Number.parseFloat(computed.paddingTop) || 0;
  const paddingBottom = Number.parseFloat(computed.paddingBottom) || 0;
  const verticalPadding = paddingTop + paddingBottom;
  const maxHeight = lineHeight * MAX_VISIBLE_ROWS + verticalPadding;
  const minHeight = lineHeight * MIN_VISIBLE_ROWS + verticalPadding;

  textarea.style.height = "auto";
  const nextHeight = Math.min(textarea.scrollHeight, maxHeight);
  textarea.style.height = `${Math.max(nextHeight, minHeight)}px`;
  textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="none">
      <path
        d="M6 12L18 6L13 18L11 13L6 12Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="currentColor">
      <rect x="7" y="7" width="10" height="10" rx="2.5" />
    </svg>
  );
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
      className="mx-auto w-full max-w-[64rem] rounded-[28px] border border-ink/10 bg-white p-5 shadow-[0_2px_12px_rgba(15,23,42,0.05)]"
    >
      <label className="block">
        <span className="sr-only">Message</span>
        <textarea
          ref={textareaRef}
          value={value}
          disabled={disabled || sending}
          maxLength={maxLength}
          rows={MIN_VISIBLE_ROWS}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => {
            isComposingRef.current = true;
          }}
          onCompositionEnd={() => {
            isComposingRef.current = false;
          }}
          placeholder="给暖心助手发送消息"
          className="block w-full resize-none rounded-[24px] border-0 bg-transparent px-0 py-0 text-[15px] leading-7 text-ink outline-none placeholder:text-ink/30 disabled:cursor-not-allowed"
        />
      </label>

      {error ? (
        <p className="mt-3 rounded-xl border border-clay/20 bg-clay/8 px-4 py-3 text-sm leading-6 text-ink">
          {error}
        </p>
      ) : null}

      <div className="mt-4 flex items-end justify-between gap-4">
        <div className="min-w-0">
          {model ? (
            <span className="inline-flex max-w-full rounded-full border border-ink/10 bg-paper px-3 py-1.5 text-[13px] font-medium text-ink/70">
              Model: {model}
            </span>
          ) : null}
        </div>

        <button
          type={primaryType}
          onClick={canStop ? () => void onStop?.() : undefined}
          disabled={primaryDisabled}
          aria-label={primaryLabel}
          className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-tide text-paper shadow-[0_4px_14px_rgba(67,96,255,0.22)] transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:bg-ink/15 disabled:text-ink/45 disabled:shadow-none"
        >
          <span className="sr-only">{primaryLabel}</span>
          {canStop ? <StopIcon /> : <SendIcon />}
        </button>
      </div>
    </form>
  );
}
