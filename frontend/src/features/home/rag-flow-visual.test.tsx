import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RagFlowVisual } from "./rag-flow-visual";

describe("RagFlowVisual", () => {
  it("explains OSS, MySQL and Milvus responsibilities without losing the complete Chunk payload", () => {
    render(<RagFlowVisual />);

    expect(screen.getByRole("heading", { name: "RAG 全链路架构" })).toBeInTheDocument();
    expect(screen.getByText("完整原始文件")).toBeInTheDocument();
    expect(screen.getByText("文档信息 · ACL · 版本 · 状态")).toBeInTheDocument();
    expect(screen.getByText("Milvus Collection")).toBeInTheDocument();

    for (const field of ["chunk_text（切块原文）", "dense_vector", "sparse_vector"]) {
      expect(screen.getByText(field)).toBeInTheDocument();
    }

    expect(screen.getByText(/全部成功索引的 Chunk · N 条记录/)).toBeInTheDocument();
  });

  it("shows ACL-filtered hybrid retrieval, RRF, Rerank and original-question Prompt assembly", () => {
    render(<RagFlowVisual />);

    for (const step of ["Query Rewrite", "ACL 条件生成", "Dense Search", "BM25 Search", "RRF 融合", "Rerank", "Top K", "Prompt 组装"]) {
      expect(screen.getByText(step)).toBeInTheDocument();
    }

    expect(screen.getByText("Query Embedding + ACL 过滤")).toBeInTheDocument();
    expect(screen.getByText("关键词匹配 + ACL 过滤")).toBeInTheDocument();
    expect(screen.getByText("原始问题 + Top K + 引用")).toBeInTheDocument();
    expect(screen.queryByText(/Prompt Injection|输入护栏|防御提示词/)).not.toBeInTheDocument();
  });
});
