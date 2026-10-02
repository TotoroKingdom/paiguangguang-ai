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
      ["能力", "/#capabilities"],
      ["作品", "/#projects"],
      ["构建", "/#building"],
      ["探索", "/#exploring"],
      ["规划", "/#journey"]
    ] as const;
    expect(within(navigation).getAllByRole("link")).toHaveLength(6);
    for (const [name, href] of anchors) {
      expect(within(navigation).getByRole("link", { name })).toHaveAttribute("href", href);
      expect(document.getElementById(href.split("#")[1])).toBeInTheDocument();
    }
    expect(within(screen.getByRole("banner")).getByRole("link", { name: "联系我" })).toHaveAttribute(
      "href",
      "/#contact"
    );

    for (const text of ["01 / 关于", "02 / 能力", "03 / 作品", "04 / 构建", "05 / 探索", "06 / 规划"]) {
      expect(screen.queryByText(text)).not.toBeInTheDocument();
    }
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("我不太相信AI会沿着一条确定的道路走向未来。");
    expect(screen.queryByText(/可交付的产品|真正有用的产品|欢迎联系我/)).not.toBeInTheDocument();

    const capabilities = screen.getByRole("region", { name: "我的技术栈" });
    expect(within(capabilities).getAllByRole("article")).toHaveLength(4);
    for (const name of ["AI & Agent / AI 与智能体", "Backend / 后端", "Frontend / 前端", "Data & Delivery / 数据与部署"]) {
      expect(within(capabilities).getByRole("heading", { name })).toBeInTheDocument();
    }

    for (const technology of ["LangGraph", "LangChain", "Python", "SQLAlchemy", "Pydantic", "React", "Three.js", "PostgreSQL", "Nginx", "Jenkins / GitHub Actions"]) {
      expect(within(capabilities).getByText(technology)).toBeInTheDocument();
    }

    const journey = screen.getByRole("region", { name: "我的职业生涯规划" });
    const currentHeading = within(journey).getByRole("heading", { name: "AI 智能体工程师", level: 3 });
    const current = currentHeading.closest("li");
    expect(current).toBeInTheDocument();
    expect(current).toHaveAttribute("aria-current", "step");
    const futureHeading = within(journey).getByRole("heading", { name: "AI 智能体架构师", level: 3 });
    const future = futureHeading.closest("li");
    expect(future).toBeInTheDocument();
    expect(future).toHaveTextContent("成长目标");

    const contact = screen.getByRole("region", { name: "保持联系" });
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
