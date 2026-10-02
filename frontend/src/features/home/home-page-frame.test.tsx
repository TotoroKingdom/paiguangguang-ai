import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HomePageFrame } from "./home-page-frame";

describe("homepage visual scope", () => {
  it("limits the spatial design and skip link to the homepage", () => {
    const { container, rerender } = render(<HomePageFrame activePage="home"><h1>Home</h1></HomePageFrame>);
    expect(container.querySelector(".home-page--spatial")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "跳到主要内容" })).toHaveAttribute("href", "#home-content");
    expect(screen.getByRole("main")).toHaveAttribute("id", "home-content");

    rerender(<HomePageFrame activePage="system" mainClassName="rag-main"><h1>RAG</h1></HomePageFrame>);
    expect(container.querySelector(".home-page--spatial")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "跳到主要内容" })).not.toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("rag-main");
  });

  it("keeps the homepage section anchors available from the RAG page", () => {
    render(<HomePageFrame activePage="system" mainClassName="rag-main"><h1>RAG</h1></HomePageFrame>);

    const navigation = screen.getByRole("navigation", { name: "主导航" });
    const anchors = [
      ["关于", "/#hero"],
      ["作品", "/#projects"],
      ["研究", "/#exploring"],
      ["成长", "/#journey"]
    ] as const;

    expect(within(navigation).getAllByRole("link")).toHaveLength(4);
    for (const [name, href] of anchors) {
      expect(within(navigation).getByRole("link", { name })).toHaveAttribute("href", href);
    }
  });
});
