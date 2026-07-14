import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));
vi.mock("@/components/auth-provider", () => ({
  useAuth: () => ({ status: "authenticated", user: { email: "owner@example.com" }, logout: vi.fn() }),
}));

describe("SiteNav", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("hides the Chatbot entry when its feature flag is disabled", async () => {
    vi.stubEnv("NEXT_PUBLIC_CHATBOT_ENABLED", "false");
    const { SiteNav } = await import("./site-nav");
    render(<SiteNav />);

    expect(screen.queryByRole("link", { name: "Chatbot" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Knowledge" })).toBeInTheDocument();
  });
});
