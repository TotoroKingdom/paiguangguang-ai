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
        className="absolute left-4 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-ink/10 bg-white text-ink shadow-[0_1px_4px_rgba(15,23,42,0.04)] transition hover:border-tide/40 hover:bg-paper lg:hidden"
      >
        <span aria-hidden="true" className="text-lg leading-none">
          ☰
        </span>
      </button>

      <div className="inline-flex rounded-full border border-ink/10 bg-white/80 p-1 shadow-[0_1px_4px_rgba(15,23,42,0.03)] backdrop-blur">
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
