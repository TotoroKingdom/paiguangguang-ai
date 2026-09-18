export type RagFlowStep = {
    id: string;
    title: string;
    description: string;
    kind: "ingestion" | "query" | "branch" | "system" | "ai" | "storage" | "response";
};

export type HomepageProject = {
    name: string;
    focus: string;
    context: string;
    problem: string;
    architecture: string[];
    contribution: string;
    outcome: string;
    accent: "purple" | "cyan" | "green";
};

export type Capability = {
    name: string;
    description: string;
    items: string[];
};

type LegacyTechStackCategory = "frontend" | "backend" | "ai" | "storage" | "workflow" | "delivery" | "response";

export type TechStackItem = {
    name: string;
    category: LegacyTechStackCategory;
};

export type ApproachStage = {
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
        title: "业务文档源",
        description: "企业知识库、制度文档、FAQ、项目资料等作为 RAG 的原始数据来源。",
        kind: "ingestion"
    },
    {
        id: "upload",
        title: "文件上传",
        description: "接收 PDF、Markdown、Word、网页文本等文档，并创建入库任务。",
        kind: "ingestion"
    },
    {
        id: "async-queue",
        title: "异步队列任务",
        description: "将解析、切块、向量化和索引写入放到后台任务中执行。",
        kind: "system"
    },
    {
        id: "parse",
        title: "文件解析",
        description: "提取正文、标题、页码、段落结构和基础 metadata。",
        kind: "ingestion"
    },
    {
        id: "cleaning",
        title: "数据清洗",
        description: "去除噪声、修复格式、合并异常换行，并保留可追踪信息。",
        kind: "ingestion"
    },
    {
        id: "chunk",
        title: "Chunk 切分",
        description: "按照 chunk size、overlap 和语义边界切分文档内容。",
        kind: "ingestion"
    },
    {
        id: "metadata",
        title: "Metadata 构建",
        description: "记录 document_id、chunk_id、workspace、权限、页码和版本信息。",
        kind: "ingestion"
    },
    {
        id: "embedding",
        title: "Embedding 向量化",
        description: "调用 embedding 模型，将 chunk 文本转换成可检索向量。",
        kind: "ai"
    },
    {
        id: "milvus-index",
        title: "Milvus 向量库",
        description: "写入 chunk embedding 和 metadata，并建立 HNSW / IVF 等索引。",
        kind: "storage"
    }
];

export const ragQuerySteps: RagFlowStep[] = [
    {
        id: "user-question",
        title: "用户问题",
        description: "用户提出问题，系统保留原始 query 用于追踪、评估和缓存。",
        kind: "query"
    },
    {
        id: "input-guardrails",
        title: "输入护栏",
        description: "检测 Prompt Injection、越权意图、PII 和明显无效输入。",
        kind: "system"
    },
    {
        id: "rewrite",
        title: "Query Rewrite",
        description: "生成多个改写问题，补全上下文，并保留原始问题一起参与召回。",
        kind: "query"
    },
    {
        id: "hybrid-retrieval",
        title: "Hybrid Retrieval",
        description: "分叉为 BM25 关键词召回和 Vector 向量召回两条并行路线。",
        kind: "branch"
    },
    {
        id: "permission-filter",
        title: "权限过滤",
        description: "结合 RBAC、workspace、document metadata 和 chunk metadata 过滤候选结果。",
        kind: "system"
    },
    {
        id: "rrf",
        title: "RRF 融合",
        description: "融合 BM25 和 Vector 两路召回结果，降低单一路召回偏差。",
        kind: "system"
    },
    {
        id: "top50",
        title: "Top 50 粗筛",
        description: "保留候选上下文集合，为后续 rerank 降低计算成本。",
        kind: "system"
    },
    {
        id: "rerank",
        title: "Rerank Top 5",
        description: "使用 rerank 模型对候选 chunk 精排，选出最相关上下文。",
        kind: "ai"
    },
    {
        id: "context",
        title: "Context Assembly",
        description: "去重、压缩、补全相邻 chunk，并生成可引用的上下文编号。",
        kind: "system"
    },
    {
        id: "llm",
        title: "DeepSeek / LLM",
        description: "基于检索上下文生成回答，避免脱离知识库自由发挥。",
        kind: "ai"
    },
    {
        id: "citation",
        title: "Citation",
        description: "输出答案、来源文档、chunk 信息和可检查引用。",
        kind: "system"
    }
];

