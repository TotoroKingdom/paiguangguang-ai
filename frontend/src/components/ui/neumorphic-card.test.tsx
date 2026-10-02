import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NeumorphicCard } from "./neumorphic-card";

afterEach(() => vi.unstubAllGlobals());

function pointerMove(card: HTMLElement, pointerType: string) {
  const event = new MouseEvent("pointermove", { bubbles: true, clientX: 1000, clientY: -1000 });
  Object.defineProperty(event, "pointerType", { value: pointerType });
  fireEvent(card, event);
}

function setup(enabled: boolean) {
  vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: enabled }));
  render(<NeumorphicCard aria-label="Project"><a href="/rag">Explore system</a></NeumorphicCard>);
  const card = screen.getByRole("article");
  vi.spyOn(card, "getBoundingClientRect").mockReturnValue({ left: 0, top: 0, width: 200, height: 100 } as DOMRect);
  return card;
}

describe("spatial project interaction", () => {
  it("bounds pointer tilt and resets when the pointer leaves", () => {
    const card = setup(true);
    pointerMove(card, "mouse");
    expect(card.style.getPropertyValue("--card-x")).toBe("3deg");
    expect(card.style.getPropertyValue("--card-y")).toBe("4deg");
    fireEvent.pointerLeave(card);
    expect(card.style.getPropertyValue("--card-x")).toBe("0deg");
    expect(card.style.getPropertyValue("--card-y")).toBe("0deg");
  });

  it("does not track touch input", () => {
    const card = setup(true);
    pointerMove(card, "touch");
    expect(card.style.getPropertyValue("--card-x")).toBe("");
  });

  it("disables tilt when motion or device preferences disallow it", () => {
    const card = setup(false);
    pointerMove(card, "mouse");
    expect(card.style.getPropertyValue("--card-y")).toBe("");
    expect(screen.getByRole("link", { name: "Explore system" })).toHaveAttribute("href", "/rag");
  });
});
