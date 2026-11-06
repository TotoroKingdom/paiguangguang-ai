import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MiniRobotPreview } from "./mini-robot-preview";

const poster = "/work/threejs-lab-preview.svg";
const originalObserver = window.IntersectionObserver;
let onIntersection: IntersectionObserverCallback | undefined;

describe("MiniRobotPreview", () => {
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

  it("keeps a static fallback until visible, then loads the shared mini model", () => {
    render(<MiniRobotPreview poster={poster} alt="机器人预览" sizes="50vw" />);

    expect(screen.getByRole("img", { name: "机器人预览" })).toHaveAttribute("src", poster);
    expect(screen.queryByTitle("Three.js 智能机器人 mini 预览")).not.toBeInTheDocument();

    act(() => onIntersection?.([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver));
    const frame = screen.getByTitle("Three.js 智能机器人 mini 预览");
    expect(frame).toHaveAttribute("src", "/threejs-lab/mini.html");
    expect(frame).toHaveAttribute("aria-hidden", "true");
    expect(frame).toHaveAttribute("tabindex", "-1");

    act(() => onIntersection?.([{ isIntersecting: false } as IntersectionObserverEntry], {} as IntersectionObserver));
    expect(screen.queryByTitle("Three.js 智能机器人 mini 预览")).not.toBeInTheDocument();
  });

  it("does not start WebGL animation when reduced motion is requested", () => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true }));
    render(<MiniRobotPreview poster={poster} alt="静态机器人预览" sizes="100vw" />);

    expect(screen.getByRole("img", { name: "静态机器人预览" })).toBeInTheDocument();
    expect(onIntersection).toBeUndefined();
    expect(screen.queryByTitle("Three.js 智能机器人 mini 预览")).not.toBeInTheDocument();
  });
});
