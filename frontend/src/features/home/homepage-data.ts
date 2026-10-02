export type RagFlowStep = {
    id: string;
    title: string;
    description: string;
    kind: "ingestion" | "query" | "branch" | "system" | "ai" | "storage" | "response";
};

export type Identity = {
    title: string;
    titleZh: string;
    secondary: string;
    statement: string;
    description: string;
};

export type Capability = {
    name: string;
    description: string;
    items: string[];
};

export type CompletedProject = {
    id: string;
    name: string;
    category: string;
    description: string;
    items: string[];
    status: "BUILT";
    href?: string;
    linkText?: string;
    image?: {
        src: string;
        alt: string;
        width: number;
        height: number;
    };
};

export type ActiveProject = {
    id: string;
    name: string;
    category: string;
    description: string;
    items: string[];
    status: "BUILDING";
    href?: string;
    linkText?: string;
};

export type ExplorationProject = {
    id: string;
    name: string;
    source: string;
    description: string;
    items: string[];
    status: "EXPLORING";
    href: string;
};

export type CareerStage = {
    id: string;
    title: string;
    label: string;
    description: string;
    state: "past" | "current" | "future";
};

type LegacyTechStackCategory = "frontend" | "backend" | "ai" | "storage" | "workflow" | "delivery" | "response";

