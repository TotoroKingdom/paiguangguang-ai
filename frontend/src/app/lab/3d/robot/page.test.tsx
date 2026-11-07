import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RobotExperimentPage from "./page";

describe("RobotExperimentPage", () => {
  it("embeds the existing robot and returns to the gallery", () => {
    render(<RobotExperimentPage />);

    expect(screen.getByRole("link", { name: /返回 3D 实验室/ })).toHaveAttribute("href", "/lab/3d");
    expect(screen.getByTitle("Three.js 智能机器人交互演示")).toHaveAttribute("src", "/threejs-lab/index.html");
  });
});
