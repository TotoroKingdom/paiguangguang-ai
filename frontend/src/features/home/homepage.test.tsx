import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/three/ai-core", () => ({
  AICore: () => <div data-testid="ai-core-mock" />
}));

import { Homepage } from "./homepage";

describe("Homepage", () => {
  it("renders the page in the intended section order with accessible navigation and content", () => {
    render(<Homepage />);

    const main = screen.getByRole("main");
    const sectionIds = Array.from(main.children)
      .filter((element): element is HTMLElement => element.tagName === "SECTION")
      .map((section) => section.id);
    expect(sectionIds).toEqual(["hero", "capabilities", "projects", "building", "exploring", "journey", "contact"]);
    expect(screen.getByTestId("ai-core-mock")).toBeInTheDocument();

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
    expect(within(screen.getByRole("banner")).getByRole("link", { name: /GitHub/ })).toHaveAttribute(
      "href",
      "https://github.com/TotoroKingdom"
    );

    const capabilities = screen.getByRole("region", { name: "我能构建什么" });
    expect(within(capabilities).getAllByRole("article")).toHaveLength(4);
    for (const name of ["智能体工程", "RAG 与知识系统", "后端与 AI 基础设施", "AI 产品工程"]) {
      expect(within(capabilities).getByRole("heading", { name })).toBeInTheDocument();
    }

    const journey = screen.getByRole("region", { name: "从构建系统，到设计架构" });
    const currentHeading = within(journey).getByRole("heading", { name: "AI 智能体工程师", level: 3 });
    const current = currentHeading.closest("li");
    expect(current).toBeInTheDocument();
    expect(current).toHaveAttribute("aria-current", "step");
    const futureHeading = within(journey).getByRole("heading", { name: "AI 智能体架构师", level: 3 });
    const future = futureHeading.closest("li");
    expect(future).toBeInTheDocument();
    expect(future).toHaveTextContent("成长目标");

    const contact = screen.getByRole("region", { name: "一起把 AI，做成真正有用的产品。" });
    expect(within(contact).getByRole("link", { name: /邮箱/ })).toHaveAttribute(
      "href",
      "mailto:totorokingdom@foxmail.com"
    );
    expect(within(contact).getByRole("link", { name: /GitHub/ })).toHaveAttribute(
      "href",
      "https://github.com/TotoroKingdom"
    );
  });
});
