import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MiniScenePreview } from "./mini-scene-preview";

const originalObserver = window.IntersectionObserver;
let onIntersection: IntersectionObserverCallback | undefined;

describe("MiniScenePreview", () => {
  beforeEach(() => {
    onIntersection = undefined;
    vi.stubGlobal("WebGLRenderingContext", class {});
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: false }));
    window.IntersectionObserver = class {
      constructor(callback: IntersectionObserverCallback) { onIntersection = callback; }
      observe() {}
      disconnect() {}
    } as unknown as typeof IntersectionObserver;
  });

  afterEach(() => {
    window.IntersectionObserver = originalObserver;
    vi.unstubAllGlobals();
  });

  it("waits for the robot's first frame without flashing an old static illustration", () => {
    const { container } = render(<MiniScenePreview scene="robot" />);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("3D LOADING")).toBeInTheDocument();
    expect(container.querySelector("iframe")).toBeNull();

    act(() => onIntersection?.([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver));
    const frame = container.querySelector("iframe")!;
    expect(frame).toHaveAttribute("src", "/threejs-lab/mini.html");
    expect(frame).toHaveAttribute("tabindex", "-1");
    expect(frame.className).not.toContain("frameReady");

    act(() => window.dispatchEvent(new MessageEvent("message", {
      data: { type: "mini-scene-ready" },
      origin: window.location.origin,
      source: frame.contentWindow
    })));
    expect(frame.className).toContain("frameReady");
    expect(screen.getByText("● LIVE 3D")).toBeInTheDocument();

    act(() => onIntersection?.([{ isIntersecting: false } as IntersectionObserverEntry], {} as IntersectionObserver));
    expect(container.querySelector("iframe")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
  });

  it("loads the gears scene using the same lightweight preview component", () => {
    const { container } = render(<MiniScenePreview scene="gears" />);
    act(() => onIntersection?.([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver));
    expect(container.querySelector("iframe")).toHaveAttribute("src", "/threejs-gears/mini.html");
  });

  it("keeps an abstract CSS fallback under reduced-motion preferences", () => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true }));
    const { container } = render(<MiniScenePreview scene="robot" />);
    expect(screen.getByText("3D PREVIEW")).toBeInTheDocument();
    expect(container.querySelector("iframe, img")).toBeNull();
  });
});
