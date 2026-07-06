"use client";

import type { ReactNode } from "react";

export function AdminEntityModal({
  open,
  title,
  description,
  children,
  footer,
  onClose,
  widthClassName = "max-w-2xl",
}: {
  open: boolean;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
  widthClassName?: string;
}) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 px-4 py-6 backdrop-blur-sm">
      <div className={["w-full rounded-none border border-ink/10 bg-white shadow-2xl", widthClassName].join(" ")}>
        <div className="border-b border-ink/10 bg-paper/70 px-5 py-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-clay">Admin action</p>
              <h3 className="mt-2 text-xl font-semibold text-ink">{title}</h3>
              {description ? <p className="mt-2 text-sm leading-6 text-ink/70">{description}</p> : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/30 hover:bg-paper"
            >
              Close
            </button>
          </div>
        </div>
        <div className="px-5 py-5">{children}</div>
        {footer ? <div className="border-t border-ink/10 bg-paper/70 px-5 py-4">{footer}</div> : null}
      </div>
    </div>
  );
}
