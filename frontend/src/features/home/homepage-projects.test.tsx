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
  it("features the 3D lab, keeps the assistant, and moves RAG to a whole-card entry", () => {
    render(<HomepageProjects />);

    const section = screen.getByRole("region", { name: "我的作品" });
    expect(section).toHaveAttribute("id", "projects");
    expect(within(section).getAllByRole("article")).toHaveLength(3);
    expect(within(section).getAllByText(/BUILT · 阶段已完成/)).toHaveLength(2);
    expect(within(section).getByText(/BUILT · 持续更新/)).toBeInTheDocument();

    expect(within(section).getByRole("heading", { name: "3D 交互实验室" })).toBeInTheDocument();
    expect(within(section).getByRole("heading", { name: "RAG 知识检索系统" })).toBeInTheDocument();
    expect(within(section).getByRole("heading", { name: "智能助手" })).toBeInTheDocument();
    expect(within(section).queryByRole("heading", { name: "办公自动化智能体" })).not.toBeInTheDocument();

    const image = within(section).getByRole("img", { name: /3D 交互实验室的机器人/ });
    expect(image).toBeInTheDocument();
    expect(within(section).getAllByRole("img")).toHaveLength(1);

    const lab = projectCard("3D 交互实验室");
    expect(lab).toHaveClass("brand-project--featured");
    const labLink = within(lab).getByRole("link", { name: /3D 交互实验室.*探索实验室/ });
    expect(labLink).toHaveAttribute("href", "/lab/3d");
    expect(labLink).toHaveClass("brand-project__card-link");
    expect(lab.querySelectorAll("a")).toHaveLength(1);

    const rag = projectCard("RAG 知识检索系统");
    expect(rag).toHaveClass("brand-project--text");
    const ragLink = within(rag).getByRole("link", { name: /RAG 知识检索系统.*查看系统/ });
    expect(ragLink).toHaveAttribute("href", "/rag");
    expect(ragLink).toHaveClass("brand-project__card-link");
    expect(rag.querySelectorAll("a")).toHaveLength(1);
    const assistant = projectCard("智能助手");
    const assistantLink = within(assistant).getByRole("link", { name: /智能助手.*体验原型/ });
    expect(assistantLink).toHaveAttribute("href", "/assistant");
    expect(assistantLink).toHaveClass("brand-project__card-link");
    expect(assistant).toHaveTextContent("交互原型");
    expect(assistant).toHaveTextContent("体验原型");
    expect(assistant.querySelectorAll("a")).toHaveLength(1);
    expect(assistantLink.querySelector("a")).toBeNull();
  });
});

describe("HomepageBuilding", () => {
  it("shows the three building projects without empty or placeholder links", () => {
    render(<HomepageBuilding />);

    const section = screen.getByRole("region", { name: "我正在构建的作品" });
    expect(section).toHaveAttribute("id", "building");
    expect(within(section).getAllByRole("article")).toHaveLength(3);
    expect(within(section).getAllByText(/BUILDING · 在建/)).toHaveLength(3);

    for (const name of ["知识中心", "企业数字员工", "ChatGPT Harness（运行框架）"]) {
      expect(within(section).getByRole("heading", { name })).toBeInTheDocument();
    }

    expect(section.querySelectorAll('a[href=""]')).toHaveLength(0);
    expect(within(section).queryByRole("link")).not.toBeInTheDocument();
  });
});

describe("HomepageExploring", () => {
  it("keeps five external research links without a duplicate robot entry", () => {
    render(<HomepageExploring />);

    const section = screen.getByRole("region", { name: "我正在探索的项目" });
    expect(section).toHaveAttribute("id", "exploring");
    expect(within(section).getAllByRole("article")).toHaveLength(5);
    expect(within(section).getAllByText(/EXPLORING · 研究中/)).toHaveLength(5);
    expect(within(section).queryByRole("heading", { name: "Three.js 智能机器人" })).not.toBeInTheDocument();

    const sources = [
      ["Codex", "OpenAI", "https://github.com/openai/codex"],
      ["DSH（DeepSeek Harness）", "DeepSeek", "https://github.com/deepseek-ai/deepseek-harness"],
      ["Pi", "earendil-works", "https://github.com/earendil-works/pi"],
      ["Hermes", "Nous Research", "https://github.com/NousResearch/hermes-agent"],
      ["PyTorch 学习实践", "Daniel Bourke", "https://github.com/mrdbourke/pytorch-deep-learning"]
    ] as const;

    expect(within(section).queryByText("OpenClaw")).not.toBeInTheDocument();

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