export const projectCards: HomepageProject[] = [
    {
        name: "Knowledge System",
        focus: "Retrieval infrastructure",
        context: "把企业文档、FAQ 与制度资料整理成可以被 Agent 使用的知识基础设施。",
        problem: "知识分散、权限边界不清，回答无法解释来源。",
        architecture: ["Ingestion", "Hybrid retrieval", "Rerank", "Citation"],
        contribution: "设计入库、权限过滤、召回精排与引用输出的完整链路。",
        outcome: "让每次回答都能回到具体上下文，支持复核与评估。",
        accent: "purple"
    },
    {
        name: "Agent Workflow",
        focus: "Executable orchestration",
        context: "让模型从一次性生成，变成可以规划、调用工具并完成任务的工作流。",
        problem: "长链路状态容易丢失，工具调用缺少边界，失败难以恢复。",
        architecture: ["Planning", "Tool calling", "Memory", "Verification"],
        contribution: "拆分状态、工具、记忆与验证节点，建立可观察的执行路径。",
        outcome: "把 Agent 行为变成可调试、可恢复、可交付的系统流程。",
        accent: "cyan"
    },
    {
        name: "AI Office Automation",
        focus: "AI product delivery",
        context: "连接企业协作工具与业务 API，减少重复操作，让结果直接进入工作流。",
        problem: "跨系统操作依赖人工，审批与结构化输出缺少审计线索。",
        architecture: ["Intent", "Tool adapters", "Approval", "Observability"],
        contribution: "实现工具适配、权限控制、结构化产出与可追踪交付界面。",
        outcome: "将模型能力收束成稳定的自动化动作，而不是孤立的 Demo。",
        accent: "green"
    }
];

export const capabilities: Capability[] = [
    {
        name: "Knowledge Systems",
        description: "让知识可检索、可控、可验证，并且始终保留来源。",
        items: ["RAG", "Retrieval", "Rerank", "Evaluation", "Permission"]
    },
    {
        name: "Agent Engineering",
        description: "把模型决策拆成可观察的计划、工具与状态流转。",
        items: ["Planning", "Tool Calling", "Memory", "Workflow"]
    },
    {
        name: "AI Product Delivery",
        description: "从界面到部署，把 AI 能力交付成可以被使用的产品。",
        items: ["Frontend", "Backend", "Deployment", "Observability"]
    }
];

// Kept for the existing standalone component; the homepage now presents capabilities as systems.
export const techStack: TechStackItem[] = [
    { name: "Java", category: "backend" },
    { name: "FastAPI", category: "backend" },
    { name: "Next.js", category: "frontend" },
    { name: "LangGraph", category: "ai" },
    { name: "RAG", category: "ai" },
    { name: "LangChain", category: "ai" },
    { name: "Milvus", category: "storage" },
    { name: "Redis", category: "storage" },
    { name: "MySQL", category: "storage" },
    { name: "VibeCoding", category: "workflow" },
    { name: "Git", category: "delivery" },
    { name: "Docker", category: "delivery" },
    { name: "Jenkins", category: "delivery" }
];

export const approachStages: ApproachStage[] = [
    {
        stage: "Observe",
        title: "可观察",
        description: "先看清问题、数据流、状态与失败边界，再决定 Agent 应该如何行动。"
    },
    {
        stage: "Evaluate",
        title: "可验证",
        description: "用检索质量、工具结果、引用链路与真实任务反馈检查系统是否可靠。"
    },
    {
        stage: "Ship",
        title: "可交付",
        description: "把经过验证的能力接入产品、部署与观测，让它在真实工作中持续产生价值。"
    }
];

