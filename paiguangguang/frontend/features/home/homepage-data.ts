export type RagFlowStep = {
    id: string;
    title: string;
    description: string;
    kind: "ingestion" | "query" | "branch" | "system" | "ai" | "storage" | "response";
};

export type OverviewCard = {
    title: string;
    description: string;
    accent: "green" | "purple" | "blue" | "pink";
};

export type TechStackItem = {
    name: string;
    category: "frontend" | "backend" | "ai" | "storage" | "workflow" | "delivery" | "response";
};

export type ProjectCard = {
    name: string;
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
    {name: "Java", category: "backend"},
    {name: "FastAPI", category: "backend"},
    {name: "Next.js", category: "frontend"},
    {name: "LangGraph", category: "ai"},
    {name: "RAG", category: "ai"},
    {name: "LangChain", category: "ai"},
    {name: "Milvus", category: "storage"},
    {name: "Redis", category: "storage"},
    {name: "MySQL", category: "storage"},
    {name: "VibeCoding", category: "workflow"},
    {name: "Git", category: "delivery"},
    {name: "Docker", category: "delivery"},
    {name: "Jenkins", category: "delivery"}
];

export const projectCards: ProjectCard[] = [
    {
        name: "Chat Bot",
        status: "Case Study",
        description: "暖心的聊天机器人",
        tags: ["Chat", "Session", "AI"]
    },
    {
        name: "Knowledge Agent",
        status: "Case Study",
        description: "企业知识库问答、文档管理、检索调试与引用查看。",
        tags: ["RAG", "Retrieval", "Citation"]
    },
    {
        name: "飞书 Agent",
        status: "Case Study",
        description: "整合飞书平台，自动写周报，自动审批，自动读取数据",
        tags: ["Planning", "Search", "Synthesis"]
    },
    {
        name: "Office Agent",
        status: "Case Study",
        description: "展示报告、摘要和结构化输出的办公自动化链路。",
        tags: ["Tools", "Report", "Workflow"]
    },
    {
        name: "智慧工业园",
        status: "Scenario",
        description: "企业知识库&&让AI为企业赋能",
        tags: ["IoT", "Energy", "Operations"]
    },
    {
        name: "智慧校园",
        status: "Scenario",
        description: "儿童陪聊机器人&&个性化生成儿童培养计划",
        tags: ["Campus", "Service", "AI"]
    },
    {
        name: "办公自动化Agent",
        status: "Scenario",
        description: "秒审秒批，解放双手",
        tags: ["Marketing", "Content", "Growth"]
    }
];

export const roadmapStages: RoadmapStage[] = [
    {
        stage: "01",
        title: "RAG System Builder",
        description: "让知识从沉睡中醒来，让系统拥有可信的记忆。"
    },
    {
        stage: "02",
        title: "Agentic Application Engineer",
        description: "让 AI 拥有行动的意志"
    },
    {
        stage: "03",
        title: "AI Application Architect",
        description: "构建一座真正能够思考、协作并服务现实世界的智能建筑"
    }
];

