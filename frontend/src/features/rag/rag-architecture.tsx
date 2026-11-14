import { Fragment, type ReactNode } from "react";
import Link from "next/link";

import { ragChapters, ragDataLoop, type RagStation, type RagStationKind } from "./rag-architecture-data";
import styles from "./rag-architecture.module.css";

type ConnectorTone = "default" | "mint" | "indigo";

function StationGlyph({ kind }: { kind: RagStationKind }) {
  const common = {
    "aria-hidden": true,
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    strokeWidth: 1.7,
    viewBox: "0 0 24 24"
  };

  switch (kind) {
    case "source":
      return <svg {...common}><path d="M8 3h7l4 4v14H8z" /><path d="M15 3v4h4M5 7v14h10M11 11h5M11 15h5" /></svg>;
    case "storage":
      return <svg {...common}><ellipse cx="12" cy="6" rx="7" ry="3" /><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" /></svg>;
    case "process":
      return <svg {...common}><path d="M3 5h7l3 3-3 3H3zM10 13h7l3 3-3 3h-7z" /><path d="M10 8h4M7 16h4" /></svg>;
    case "index":
      return <svg {...common}><path d="M4 7h16M4 12h11M4 17h14" /><circle cx="19" cy="12" r="1.5" /><circle cx="8" cy="17" r="1.5" /></svg>;
    case "query":
      return <svg {...common}><path d="M4 5h16v11H9l-5 4z" /><path d="M8 9h8M8 12h5" /></svg>;
    case "guard":
      return <svg {...common}><path d="M12 3 5 6v5c0 4.4 2.9 8 7 10 4.1-2 7-5.6 7-10V6z" /><path d="m9 12 2 2 4-4" /></svg>;
    case "retrieval":
      return <svg {...common}><path d="M4 8h13M14 5l3 3-3 3M4 16h13M14 13l3 3-3 3" /></svg>;
    case "fusion":
      return <svg {...common}><path d="M4 5h16l-6 7v7l-4-2v-5z" /></svg>;
    case "prompt":
      return <svg {...common}><rect x="4" y="4" width="12" height="12" rx="2" /><path d="M8 8h12v12H8zM11 12h5M11 15h3" /></svg>;
    case "model":
      return <svg {...common}><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /><path d="M12 3v3M12 18v3M3 12h3M18 12h3" /></svg>;
    case "answer":
      return <svg {...common}><path d="M5 8h6v6H7v3H4v-5c0-2.2.4-3.6 1-4ZM14 8h6v6h-4v3h-3v-5c0-2.2.4-3.6 1-4Z" /></svg>;
    case "loop":
      return <svg {...common}><path d="M20 8a8 8 0 1 0 1 6" /><path d="M20 3v5h-5" /></svg>;
  }
}

function StationCard({ station, compact = false }: { station: RagStation; compact?: boolean }) {
  return (
    <article
      className={styles.card}
      data-accent={station.accent}
      data-compact={compact || undefined}
      data-featured={station.featured || undefined}
      data-station-kind={station.kind}
      aria-labelledby={`rag-station-${station.id}`}
    >
      <div className={styles.cardMeta}>
        <span className={styles.cardStep}>{station.step}</span>
        <span className={styles.cardEyebrow}>{station.eyebrow}</span>
      </div>

      <div className={styles.cardBody}>
        <span className={styles.glyphWrap} aria-hidden="true">
          <StationGlyph kind={station.kind} />
        </span>
        <div className={styles.cardCopy}>
          <h3 id={`rag-station-${station.id}`} className={styles.cardTitle}>{station.title}</h3>
          <p className={styles.cardDetail}>{station.detail}</p>
        </div>
      </div>

      {station.kind === "index" ? (
        <div className={styles.indexMeters} aria-hidden="true">
          <span /><span /><span />
        </div>
      ) : null}
      {station.kind === "retrieval" ? (
        <div className={styles.retrievalLanes} aria-hidden="true">
          <span>Dense</span><span>BM25</span>
        </div>
      ) : null}
      {station.kind === "fusion" ? (
        <div className={styles.fusionChain} aria-hidden="true">
          <span>RRF</span><i /><span>Rerank</span>
        </div>
      ) : null}
      {station.kind === "model" ? <span className={styles.modelHalo} aria-hidden="true" /> : null}
      {station.kind === "answer" ? (
        <div className={styles.citationLines} aria-hidden="true">
          <span /><span /><span />
        </div>
      ) : null}

      {station.chips?.length ? (
        <ul className={styles.chips} aria-label={`${station.title} 关键字段`}>
          {station.chips.map((chip) => <li key={chip}>{chip}</li>)}
        </ul>
      ) : null}
    </article>
  );
}

