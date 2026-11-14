import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HomePageFrame } from "./home-page-frame";

describe("homepage visual scope", () => {
  it("limits the spatial design and skip link to the homepage", () => {
    const { container, rerender } = render(<HomePageFrame activePage="home"><h1>Home</h1></HomePageFrame>);
    expect(container.querySelector(".home-page--spatial")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "跳到主要内容" })).toHaveAttribute("href", "#home-content");
    expect(screen.getByRole("main")).toHaveAttribute("id", "home-content");

    rerender(<HomePageFrame activePage="rag" mainClassName="rag-main"><h1>RAG</h1></HomePageFrame>);
    expect(container.querySelector(".home-page--spatial")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "跳到主要内容" })).not.toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("rag-main");
  });

  it("allows a page to opt into the spatial theme explicitly", () => {
    const { container } = render(
      <HomePageFrame activePage="rag" theme="spatial" mainClassName="rag-main"><h1>RAG</h1></HomePageFrame>
    );
    expect(container.querySelector(".home-page--spatial")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "跳到主要内容" })).not.toBeInTheDocument();
  });

  it("keeps the homepage navigation available from the RAG page", () => {
    render(<HomePageFrame activePage="rag" theme="spatial" mainClassName="rag-main"><h1>RAG</h1></HomePageFrame>);

    const navigation = screen.getByRole("navigation", { name: "主导航" });
    const anchors = [
      ["关于", "/#hero"],
      ["能力", "/#capabilities"],
      ["作品", "/#projects"],
      ["构建", "/#building"],
      ["探索", "/#exploring"],
      ["规划", "/#journey"]
    ] as const;

    expect(within(navigation).getAllByRole("link")).toHaveLength(6);
    for (const [name, href] of anchors) {
      expect(within(navigation).getByRole("link", { name })).toHaveAttribute("href", href);
    }
  });
});
