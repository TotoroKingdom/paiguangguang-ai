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
    <header className="flex min-h-14 shrink-0 flex-wrap items-center gap-3 border-b border-ink/10 bg-white/85 px-4 py-3 backdrop-blur sm:px-6 lg:px-8">
      <button
        type="button"
        aria-label="Open conversations"
        onClick={onOpenSidebar}
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-ink/10 bg-white text-ink transition hover:border-tide/40 hover:bg-paper lg:hidden"
      >
        <span aria-hidden="true" className="text-lg leading-none">
          ☰
        </span>
      </button>

      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/45">Chatbot workspace</p>
        <h1 className="truncate text-lg font-semibold text-ink">{VIEW_LABELS[view]}</h1>
      </div>

      <div className="ml-auto inline-flex rounded-full border border-ink/10 bg-paper p-1">
        {(Object.keys(VIEW_LABELS) as ChatbotView[]).map((item) => (
          <button
            key={item}
            type="button"
            aria-pressed={view === item}
            onClick={() => onChangeView(item)}
            className={[
              "rounded-full px-3 py-2 text-sm font-semibold transition",
              view === item
                ? "bg-tide text-paper shadow-sm"
                : "text-ink/70 hover:bg-white hover:text-ink",
            ].join(" ")}
          >
            {VIEW_LABELS[item]}
          </button>
        ))}
      </div>
    </header>
  );
}
