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
    items: (string | { name: string; children: string[] })[];
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
    statusLabel?: string;
    cardLink?: boolean;
    previewScene?: "robot";
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
        name: "全栈 / Full-Stack",
        description: "以服务、界面和基础设施支撑完整应用。",
        items: ["Python", "FastAPI", "Java", "Spring Boot", "TypeScript", "MySQL / PostgreSQL", "Docker", "Redis"]
    },
    {
        name: "智能体架构 / Agent Architecture",
        description: "组织智能体工作模式、工具与人机协作。",
        items: [{ name: "编排 LangGraph", children: ["Workflow", "Plan & Execute", "ReAct（推理与行动）", "Reflection", "Supervisor"] }, "工具调用 / Tool Calling", "上下文工程 / Context Engineering", "记忆系统 / Memory", "人机协作 / HITL"]
    },
    {
        name: "RAG 与知识治理",
        description: "围绕检索和知识治理构建可靠的知识基础。",
        items: ["Embedding", "BM25", "RRF", "Rerank", "Milvus", "知识治理"]
    },
    {
        name: "评估与可靠性 / Evaluation & Reliability",
        description: "通过评估、追踪和安全边界提升系统可靠性。",
        items: ["Agent Evals（智能体评估）", "Tracing（追踪）", "Langfuse", "故障恢复", "成本与延迟优化", "审计与安全边界"]
    }
];

export const homepageSections = {
    about: { eyebrow: "01 / 关于" },
    capabilities: { eyebrow: "02 / 能力", title: "我的技术栈", description: "围绕全栈、智能体架构、知识治理与可靠性，记录我的工程实践。" },
    projects: { eyebrow: "03 / 作品", title: "我的作品", description: "从可交互的三维实验，到智能助手与可追踪的知识检索系统。" },
    building: { eyebrow: "04 / 构建", title: "我正在构建的作品", description: "持续构建知识中心、企业数字员工与智能体运行框架，记录当前的工程进展。" },
    exploring: { eyebrow: "05 / 探索", title: "我正在探索的项目", description: "我正在研究的外部开源项目与学习资料。它们由各自的组织或作者维护。" },
    journey: { eyebrow: "06 / 规划", title: "我的职业生涯规划", description: "从后端工程到智能体工程、架构与前沿部署，持续积累系统设计与工程实践。" }
};

export const homepageContact = {
    title: "保持联系",
    description: "我会持续在这里记录正在构建和研究的 AI 系统。",
    footerCopy: "持续构建，持续研究。"
};

export const completedProjects: CompletedProject[] = [
    {
        id: "threejs-lab",
        name: "3D 交互实验室",
        category: "CREATIVE LAB / THREE.JS",
        description: "用代码构建、驱动和探索三维世界。从智能机器人到机械结构，把程序化建模与实时交互变成看得见的作品。",
        items: ["程序化建模", "交互动画", "WebGL 实时渲染"],
        status: "BUILT",
        statusLabel: "持续更新",
        href: "/lab/3d",
        linkText: "探索实验室",
        cardLink: true,
        previewScene: "robot"
    },
    {
        id: "ai-chatbot",
        name: "智能助手",
        category: "CONVERSATION / 对话",
        description: "通过交互原型体验多会话、能力选择与模拟对话。",
        items: ["多会话", "工具与技能", "连接器与智能体", "文件管理"],
        status: "BUILT",
        href: "/assistant",
        linkText: "体验原型",
        cardLink: true
    },
    {
        id: "rag-knowledge-system",
        name: "RAG 知识检索系统",
        category: "KNOWLEDGE / 知识",
        description: "将文档入库、混合检索、重排和引用组织成可追踪的知识检索链路。",
        items: ["混合检索", "RRF 融合", "Rerank 重排", "引用与评估"],
        status: "BUILT",
        href: "/rag",
        linkText: "查看系统",
        cardLink: true
    }
];

export const activeProjects: ActiveProject[] = [
    {
        id: "knowledge-platform",
        name: "知识中心",
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
        name: "DSH（DeepSeek Harness）",
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
        id: "ai-agent-engineer",
        title: "Agent 工程师（智能体工程师）",
        label: "AGENT ENGINEERING / 智能体工程",
        description: "围绕工作流、工具、记忆和人机协同构建可执行的 Agent 系统。",
        state: "current"
    },
    {
        id: "ai-agent-architect",
        title: "Agent 架构师（智能体架构师）",
        label: "AGENT ARCHITECTURE / 智能体架构",
        description: "持续探索 Agent 运行时、知识基础设施、分布式系统、评估与治理。",
        state: "future"
    },
    {
        id: "fde",
        title: "FDE（前沿部署工程师）",
        label: "FORWARD DEPLOYED ENGINEER / 前沿部署",
        description: "深入真实业务场景，部署并迭代智能体系统。",
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
