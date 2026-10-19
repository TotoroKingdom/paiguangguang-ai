import { describe, expect, it } from "vitest";
import { deviceDprLimit, isModelVisible } from "./ai-core-runtime";

describe("AI Core runtime limits", () => {
  it("stays hidden over consecutive low-opacity frames and reappears at the threshold", () => {
    expect([1, 0.004, 0.003, 0, 0.004, 0.005, 0.1].map(isModelVisible))
      .toEqual([true, false, false, false, false, true, true]);
  });
  it.each([[false, false, 1.5], [false, true, 1.35], [true, false, 1.25], [true, true, 1.25]])(
    "selects DPR for compact=%s lowPower=%s", (compact, lowPower, expected) => {
      expect(deviceDprLimit(compact as boolean, lowPower as boolean)).toBe(expected);
    }
  );
});
