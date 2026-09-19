import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HomepageProjects } from "./homepage-projects";

describe("HomepageProjects", () => {
  it("shows real project interfaces and working case links", () => {
    render(<HomepageProjects />);

    expect(screen.getByText("Mini-Codex")).toBeInTheDocument();
    expect(screen.getByText("DeepSeek Harness")).toBeInTheDocument();
    expect(screen.getByText("RAG Control Plane")).toBeInTheDocument();
    expect(screen.getAllByRole("img")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Explore system" })).toHaveAttribute("href", "/rag");
  });
});
