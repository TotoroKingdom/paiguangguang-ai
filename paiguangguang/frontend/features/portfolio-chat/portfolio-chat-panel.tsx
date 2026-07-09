"use client";

import { FormEvent, useState } from "react";

import { ApiError, postJson } from "@/lib/api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type PortfolioChatData = {
  reply: string;
  session_id: string;
};

const starterMessages: ChatMessage[] = [
  {
    id: "assistant-welcome",
    role: "assistant",
    content:
      "Ask me anything about this AI engineer portfolio. I can explain the project structure, phases, and the systems that are planned for V2 and V3."
  }
];

const suggestions = [
  "What is this project built to demonstrate?",
  "How is V1 different from V2?",
  "Which module should I look at first?"
];

function makeMessageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function PortfolioChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>(starterMessages);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const message = input.trim();
    if (!message || isLoading) {
      return;
    }

    setError(null);
    setInput("");
    setIsLoading(true);
    setMessages((current) => [...current, { id: makeMessageId(), role: "user", content: message }]);

    try {
      const result = await postJson<PortfolioChatData, { message: string; session_id: string | null }>(
        "/api/v1/chat/portfolio",
        {
          message,
          session_id: sessionId
        }
      );

      setSessionId(result.session_id);
      setMessages((current) => [
        ...current,
        { id: makeMessageId(), role: "assistant", content: result.reply }
      ]);
    } catch (err) {
      const messageText =
        err instanceof ApiError ? err.message : "Unable to reach the chat bot backend.";
      setError(messageText);
      setInput(message);
    } finally {
      setIsLoading(false);
    }
  }

  function handleSuggestionClick(text: string) {
    if (isLoading) {
      return;
    }

    setInput(text);
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
      <div className="border border-ink/10 bg-white/70 p-5 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase text-clay">V1 Live Module</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">Chat bot</h2>
          </div>
          <div className="rounded-full border border-tide/20 bg-tide/10 px-3 py-1 text-xs font-semibold text-tide">
            Session {sessionId ? "active" : "new"}
          </div>
        </div>

        <div className="mt-5 space-y-4">
          <div className="max-h-[26rem] space-y-3 overflow-y-auto rounded-2xl border border-ink/10 bg-paper/80 p-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={[
                  "flex",
                  message.role === "user" ? "justify-end" : "justify-start"
                ].join(" ")}
              >
                <div
                  className={[
                    "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-7 shadow-sm",
                    message.role === "user"
                      ? "bg-ink text-paper"
                      : "border border-ink/10 bg-white text-ink"
                  ].join(" ")}
                >
                  {message.content}
                </div>
              </div>
            ))}
            {isLoading ? (
              <div className="flex justify-start">
                <div className="rounded-2xl border border-ink/10 bg-white px-4 py-3 text-sm text-ink/60">
                  Thinking through the portfolio context...
                </div>
              </div>
            ) : null}
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-ink">Ask a question</span>
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                rows={4}
                placeholder="Try asking about the project phases, architecture, or the AI systems behind the site."
                className="w-full resize-none border border-ink/15 bg-white px-4 py-3 text-sm leading-7 text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
              />
            </label>

            {error ? (
              <div className="border border-clay/30 bg-clay/10 px-4 py-3 text-sm leading-6 text-ink">
                {error}
              </div>
            ) : null}

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={isLoading}
                className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isLoading ? "Sending..." : "Send"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setMessages(starterMessages);
                  setSessionId(null);
                  setError(null);
                  setInput("");
                }}
                className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink/25 hover:bg-paper"
              >
                Reset chat
              </button>
            </div>
          </form>
        </div>
      </div>

      <aside className="space-y-4">
        <div className="border border-ink/10 bg-white/65 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase text-clay">Suggested prompts</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => handleSuggestionClick(suggestion)}
                className="border border-ink/10 bg-paper px-3 py-2 text-left text-sm leading-6 text-ink transition hover:border-tide/35 hover:bg-white"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>

        <div className="border border-ink/10 bg-white/65 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase text-clay">What this proves</p>
          <ul className="mt-4 space-y-3 text-sm leading-7 text-ink/75">
            <li>Frontend state management for a single chat workflow</li>
            <li>Backend round-trip with a stable API contract</li>
            <li>Session memory across multiple turns</li>
            <li>Error handling for backend failures</li>
          </ul>
        </div>
      </aside>
    </section>
  );
}
