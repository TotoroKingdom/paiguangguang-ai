import { afterEach, describe, expect, it, vi } from "vitest";

import { getBackendBaseUrl } from "@/lib/api";

describe("getBackendBaseUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses same-origin requests when no backend URL is configured", () => {
    vi.stubEnv("NEXT_PUBLIC_BACKEND_URL", "");

    expect(getBackendBaseUrl()).toBe("");
  });

  it("normalizes a configured backend URL", () => {
    vi.stubEnv("NEXT_PUBLIC_BACKEND_URL", " https://api.example.test/ ");

    expect(getBackendBaseUrl()).toBe("https://api.example.test");
  });
});
