import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RagArchitecture } from "./rag-architecture";

describe("RagArchitecture", () => {
  it("presents the three flow chapters and their key responsibilities", () => {
    render(<RagArchitecture />);

    expect(screen.getByRole("heading", { level: 1, name: "RAG 知识检索系统" })).toBeInTheDocument();
    for (const chapter of ["离线索引", "在线检索", "生成与回流"]) {
      expect(screen.getByRole("heading", { level: 2, name: chapter })).toBeInTheDocument();
    }

    expect(screen.getByRole("heading", { level: 3, name: "OSS / MinIO" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Milvus" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "双路检索" })).toBeInTheDocument();
    expect(screen.getByText("Top N ≈ 50")).toBeInTheDocument();
    expect(screen.getByText("Top K ≈ 5")).toBeInTheDocument();
    expect(screen.getByText("原始问题 + Top K + 引用")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "答案与引用" })).toBeInTheDocument();
  });

  it("renders distinct data and quality loops with their boundaries", () => {
    render(<RagArchitecture />);

    const dataLoop = screen.getByRole("group", { name: "数据更新回环" });
    for (const label of ["文档变更", "MySQL", "重建或失效", "Milvus 同步"]) {
      expect(within(dataLoop).getByRole("heading", { level: 3, name: label })).toBeInTheDocument();
    }

    const qualityLoop = screen.getByRole("group", { name: "质量反馈回环" });
    expect(within(qualityLoop).getByText("知识更新 · 重新索引")).toBeInTheDocument();
    expect(within(qualityLoop).getByText(/不代表每次请求自动回写知识库/)).toBeInTheDocument();

    expect(screen.getByRole("link", { name: "作品" })).toHaveAttribute("href", "/#projects");
    expect(screen.getByRole("link", { name: /返回首页/ })).toHaveAttribute("href", "/");
  });
});