function Connector({ tone = "default", dashed = false }: { tone?: ConnectorTone; dashed?: boolean }) {
  return <span className={styles.connector} data-dashed={dashed || undefined} data-tone={tone} aria-hidden="true" />;
}

function StationRow({ stations }: { stations: RagStation[] }) {
  return (
    <div className={styles.stationRow}>
      {stations.map((station, index) => (
        <Fragment key={station.id}>
          <StationCard station={station} />
          {index < stations.length - 1 ? <Connector /> : null}
        </Fragment>
      ))}
    </div>
  );
}

function Chapter({ chapter, children }: { chapter: (typeof ragChapters)[number]; children?: ReactNode }) {
  return (
    <section className={styles.chapter} aria-labelledby={`rag-chapter-${chapter.id}`}>
      <header className={styles.chapterHeader}>
        <span className={styles.chapterIndex}>{chapter.index}</span>
        <div>
          <h2 id={`rag-chapter-${chapter.id}`} className={styles.chapterTitle}>{chapter.title}</h2>
          <p className={styles.chapterDescription}>{chapter.description}</p>
        </div>
      </header>
      <StationRow stations={chapter.stations} />
      {children}
    </section>
  );
}

export function RagArchitecture() {
  return (
    <>
      <header className={styles.pageHeader}>
        <div className={styles.headerCopy}>
          <p className={styles.breadcrumb}>
            <Link href="/#projects">作品</Link>
            <span aria-hidden="true">/</span>
            <span>RAG</span>
          </p>
          <h1 className={styles.title}>RAG 知识检索系统</h1>
          <p className={styles.lede}>
            从文档入库、索引构建，到混合检索、重排与引用生成。实线表示数据流，虚线表示权限约束与回环。
          </p>
          <Link className={styles.backLink} href="/">← 返回首页</Link>
        </div>

        <aside className={styles.legend} aria-label="读图说明">
          <p className={styles.legendTitle}>读图</p>
          <ul>
            <li><span className={styles.legendLine} data-tone="solid" aria-hidden="true" />实线 · 数据流</li>
            <li><span className={styles.legendLine} data-tone="dashed" aria-hidden="true" />虚线 · 权限与回环</li>
            <li><span className={styles.legendIndex}>01</span>离线索引</li>
            <li><span className={styles.legendIndex}>02</span>在线检索</li>
            <li><span className={styles.legendIndex}>03</span>生成与回流</li>
          </ul>
        </aside>
      </header>

      <figure className={styles.figure} aria-labelledby="rag-flow-caption">
        <div className={styles.canvas}>
          <span className={styles.returnRail} aria-hidden="true" />
          <Chapter chapter={ragChapters[0]}>
            <div className={styles.subLoop} role="group" aria-label="数据更新回环">
              <div className={styles.loopMeta}>
                <span className={styles.loopBadge} data-tone="mint">数据更新回环</span>
                <span className={styles.loopDescription}>文档变更后同步版本、状态与索引。</span>
              </div>
              <div className={styles.loopRow}>
                {ragDataLoop.map((station) => (
                  <Fragment key={station.id}>
                    <StationCard station={station} compact />
                    <Connector tone="mint" dashed />
                  </Fragment>
                ))}
                <span className={styles.loopReturn} aria-hidden="true">↺</span>
              </div>
              <p className={styles.loopFoot}>回到索引构建 · 与主索引保持一致</p>
            </div>
          </Chapter>

          <Chapter chapter={ragChapters[1]} />

          <Chapter chapter={ragChapters[2]}>
            <div className={styles.qualityLoop} role="group" aria-label="质量反馈回环">
              <div className={styles.qualityTrack}>
                <span className={styles.loopBadge} data-tone="indigo">质量反馈回环</span>
                <span className={styles.qualityLine} aria-hidden="true" />
                <span className={styles.qualityLabel}>知识更新 · 重新索引</span>
                <span className={styles.qualityReturn} aria-hidden="true">↺ 回到 01</span>
              </div>
              <p className={styles.loopNote}>虚线为治理 / 优化机制，不代表每次请求自动回写知识库。</p>
            </div>
          </Chapter>
        </div>
        <figcaption id="rag-flow-caption" className={styles.caption}>
          RAG 链路图 · 01 → 02 → 03；虚线表示数据治理与质量优化回环。
        </figcaption>
      </figure>
    </>
  );
}
