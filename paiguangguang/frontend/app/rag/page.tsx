import { HomePageFrame } from "@/features/home/home-page-frame";
import { ragIngestionSteps, ragQuerySteps } from "@/features/home/homepage-data";
import { RagFlowVisual } from "@/features/home/rag-flow-visual";

export const metadata = {
  title: "RAG Control Plane · TotoroKingdom",
  description: "一条可追踪、可验证的 RAG 链路"
};

export default function RagPage() {
  return (
    <div className="rag-page">
      <HomePageFrame
        activePage="system"
        footerLabel="TG / RAG CONTROL PLANE"
        footerCopy="Every step can be inspected."
        mainClassName="rag-main"
      >
          <section className="rag-intro">
            <div>
              <p className="hero-kicker">
                <span className="hero-kicker__dot" />
                RAG CONTROL PLANE <span className="hero-kicker__year">/ TRACEABLE SYSTEM</span>
              </p>
              <h1 className="rag-intro__title">
                让每一次回答，
                <br />
                <span>都有迹可循。</span>
              </h1>
              <p className="rag-intro__copy">
                从原始文档、混合召回到带引用的最终回答，把一条复杂的 RAG 链路拆成可以观察、验证和持续优化的系统。
              </p>
            </div>

            <a href="/" className="home-button home-button--glass rag-intro__back">
              ← 回到首页
            </a>
          </section>

          <section className="rag-board-section" aria-label="RAG 完整链路">
            <RagFlowVisual ingestionSteps={ragIngestionSteps} querySteps={ragQuerySteps} />
          </section>
      </HomePageFrame>
    </div>
  );
}
