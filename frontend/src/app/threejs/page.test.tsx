import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ThreeJsLabPage from "./page";

describe("ThreeJsLabPage", () => {
  it("opens the migrated robot experiment and provides a route back", () => {
    render(<ThreeJsLabPage />);

    expect(screen.getByRole("link", { name: /返回探索项目/ })).toHaveAttribute("href", "/#exploring");
    expect(screen.getByTitle("Three.js 智能机器人交互演示")).toHaveAttribute("src", "/threejs-lab/index.html");
  });
});
