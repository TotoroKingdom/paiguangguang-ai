import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HomepageProjects } from "./homepage-projects";

describe("HomepageProjects", () => {
  it("shows portfolio cases without links to removed business routes", () => {
    render(<HomepageProjects />);

    expect(screen.getByText("Knowledge System")).toBeInTheDocument();
    expect(screen.getByText("Agent Workflow")).toBeInTheDocument();
    expect(screen.getByText("AI Office Automation")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
