import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "./app-shell";

let pathname = "/";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
}));

vi.mock("@/components/site-nav", () => ({
  SiteNav: () => <header data-testid="site-nav" />,
}));

describe("AppShell", () => {
  afterEach(() => {
    pathname = "/";
  });

  it("renders the chatbot route without the global shell padding", () => {
    pathname = "/chat-bot";

    render(
      <AppShell>
        <div data-testid="workspace" />
      </AppShell>
    );

    expect(screen.queryByTestId("site-nav")).not.toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("h-dvh", "p-0");
    expect(screen.getByTestId("workspace")).toBeInTheDocument();
  });

  it("keeps the global shell for regular routes", () => {
    pathname = "/agents/knowledge";

    render(
      <AppShell>
        <div data-testid="workspace" />
      </AppShell>
    );

    expect(screen.getByTestId("site-nav")).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("px-4", "py-6");
  });
});
