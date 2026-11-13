import Link from "next/link";

import { HomePageFrame } from "@/features/home/home-page-frame";
import { RagFlowVisual } from "@/features/home/rag-flow-visual";

export const metadata = {
  title: "RAG 系统架构 · TotoroKingdom",
  description: "从 OSS / MySQL 文档入库到 Milvus 混合检索、RRF、Rerank 与可引用答案生成的完整 RAG 架构。"
};

export default function RagPage() {
  return (
    <div className="rag-page">
      <HomePageFrame
        activePage="system"
        footerLabel="TG / RAG ARCHITECTURE"
        footerCopy="Knowledge infrastructure, clearly mapped."
        mainClassName="rag-main"
      >
        <section className="rag-intro">
          <div>
            <p className="hero-kicker">
              <span className="hero-kicker__dot" />
              RAG ARCHITECTURE <span className="hero-kicker__year">/ KNOWLEDGE SYSTEM</span>
            </p>
            <h1 className="rag-intro__title" style={{ fontSize: "clamp(2.9rem, 5.5vw, 5.3rem)" }}>
              让知识流转，
              <br />
              <span>清晰可见。</span>
            </h1>
            <p className="rag-intro__copy">
              从文件存储、数据切块与索引构建，到权限约束下的混合检索、结果重排和引用生成，一张图呈现完整的 RAG 链路。
            </p>
          </div>

          <Link href="/" className="home-button home-button--glass rag-intro__back">
            ← 回到首页
          </Link>
        </section>

        <section className="rag-board-section" aria-label="RAG 全链路架构">
          <RagFlowVisual />
        </section>
      </HomePageFrame>
    </div>
  );
}
