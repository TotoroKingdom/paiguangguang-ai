export type RagStationKind =
  | "source"
  | "storage"
  | "process"
  | "index"
  | "query"
  | "guard"
  | "retrieval"
  | "fusion"
  | "prompt"
  | "model"
  | "answer"
  | "loop";

export type RagAccent = "indigo" | "lavender" | "cyan" | "mint" | "amber";

export type RagStation = {
  id: string;
  step: string;
  eyebrow: string;
  title: string;
  detail: string;
  kind: RagStationKind;
  chips?: string[];
  accent?: RagAccent;
  featured?: boolean;
};

export type RagChapter = {
  id: string;
  index: string;
  title: string;
  description: string;
  stations: RagStation[];
};

export const ragChapters: RagChapter[] = [
  {
    id: "offline-index",
    index: "01",
    title: "离线索引",
    description: "原始文件、业务元数据与 Chunk 索引分别存储，最终写入 Milvus。",
    stations: [
      {
        id: "upload",
        step: "01",
        eyebrow: "SOURCE",
        title: "文件上传",
        detail: "接收文件并创建入库任务",
        kind: "source",
        chips: ["PDF · DOCX · TXT", "异步任务（可选）"],
        accent: "indigo"
      },
      {
        id: "object-storage",
        step: "02",
        eyebrow: "FILE STORAGE",
        title: "OSS / MinIO",
        detail: "保留完整原始文件",
        kind: "storage",
        chips: ["原始文件"],
        accent: "cyan"
      },
      {
        id: "parse-chunk",
        step: "03",
        eyebrow: "PREPARE",
        title: "解析与切分",
        detail: "解析 · 清洗 · Chunk 切分",
        kind: "process",
        chips: ["页码", "语义边界", "overlap"],
        accent: "amber"
      },
      {
        id: "index-build",
        step: "04",
        eyebrow: "INDEX",
        title: "索引构建",
        detail: "同一 Chunk 生成三类检索字段",
        kind: "index",
        chips: ["Dense Embedding", "BM25 Sparse", "Metadata"],
        accent: "lavender"
      },
      {
        id: "milvus",
        step: "05",
        eyebrow: "VECTOR DB",
        title: "Milvus",
        detail: "全部已索引 Chunk，不等于 Top K",
        kind: "storage",
        chips: ["chunk_text", "dense_vector", "sparse_vector", "ACL"],
        accent: "cyan",
        featured: true
      }
    ]
  },
  {
    id: "online-retrieval",
    index: "02",
    title: "在线检索",
    description: "MySQL ACL 同时约束 Dense 与 BM25 两条检索路径。",
    stations: [
      {
        id: "question",
        step: "01",
        eyebrow: "REQUEST",
        title: "用户问题",
        detail: "保留原始 Query",
        kind: "query",
        chips: ["原始问题"],
        accent: "indigo"
      },
      {
        id: "rewrite",
        step: "02",
        eyebrow: "REWRITE",
        title: "查询改写",
        detail: "改写用于检索，原始问题进入 Prompt",
        kind: "query",
        chips: ["可选"],
        accent: "lavender"
      },
      {
        id: "acl",
        step: "03",
        eyebrow: "ACCESS",
        title: "权限过滤",
        detail: "从 MySQL 获取授权范围",
        kind: "guard",
        chips: ["来源 MySQL", "ACL"],
        accent: "mint"
      },
      {
        id: "hybrid",
        step: "04",
        eyebrow: "HYBRID",
        title: "双路检索",
        detail: "ACL 同时作用于两路",
        kind: "retrieval",
        accent: "indigo"
      },
      {
        id: "fusion",
        step: "05",
        eyebrow: "RANK",
        title: "融合与重排",
        detail: "RRF 融合后交叉编码重排",
        kind: "fusion",
        chips: ["Top N ≈ 50", "Top K ≈ 5"],
        accent: "amber"
      }
    ]
  },
  {
    id: "generate-feedback",
    index: "03",
    title: "生成与回流",
    description: "检索结果组装为 Prompt，生成带引用的答案；评估结果进入知识更新。",
    stations: [
      {
        id: "prompt",
        step: "01",
        eyebrow: "PROMPT",
        title: "Prompt 组装",
        detail: "原始问题 + Top K + 引用",
        kind: "prompt",
        chips: ["原始问题", "Top K"],
        accent: "indigo"
      },
      {
        id: "llm",
        step: "02",
        eyebrow: "MODEL",
        title: "LLM 生成",
        detail: "基于检索上下文生成答案",
        kind: "model",
        chips: ["DeepSeek / LLM"],
        accent: "lavender",
        featured: true
      },
      {
        id: "answer",
        step: "03",
        eyebrow: "OUTPUT",
        title: "答案与引用",
        detail: "返回来源文档与 chunk",
        kind: "answer",
        chips: ["来源文档", "chunk_id", "校验"],
        accent: "mint"
      },
      {
        id: "feedback",
        step: "04",
        eyebrow: "LOOP",
        title: "评估与反馈",
        detail: "质量结果进入知识更新",
        kind: "loop",
        chips: ["质量", "回归"],
        accent: "indigo"
      }
    ]
  }
];

export const ragDataLoop: RagStation[] = [
  {
    id: "document-change",
    step: "L1",
    eyebrow: "LIFECYCLE",
    title: "文档变更",
    detail: "新增 · 更新 · 删除",
    kind: "loop",
    chips: ["生命周期"],
    accent: "mint"
  },
  {
    id: "mysql",
    step: "L2",
    eyebrow: "BUSINESS DATA",
    title: "MySQL",
    detail: "文档信息 · 版本 · ACL · 状态",
    kind: "storage",
    chips: ["版本", "ACL"],
    accent: "mint"
  },
  {
    id: "reindex",
    step: "L3",
    eyebrow: "REINDEX",
    title: "重建或失效",
    detail: "旧索引失效，新索引重建",
    kind: "process",
    chips: ["幂等"],
    accent: "mint"
  },
  {
    id: "milvus-sync",
    step: "L4",
    eyebrow: "SYNC",
    title: "Milvus 同步",
    detail: "与主索引保持一致",
    kind: "storage",
    chips: ["同步"],
    accent: "cyan"
  }
];
