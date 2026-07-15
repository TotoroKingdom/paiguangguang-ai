"use client";

type ChatbotView = "chat" | "memories";

type ChatbotHeaderProps = {
  view: ChatbotView;
  onChangeView: (view: ChatbotView) => void;
  onOpenSidebar: () => void;
};

const VIEW_LABELS: Record<ChatbotView, string> = {
  chat: "Chat",
  memories: "Memories",
};

export function ChatbotHeader({ view, onChangeView, onOpenSidebar }: ChatbotHeaderProps) {
  return (
    <header className="relative flex min-h-14 shrink-0 items-center justify-end px-4 py-3 sm:px-6 lg:px-8">
      <button
        type="button"
        aria-label="Open conversations"
        onClick={onOpenSidebar}
        className="absolute left-4 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[var(--chat-border)] bg-white text-ink/55 shadow-[0_1px_3px_rgba(18,24,35,0.05)] transition hover:border-tide/35 hover:text-tide lg:hidden"
      >
        <span aria-hidden="true" className="inline-flex h-4 w-4 flex-col justify-between">
          <span className="block h-0.5 w-full rounded-full bg-current" />
          <span className="block h-0.5 w-full rounded-full bg-current" />
          <span className="block h-0.5 w-full rounded-full bg-current" />
        </span>
      </button>

      <div className="inline-flex rounded-full border border-[var(--chat-border)] bg-white/90 p-1 shadow-[0_1px_4px_rgba(18,24,35,0.04)] backdrop-blur">
        {(Object.keys(VIEW_LABELS) as ChatbotView[]).map((item) => (
          <button
            key={item}
            type="button"
            aria-pressed={view === item}
            onClick={() => onChangeView(item)}
            className={[
              "rounded-full px-3.5 py-2 text-sm font-semibold transition",
              view === item
                ? "bg-tide text-paper shadow-sm"
                : "text-ink/65 hover:bg-white hover:text-ink",
            ].join(" ")}
          >
            {VIEW_LABELS[item]}
          </button>
        ))}
      </div>
    </header>
  );
}
