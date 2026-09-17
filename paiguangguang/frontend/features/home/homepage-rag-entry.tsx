import { ArrowUpRightIcon, DatabaseIcon, WorkflowIcon } from "@/components/icons";

export function HomepageRagEntry() {
  return (
    <section id="rag-flow" className="home-section rag-entry-section scroll-mt-24">
      <a href="/rag" className="rag-entry-card">
        <div className="rag-entry-card__visual" aria-hidden="true">
          <div className="rag-entry-card__grid" />
          <div className="rag-entry-card__node rag-entry-card__node--input">
            <DatabaseIcon size={17} />
            <span>DOCUMENTS</span>
          </div>
          <div className="rag-entry-card__node rag-entry-card__node--middle">
            <WorkflowIcon size={20} />
            <span>RETRIEVAL</span>
          </div>
          <div className="rag-entry-card__node rag-entry-card__node--output">
            <span className="rag-entry-card__pulse" />
            <span>ANSWER</span>
          </div>
          <span className="rag-entry-card__line rag-entry-card__line--one" />
          <span className="rag-entry-card__line rag-entry-card__line--two" />
          <span className="rag-entry-card__caption">TRACEABLE / RAG CONTROL PLANE</span>
        </div>

        <div className="rag-entry-card__copy">
          <div>
            <p className="eyebrow">System map / 01</p>
            <h2 className="section-title">让每一次回答，都有迹可循</h2>
            <p className="section-description">
              入库、召回、重排、生成和引用，每一步都可以被看见，也可以被验证。
            </p>
          </div>
          <span className="rag-entry-card__action">
            打开完整 RAG 链路
            <ArrowUpRightIcon size={17} />
          </span>
        </div>
      </a>
    </section>
  );
}
