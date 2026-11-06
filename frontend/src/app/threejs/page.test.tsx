import { describe, expect, it, vi } from "vitest";

import ThreeJsLabPage from "./page";

const redirectMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ redirect: redirectMock }));

describe("legacy /threejs route", () => {
  it("redirects older links to the robot within the new laboratory", () => {
    ThreeJsLabPage();
    expect(redirectMock).toHaveBeenCalledWith("/lab/3d/robot");
  });
});
