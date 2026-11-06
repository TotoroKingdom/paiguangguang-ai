import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ThreeDLabGalleryPage from "./page";

describe("ThreeDLabGalleryPage", () => {
  it("provides one interactive experiment and non-clickable future concepts", () => {
    render(<ThreeDLabGalleryPage />);

    expect(screen.getByRole("heading", { level: 1, name: /3D 交互实验室/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /返回我的作品/ })).toHaveAttribute("href", "/#projects");

    const robotLink = screen.getByRole("link", { name: /智能机器人，进入交互实验/ });
    expect(robotLink).toHaveAttribute("href", "/lab/3d/robot");
    expect(within(robotLink).getByText("可交互", { exact: false })).toBeInTheDocument();

    for (const name of ["机械齿轮", "粒子星系"]) {
      const planned = screen.getByRole("article", { name: `${name}，规划中` });
      expect(within(planned).getByRole("heading", { name })).toBeInTheDocument();
      expect(within(planned).getByText("规划中")).toBeInTheDocument();
      expect(within(planned).getByText("即将开放")).toBeInTheDocument();
      expect(within(planned).queryByRole("link")).not.toBeInTheDocument();
    }

    expect(screen.queryByRole("link", { name: /机械齿轮|粒子星系/ })).not.toBeInTheDocument();
  });
});
