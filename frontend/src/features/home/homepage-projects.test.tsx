import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HomepageBuilding, HomepageExploring, HomepageProjects } from "./homepage-projects";

function projectCard(name: string) {
  const heading = screen.getByRole("heading", { name, level: 3 });
  const card = heading.closest("article");
  expect(card).toBeInTheDocument();
  return card as HTMLElement;
}

describe("HomepageProjects", () => {
  it("presents the three completed systems and links only the RAG explanation", () => {
    render(<HomepageProjects />);

    const section = screen.getByRole("region", { name: "我的作品" });
    expect(section).toHaveAttribute("id", "projects");
    expect(within(section).getAllByRole("article")).toHaveLength(3);
    expect(within(section).getAllByText(/BUILT · 阶段已完成/)).toHaveLength(3);

    expect(within(section).getByRole("heading", { name: "RAG 知识检索系统" })).toBeInTheDocument();
    expect(within(section).getByRole("heading", { name: "AI 聊天机器人" })).toBeInTheDocument();
    expect(within(section).getByRole("heading", { name: "办公自动化智能体" })).toBeInTheDocument();

    const image = within(section).getByRole("img", { name: "RAG 知识检索系统链路说明截图" });
    expect(image).toBeInTheDocument();
    expect(within(section).getAllByRole("img")).toHaveLength(1);

    const ragLink = within(projectCard("RAG 知识检索系统")).getByRole("link", { name: /查看系统说明/ });
    expect(ragLink).toHaveAttribute("href", "/rag");
    expect(within(projectCard("AI 聊天机器人")).queryByRole("link")).not.toBeInTheDocument();
    expect(within(projectCard("办公自动化智能体")).queryByRole("link")).not.toBeInTheDocument();
  });
});

describe("HomepageBuilding", () => {
  it("shows the three building projects without empty or placeholder links", () => {
    render(<HomepageBuilding />);

    const section = screen.getByRole("region", { name: "我正在构建的作品" });
    expect(section).toHaveAttribute("id", "building");
    expect(within(section).getAllByRole("article")).toHaveLength(3);
    expect(within(section).getAllByText(/BUILDING · 在建/)).toHaveLength(3);

    for (const name of ["知识平台", "企业数字员工", "ChatGPT Harness（运行框架）"]) {
      expect(within(section).getByRole("heading", { name })).toBeInTheDocument();
    }

    expect(section.querySelectorAll('a[href=""]')).toHaveLength(0);
    expect(within(section).queryByRole("link")).not.toBeInTheDocument();
  });
});

describe("HomepageExploring", () => {
  it("uses one external semantic card link for each official research source", () => {
    render(<HomepageExploring />);

    const section = screen.getByRole("region", { name: "我正在探索的项目" });
    expect(section).toHaveAttribute("id", "exploring");
    expect(within(section).getAllByRole("article")).toHaveLength(6);
    expect(within(section).getAllByText(/EXPLORING · 研究中/)).toHaveLength(6);

    const sources = [
      ["Codex", "OpenAI", "https://github.com/openai/codex"],
      ["DeepSeek Harness", "DeepSeek", "https://github.com/deepseek-ai/deepseek-harness"],
      ["Pi", "earendil-works", "https://github.com/earendil-works/pi"],
      ["Hermes", "Nous Research", "https://github.com/NousResearch/hermes-agent"],
      ["OpenClaw", "OpenClaw", "https://github.com/openclaw/openclaw"],
      ["PyTorch 学习实践", "Daniel Bourke", "https://github.com/mrdbourke/pytorch-deep-learning"]
    ] as const;

    for (const [name, source, href] of sources) {
      const card = projectCard(name);
      const link = within(card).getByRole("link");

      expect(link).toHaveAttribute("href", href);
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
      expect(link).toContainElement(within(card).getByRole("heading", { name, level: 3 }));
      expect(within(card).getByText(`来源 · ${source}`)).toBeInTheDocument();
      expect(link.querySelectorAll("a, button, input, select, textarea")).toHaveLength(0);
    }
  });
});
