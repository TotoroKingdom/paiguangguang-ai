import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ThreeDLabGalleryPage from "./page";

describe("ThreeDLabGalleryPage", () => {
  it("links to the robot and gears experiments while keeping future concepts non-clickable", () => {
    render(<ThreeDLabGalleryPage />);

    expect(screen.getByRole("heading", { level: 1, name: /3D 交互实验室/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /返回我的作品/ })).toHaveAttribute("href", "/#projects");

    const robotLink = screen.getByRole("link", { name: /智能机器人，进入交互实验/ });
    expect(robotLink).toHaveAttribute("href", "/lab/3d/robot");
    expect(within(robotLink).getByText("可交互", { exact: false })).toBeInTheDocument();

    const gearsLink = screen.getByRole("link", { name: /机械齿轮，进入交互实验/ });
    expect(gearsLink).toHaveAttribute("href", "/lab/3d/gears");
    expect(within(gearsLink).getByText("可交互", { exact: false })).toBeInTheDocument();

    for (const name of ["粒子星系"]) {
      const planned = screen.getByRole("article", { name: `${name}，规划中` });
      expect(within(planned).getByRole("heading", { name })).toBeInTheDocument();
      expect(within(planned).getByText("规划中")).toBeInTheDocument();
      expect(within(planned).getByText("即将开放")).toBeInTheDocument();
      expect(within(planned).queryByRole("link")).not.toBeInTheDocument();
    }

    expect(screen.queryByRole("link", { name: /粒子星系/ })).not.toBeInTheDocument();
    expect(screen.getByLabelText("已上线 2 个实验，共规划 3 个")).toBeInTheDocument();
  });
});
