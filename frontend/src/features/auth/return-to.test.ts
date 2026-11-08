import { describe, expect, it } from "vitest";
import { safeReturnTo } from "./return-to";

describe("safeReturnTo", () => {
  it("accepts only same-site assistant paths", () => {
    expect(safeReturnTo("/assistant/me")).toBe("/assistant/me");
    expect(safeReturnTo("/assistant/chat/abc?tab=1")).toBe(
      "/assistant/chat/abc?tab=1",
    );
    expect(safeReturnTo("/assistant")).toBe("/assistant");
  });

  it("rejects external, protocol-relative and backslash paths", () => {
    expect(safeReturnTo("https://evil.example")).toBeNull();
    expect(safeReturnTo("//evil.example/assistant")).toBeNull();
    expect(safeReturnTo("/\\evil.example")).toBeNull();
    expect(safeReturnTo("/assistant\\..\\evil")).toBeNull();
    expect(safeReturnTo("javascript:alert(1)")).toBeNull();
  });

  it("rejects non-assistant, encoded and control-character paths", () => {
    expect(safeReturnTo("/admin")).toBeNull();
    expect(safeReturnTo("/assistant/%2F%2Fevil")).toBe("/assistant/%2F%2Fevil");
    expect(safeReturnTo("/assistant/\nnext")).toBeNull();
    expect(safeReturnTo("")).toBeNull();
    expect(safeReturnTo(null)).toBeNull();
  });
});
