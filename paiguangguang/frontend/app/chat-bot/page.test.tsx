import { render, screen } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import ChatBotPage from "./page";

const { notFound } = vi.hoisted(() => ({ notFound: vi.fn() }));

vi.mock("next/navigation", () => ({ notFound }));

vi.mock("@/features/chatbot/components/chatbot-shell", () => ({
  ChatbotShell: () => <div data-testid="chatbot-shell" />,
}));

describe("ChatBotPage", () => {
  beforeEach(() => {
    notFound.mockClear();
    vi.unstubAllEnvs();
  });

  it("renders the new ChatbotShell workspace", () => {
    render(<ChatBotPage />);

    expect(screen.getByTestId("chatbot-shell")).toBeInTheDocument();
  });

  it("returns not found when the Chatbot flag is disabled", () => {
    vi.stubEnv("NEXT_PUBLIC_CHATBOT_ENABLED", "false");
    render(<ChatBotPage />);
    expect(notFound).toHaveBeenCalledTimes(1);
  });
});
