import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import ChatBotPage from "./page";

vi.mock("@/features/chatbot/components/chatbot-shell", () => ({
  ChatbotShell: () => <div data-testid="chatbot-shell" />,
}));

describe("ChatBotPage", () => {
  it("renders the new ChatbotShell workspace", () => {
    render(<ChatBotPage />);

    expect(screen.getByTestId("chatbot-shell")).toBeInTheDocument();
  });
});
