"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AssistantIcon } from "./assistant-icon";

export function AssistantDialog({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const titleId = useId();
  const container = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const focusable = () =>
      Array.from(
        container.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], input:not([disabled]), select, textarea, [tabindex="0"]',
        ) ?? [],
      );
    (
      focusable().find((el) => el.tagName === "INPUT") ??
      focusable()[0] ??
      container.current
    )?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeRef.current();
      }
      if (event.key === "Tab") {
        const elements = focusable();
        const first = elements[0];
        const last = elements[elements.length - 1];
        if (!first) {
          event.preventDefault();
          container.current?.focus();
        } else if (!container.current?.contains(document.activeElement)) {
          event.preventDefault();
          (event.shiftKey ? last : first).focus();
        } else if (
          event.shiftKey &&
          (document.activeElement === first || document.activeElement === container.current)
        ) {
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
  }, []);
  useEffect(() => {
    if (container.current && !container.current.contains(document.activeElement)) {
      (
        container.current.querySelector<HTMLElement>(
          "button:not([disabled]), input:not([disabled]), a[href]",
        ) ?? container.current
      ).focus();
    }
  }, [title]);
  return createPortal(
    <div
      className="assistant-dialog-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="assistant-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        ref={container}
      >
        <header>
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="as-icon-button" onClick={onClose} aria-label="关闭弹窗">
            <AssistantIcon name="close" />
          </button>
        </header>
        <div className="assistant-dialog-body">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
