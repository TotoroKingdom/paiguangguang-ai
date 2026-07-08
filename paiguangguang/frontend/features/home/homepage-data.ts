export type RagFlowStep = {
  id: string;
  title: string;
  description: string;
  kind: "ingestion" | "query" | "branch" | "system" | "ai" | "storage";
};

export type OverviewCard = {
  title: string;
  description: string;
  accent: "green" | "purple" | "blue" | "pink";
};

export type TechStackItem = {
  name: string;
  category: "frontend" | "backend" | "ai" | "storage" | "workflow" | "delivery";
};

export type ProjectCard = {
  name: string;
  href: string;
  status: string;
  description: string;
  tags: string[];
};

export type RoadmapStage = {
  stage: string;
  title: string;
  description: string;
};

export type ContactLink = {
  label: string;
  value: string;
  href: string;
};

export const ragIngestionSteps: RagFlowStep[] = [
  {
    id: "knowledge-base",
    title: "企业知识库",
    description: "业务文档进入 RAG 入库链路。",
    kind: "ingestion"
  },
  {
    id: "cleaning",
    title: "数据清洗",
    description: "整理格式、去噪、保留可追踪信息。",
    kind: "ingestion"
  },
  {
    id: "upload",
    title: "文件上传",
    description: "接收文档并创建处理任务。",
    kind: "ingestion"
  },
  {
    id: "async-queue",
    title: "异步队列任务",
    description: "解析与索引进入后台任务队列。",
    kind: "system"
  },
  {
    id: "parse",
    title: "文件解析",
    description: "提取文本、标题、页码与基础 metadata。",
    kind: "ingestion"
  },
  {
    id: "chunk",
    title: "Chunk 切分",
    description: "按 overlap 与语义边界控制上下文粒度。",
    kind: "ingestion"
  },
  {
    id: "metadata",
    title: "Metadata 构建",
    description: "记录 workspace、权限、文件与 chunk 信息。",
    kind: "ingestion"
  },
  {
    id: "embedding",
    title: "Embedding 向量化",
    description: "通过模型生成可检索向量。",
    kind: "ai"
  },
  {
    id: "milvus-index",
    title: "Milvus / HNSW-IVF",
    description: "写入向量库并建立索引加速检索。",
    kind: "storage"
  }
];

export const ragQuerySteps: RagFlowStep[] = [
  {
    id: "user-question",
    title: "用户问题",
    description: "用户提出需要回答的问题。",
    kind: "query"
  },
  {
    id: "input-guardrails",
    title: "输入护栏",
    description: "检测 Prompt Injection、PII 与敏感输入。",
    kind: "system"
  },
  {
    id: "rewrite",
    title: "Rewrite",
    description: "生成 N 个 rewrite，并与原问题一起检索。",
    kind: "ai"
  },
  {
    id: "hybrid-retrieval",
    title: "Hybrid Retrieval",
    description: "同时执行 BM25 关键词检索与 Vector 检索。",
    kind: "branch"
  },
  {
    id: "permission-filter",
    title: "权限过滤",
    description: "结合 RBAC、workspace 与 metadata filter 过滤结果。",
    kind: "system"
  },
  {
    id: "rrf",
    title: "RRF 融合",
    description: "融合多路召回结果并重新排序。",
    kind: "query"
  },
  {
    id: "top50",
    title: "Top 50 粗筛",
    description: "保留候选上下文集合。",
    kind: "query"
  },
  {
    id: "rerank",
    title: "Rerank Top 5",
    description: "将最相关的上下文提升到前列。",
    kind: "ai"
  },
  {
    id: "context",
    title: "Context Assembly",
    description: "去重、压缩、补全相邻 chunk 并生成引用编号。",
    kind: "query"
  },
  {
    id: "llm",
    title: "DeepSeek / LLM",
    description: "基于上下文生成最终回答。",
    kind: "ai"
  },
  {
    id: "citation",
    title: "Citation",
    description: "输出答案、来源和可检查引用。",
    kind: "query"
  }
];

export const overviewCards: OverviewCard[] = [
  {
    title: "RAG Engineer",
    description: "围绕入库、检索、rerank、上下文组装和引用链路构建工程能力。",
    accent: "green"
  },
  {
    title: "Agent Workflow",
    description: "把计划、工具调用、状态流转和结果拆成可观察流程。",
    accent: "purple"
  },
  {
    title: "Full-stack AI",
    description: "连接前端体验、API、权限、存储和模型服务。",
    accent: "blue"
  },
  {
    title: "VibeCoding",
    description: "用 AI 协作提速交付，同时保持工程边界与验证流程。",
    accent: "pink"
  }
];

export const techStack: TechStackItem[] = [
  { name: "Next.js", category: "frontend" },
  { name: "Java", category: "backend" },
  { name: "FastAPI", category: "backend" },
  { name: "DeepSeek", category: "ai" },
  { name: "Milvus", category: "storage" },
  { name: "Redis", category: "storage" },
  { name: "MySQL", category: "storage" },
  { name: "RAG", category: "ai" },
  { name: "Agent", category: "workflow" },
  { name: "VibeCoding", category: "workflow" },
  { name: "Git", category: "delivery" },
  { name: "Docker", category: "delivery" },
  { name: "Jenkins", category: "delivery" }
];

export const projectCards: ProjectCard[] = [
  {
    name: "Portfolio Chat",
    href: "/",
    status: "Live",
    description: "解释作品集、系统架构和项目阶段的对话入口。",
    tags: ["Chat", "Session", "AI"]
  },
  {
    name: "Knowledge Agent",
    href: "/agents/knowledge",
    status: "RAG Core",
    description: "企业知识库问答、文档管理、检索调试与引用查看。",
    tags: ["RAG", "Retrieval", "Citation"]
  },
  {
    name: "Browser Agent",
    href: "/agents/browser",
    status: "Agent Demo",
    description: "展示规划、搜索和综合输出的浏览器研究流程。",
    tags: ["Planning", "Search", "Synthesis"]
  },
  {
    name: "Office Agent",
    href: "/agents/office",
    status: "Agent Demo",
    description: "展示报告、摘要和结构化输出的办公自动化链路。",
    tags: ["Tools", "Report", "Workflow"]
  }
];

export const roadmapStages: RoadmapStage[] = [
  {
    stage: "01",
    title: "RAG System Builder",
    description: "持续打磨检索质量、权限过滤、上下文工程和评估闭环。"
  },
  {
    stage: "02",
    title: "Agent Application Engineer",
    description: "把计划、工具和状态做成可交付的业务能力。"
  },
  {
    stage: "03",
    title: "AI Application Architect",
    description: "从业务目标出发设计 AI 应用架构、治理边界和交付体系。"
  }
];

export const contactLinks: ContactLink[] = [
  {
    label: "入口",
    value: "Knowledge Agent",
    href: "/agents/knowledge"
  },
  {
    label: "浏览",
    value: "Browser Agent",
    href: "/agents/browser"
  },
  {
    label: "办公",
    value: "Office Agent",
    href: "/agents/office"
  },
  {
    label: "首页",
    value: "Portfolio Chat",
    href: "/"
  }
];
