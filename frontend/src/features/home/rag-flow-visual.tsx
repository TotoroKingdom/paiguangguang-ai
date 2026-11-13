import type { ReactNode } from "react";

import styles from "./rag-flow-visual.module.css";

type Tone = "default" | "blue" | "teal" | "violet" | "amber" | "green";

type DiagramNodeProps = {
  title: string;
  detail?: string;
  eyebrow?: string;
  tone?: Tone;
  children?: ReactNode;
};

function DiagramNode({ title, detail, eyebrow, tone = "default", children }: DiagramNodeProps) {
  return (
    <div className={styles.node} data-tone={tone}>
      {eyebrow ? <span className={styles.nodeEyebrow}>{eyebrow}</span> : null}
      <strong className={styles.nodeTitle}>{title}</strong>
      {detail ? <span className={styles.nodeDetail}>{detail}</span> : null}
      {children}
    </div>
  );
}

function Arrow() {
  return <span className={styles.arrow} aria-hidden="true">→</span>;
}

function DiagramSection({
  index,
  title,
  subtitle,
  children
}: {
  index: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section className={styles.section}>
      <div className={styles.sectionHeading}>
        <div className={styles.sectionHeadingMain}>
          <span className={styles.sectionIndex}>{index}</span>
          <div>
            <h4 className={styles.sectionTitle}>{title}</h4>
            <p className={styles.sectionSubtitle}>{subtitle}</p>
          </div>
        </div>
      </div>
      {children}
    </section>
  );
}