export type TechStackItem = {
    name: string;
    category: LegacyTechStackCategory;
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

export const homepageIdentity: Identity = {
    title: "AI Agent Engineer",
    titleZh: "AI 智能体工程师",
    secondary: "全栈工程师",
    statement: "我不太相信AI会沿着一条确定的道路走向未来。",
    description: "它更像水，遇到不同的环境，就会形成不同的形状。 与其预测未来最终会成为什么样，我更愿意亲自参与其中，塑造它的样子：做一些东西，观察它如何变化，也观察人在这种变化里该站在哪里。"
};

export const capabilities: Capability[] = [
    {
        name: "AI & Agent / AI 与智能体",
        description: "探索模型、知识检索与智能体工作流的组合。",
        items: ["LangGraph", "LangChain", "RAG / 检索增强生成", "Tool Calling / 工具调用", "Human-in-the-loop / 人工介入", "LLM API / 大模型接口 · DeepSeek"]
    },
    {
        name: "Backend / 后端",
        description: "用服务、接口与数据模型组织应用逻辑。",
        items: ["Java", "Python", "FastAPI", "SQLAlchemy", "Pydantic", "REST API / REST 接口"]
    },
    {
        name: "Frontend / 前端",
        description: "连接 AI 系统与可理解、可交互的界面。",
        items: ["Next.js", "TypeScript", "Tailwind CSS", "Framer Motion", "React", "Three.js"]
    },
    {
        name: "Data & Delivery / 数据与部署",
        description: "围绕存储、检索、部署与持续集成积累实践。",
        items: ["PostgreSQL", "Redis", "ChromaDB / Vector DB / 向量数据库", "Docker", "Nginx", "Jenkins / GitHub Actions"]
    }
];

export const homepageSections = {
    about: { eyebrow: "01 / 关于" },
    capabilities: { eyebrow: "02 / 能力", title: "我的技术栈", description: "围绕 AI 与智能体、后端、前端、数据与部署，记录我使用和学习的技术。" },
    projects: { eyebrow: "03 / 作品", title: "我的作品", description: "已完成的项目实践：知识检索、持续对话与办公任务执行。" },
    building: { eyebrow: "04 / 构建", title: "我正在构建的作品", description: "持续构建知识平台、企业数字员工与智能体运行框架，记录当前的工程进展。" },
    exploring: { eyebrow: "05 / 探索", title: "我正在探索的项目", description: "我正在研究的外部开源项目与学习资料。它们由各自的组织或作者维护。" },
    journey: { eyebrow: "06 / 规划", title: "我的职业生涯规划", description: "沿着后端、AI 应用、智能体工程到智能体架构的路线，持续积累系统设计与工程实践。" }
};

export const homepageContact = {
    title: "保持联系",
    description: "我会持续在这里记录正在构建和研究的 AI 系统。",
    footerCopy: "持续构建，持续研究。"
};

export const completedProjects: CompletedProject[] = [
    {
        id: "rag-knowledge-system",
        name: "RAG 知识检索系统",
        category: "KNOWLEDGE / 知识",
        description: "将文档入库、混合召回、重排和引用组织成可追踪的知识检索链路。",
        items: ["文档入库与切分", "混合召回与 RRF 融合", "重排与上下文组装", "引用与评估"],
        status: "BUILT",
        href: "/rag",
        linkText: "查看系统说明",
        image: {
            src: "/work/rag-control-plane.png",
            alt: "RAG 知识检索系统链路说明截图",
            width: 1440,
            height: 900
        }
    },
    {
        id: "ai-chatbot",
        name: "AI 聊天机器人",
        category: "CONVERSATION / 对话",
        description: "围绕多会话、持久历史和记忆组织可持续的流式对话体验。",
        items: ["多会话与持久历史", "流式响应与模型网关", "短期、长期与语义记忆", "检查点与数据持久化"],
        status: "BUILT"
    },
    {
        id: "office-automation-agent",
        name: "办公自动化智能体",
        category: "ACTION / 行动",
        description: "将工具调用、审批和业务 API 集成到可追踪的企业任务流程中。",
        items: ["智能体工作流与工具调用", "Human-in-the-loop 人工介入", "业务 API 集成与审批", "结构化输出与审计追踪"],
        status: "BUILT"
    }
];

export const activeProjects: ActiveProject[] = [
    {
        id: "knowledge-platform",
        name: "知识平台",
        category: "KNOWLEDGE / 知识治理",
        description: "正在构建知识对象、权限边界和治理规则，为智能体提供可靠的知识基础。",
        items: ["知识对象", "ACL 访问权限治理", "知识规则", "智能体治理"],
        status: "BUILDING"
    },
    {
        id: "enterprise-digital-employee",
        name: "企业数字员工",
        category: "ACTION / 企业协作",
        description: "正在开发能在企业工作流中执行受控、可审计任务的数字员工。",
        items: ["智能体运行时", "企业工具接入", "审批与人工介入", "任务执行与审计"],
        status: "BUILDING"
    },
    {
        id: "chatgpt-harness",
        name: "ChatGPT Harness（运行框架）",
        category: "RUNTIME / 运行时",
        description: "正在围绕模型、工具、上下文和执行环境构建可控的运行框架。",
        items: ["模型运行框架", "工具协议", "上下文工程", "记忆与执行环境"],
        status: "BUILDING"
    }
];

export const explorationProjects: ExplorationProject[] = [
    {
        id: "codex",
        name: "Codex",
        source: "OpenAI",
        description: "研究编码智能体的运行机制，以及工具执行和开发者体验如何协同。",
        items: ["智能体运行框架", "工具执行", "上下文工程", "开发者体验"],
        status: "EXPLORING",
        href: "https://github.com/openai/codex"
    },
    {
        id: "deepseek-harness",
        name: "DeepSeek Harness",
        source: "DeepSeek",
        description: "研究模型接入、工具执行和上下文管理在智能体运行框架中的组合方式。",
        items: ["模型接入", "工具执行", "上下文管理", "智能体集成"],
        status: "EXPLORING",
        href: "https://github.com/deepseek-ai/deepseek-harness"
    },
    {
        id: "pi",
        name: "Pi",
        source: "earendil-works",
        description: "研究轻量智能体运行时如何组织工具调用、上下文和记忆。",
        items: ["智能体运行时", "工具调用", "上下文与记忆", "开发者集成"],
        status: "EXPLORING",
        href: "https://github.com/earendil-works/pi"
    },
    {
        id: "hermes",
        name: "Hermes",
        source: "Nous Research",
        description: "研究智能体的任务执行、工具使用和可持续记忆机制。",
        items: ["智能体运行机制", "工具使用", "记忆系统", "任务执行"],
        status: "EXPLORING",
        href: "https://github.com/NousResearch/hermes-agent"
    },
    {
        id: "openclaw",
        name: "OpenClaw",
        source: "OpenClaw",
        description: "研究智能体运行时如何连接工具、上下文、记忆与外部集成。",
        items: ["智能体运行时", "工具与集成", "上下文管理", "记忆机制"],
        status: "EXPLORING",
        href: "https://github.com/openclaw/openclaw"
    },
    {
        id: "pytorch-deep-learning",
        name: "PyTorch 学习实践",
        source: "Daniel Bourke",
        description: "通过 Daniel Bourke 的课程与实践项目学习 PyTorch 深度学习流程。",
        items: ["PyTorch 深度学习", "模型训练实践", "课程实验", "Daniel Bourke 课程"],
        status: "EXPLORING",
        href: "https://github.com/mrdbourke/pytorch-deep-learning"
    }
];

export const careerStages: CareerStage[] = [
    {
        id: "backend-engineer",
        title: "后端工程师",
        label: "BACKEND / 后端基础",
        description: "建立可靠的服务、数据和 API 工程基础。",
        state: "past"
    },
    {
        id: "ai-application-engineer",
        title: "AI 应用工程师",
        label: "AI APPLICATION / AI 应用",
        description: "将 RAG、LLM 和 AI 交互组织成可使用的产品。",
        state: "past"
    },
    {
        id: "ai-agent-engineer",
        title: "AI 智能体工程师",
        label: "AGENT ENGINEERING / 智能体工程",
        description: "围绕工作流、工具、记忆和人机协同构建可执行的 Agent 系统。",
        state: "current"
    },
    {
        id: "ai-agent-architect",
        title: "AI 智能体架构师",
        label: "AGENT ARCHITECTURE / 智能体架构",
        description: "持续探索 Agent 运行时、知识基础设施、分布式系统、评估与治理。",
        state: "future"
    }
];

export const homepageNavigation = [
    { label: "关于", href: "/#hero" },
    { label: "能力", href: "/#capabilities" },
    { label: "作品", href: "/#projects" },
    { label: "构建", href: "/#building" },
    { label: "探索", href: "/#exploring" },
    { label: "规划", href: "/#journey" }
];

export const githubProfileHref = "https://github.com/TotoroKingdom";

export const homepageContactLinks: ContactLink[] = [
    {
        label: "邮箱",
        value: "totorokingdom@foxmail.com",
        href: "mailto:totorokingdom@foxmail.com"
    },
    {
        label: "GitHub",
        value: "TotoroKingdom",
        href: githubProfileHref
    }
];

// Kept for the existing standalone component; homepage technology groups are defined above.
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