export function RagFlowVisual() {
  return (
    <div className={styles.board}>
      <header className={styles.boardHeader}>
        <div>
          <p className={styles.kicker}><span className={styles.statusDot} /> SYSTEM ARCHITECTURE / RAG</p>
          <h2 className={styles.boardTitle}>RAG 全链路架构</h2>
          <p className={styles.boardSubtitle}>文档入库、混合检索与答案生成。数据流向明确，存储职责清晰。</p>
        </div>
        <div className={styles.headerPills} aria-label="核心技术">
          <span>OSS / MinIO</span><span>MySQL</span><span>Milvus</span>
        </div>
      </header>

      <DiagramSection
        index="01"
        title="文档入库与索引构建"
        subtitle="离线处理 · 所有成功建立索引的 Chunk 都写入 Milvus"
      >
        <div className={styles.scrollRegion} tabIndex={0} role="region" aria-label="文档入库架构图，可横向滚动">
          <div className={styles.ingestFlow}>
            <DiagramNode title="文件上传" eyebrow="SOURCE" detail="PDF · DOCX · TXT" />
            <Arrow />
            <div className={styles.storagePair} aria-label="原始文件与业务信息分开存储">
              <DiagramNode title="OSS / MinIO" eyebrow="FILE STORAGE" detail="完整原始文件" tone="blue" />
              <DiagramNode title="MySQL" eyebrow="BUSINESS DATA" detail="文档信息 · ACL · 版本 · 状态" tone="green" />
            </div>
            <Arrow />
            <DiagramNode title="MQ / 异步任务" detail="可选" />
            <Arrow />
            <DiagramNode title="解析与清洗" detail="提取正文 · 格式归一" />
            <Arrow />
            <DiagramNode title="Chunking" detail="切分产生 N 个 Chunk" />
            <Arrow />
            <DiagramNode title="Chunk 数据" eyebrow="INDEX INPUT" detail="文本 · ID · 检索元数据" tone="amber" />
          </div>
        </div>

        <div className={styles.indexBridge}>
          <div className={styles.bridgeLabel}>
            <span className={styles.bridgeLine} />
            <span>每个 Chunk 同时构建以下检索字段</span>
            <span className={styles.bridgeLine} />
          </div>
          <div className={styles.indexLayout}>
            <div className={styles.indexInputs}>
              <div className={styles.indexMethod} data-tone="violet">
                <span className={styles.methodCode}>01 / SEMANTIC</span>
                <strong>Embedding 模型</strong>
                <span>生成 Dense Vector</span>
              </div>
              <div className={styles.indexMethod} data-tone="amber">
                <span className={styles.methodCode}>02 / KEYWORD</span>
                <strong>Milvus BM25 Function</strong>
                <span>分词并生成 Sparse Vector</span>
              </div>
              <div className={styles.indexMethod} data-tone="blue">
                <span className={styles.methodCode}>03 / CONTENT</span>
                <strong>Chunk 原文与元数据</strong>
                <span>chunk_text · ID · ACL 检索字段</span>
              </div>
            </div>
            <div className={styles.converge} aria-hidden="true">
              <span /><span /><span />
            </div>
            <div className={styles.milvusCard}>
              <span className={styles.milvusLabel}>VECTOR DATABASE / MILVUS</span>
              <strong className={styles.milvusTitle}>Milvus Collection</strong>
              <span className={styles.milvusSubtitle}>全部成功索引的 Chunk · N 条记录</span>
              <div className={styles.milvusFields}>
                <span>chunk_id / document_id</span>
                <span>chunk_text（切块原文）</span>
                <span>dense_vector</span>
                <span>sparse_vector</span>
                <span>检索元数据 / ACL 字段</span>
              </div>
            </div>
          </div>
        </div>
        <p className={styles.note}><strong>存储职责</strong> OSS 保留完整原始文件；MySQL 管理业务信息及权限；Milvus 存储已索引的全部 Chunk 文本和检索向量。</p>
      </DiagramSection>

      <DiagramSection
        index="02"
        title="混合检索与候选融合"
        subtitle="在线查询 · MySQL 的权限条件同时作用于 Dense / BM25 两条检索路径"
      >
        <div className={styles.scrollRegion} tabIndex={0} role="region" aria-label="在线混合检索架构图，可横向滚动">
          <div className={styles.queryFlow}>
            <DiagramNode title="用户问题" eyebrow="REQUEST" detail="保留原始 Query" />
            <Arrow />
            <DiagramNode title="Query Rewrite" detail="问题重写 · 可选" />
            <Arrow />
            <DiagramNode title="ACL 条件生成" detail="从 MySQL 获取授权范围" tone="green" />
            <Arrow />
            <div className={styles.retrievalPair} aria-label="并行双路检索">
              <DiagramNode title="Dense Search" eyebrow="VECTOR" detail="Query Embedding + ACL 过滤" tone="violet" />
              <DiagramNode title="BM25 Search" eyebrow="KEYWORD" detail="关键词匹配 + ACL 过滤" tone="amber" />
            </div>
            <Arrow />
            <DiagramNode title="RRF 融合" detail="合并两路结果的排名" tone="teal" />
          </div>
        </div>
        <div className={styles.transition} aria-hidden="true"><span /> RRF 候选结果 <span>↓</span></div>
        <div className={styles.scrollRegion} tabIndex={0} role="region" aria-label="答案生成架构图，可横向滚动">
          <div className={styles.answerFlow}>
            <DiagramNode title="Top N" eyebrow="RECALL" detail="候选集合 · 例如 50 条" />
            <Arrow />
            <DiagramNode title="Rerank" detail="交叉编码重排序" tone="violet" />
            <Arrow />
            <DiagramNode title="Top K" detail="最终片段 · 例如 5 条" />
            <Arrow />
            <DiagramNode title="Prompt 组装" detail="原始问题 + Top K + 引用" tone="blue" />
            <Arrow />
            <DiagramNode title="LLM" detail="生成答案与来源引用" tone="violet" />
            <Arrow />
            <DiagramNode title="答案校验" detail="返回用户" tone="green" />
          </div>
        </div>
        <p className={styles.note}><strong>查询原则</strong> 原始问题进入 Prompt；重写后的问题用于检索。Top N / Top K 只是单次查询的筛选结果，不代表 Milvus 只存这些 Chunk。</p>
      </DiagramSection>
      <div className={styles.boardFooter}>
        <span><i className={styles.footerDot} /> ARCHITECTURE REFERENCE</span>
        <span>INDEXING → RETRIEVAL → GENERATION</span>
      </div>
    </div>
  );
}
