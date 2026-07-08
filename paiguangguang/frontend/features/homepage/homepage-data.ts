export type HomepageLink = {
  title: string;
  href: string;
  description: string;
  status: string;
};

export type WorkflowStep = {
  label: string;
  title: string;
  description: string;
};

export type HomepageProject = {
  name: string;
  description: string;
  tags: string[];
  href: string;
  proof: string;
  imageSrc?: string;
};

export type HomepageTech = {
  name: string;
  category: "frontend" | "backend" | "ai" | "storage" | "delivery";
  imageSrc?: string;
};

export const heroProofPoints = [
  "Next.js product surface",
  "FastAPI AI backend",
  "RAG and citations",
  "Visible agent workflows"
];

export const moduleLinks: HomepageLink[] = [
  {
    title: "Knowledge Agent",
    href: "/agents/knowledge",
    description: "Authenticated RAG workspace for documents, retrieval, citations, and debug traces.",
    status: "RAG track"
  },
  {
    title: "Browser Agent",
    href: "/agents/browser",
    description: "Research workflow demo with visible planning, search steps, and synthesis.",
    status: "Agent demo"
  },
  {
    title: "Office Agent",
    href: "/agents/office",
    description: "Office automation demo with tool execution steps and structured output.",
    status: "Agent demo"
  },
  {
    title: "Architecture",
    href: "/architecture",
    description: "Interactive system graph for frontend, backend, AI, storage, and workflow layers.",
    status: "System map"
  },
  {
    title: "Admin",
    href: "/admin",
    description: "Management surface for users, roles, workspaces, documents, and ingestion state.",
    status: "Ops surface"
  }
];

export const workflowSteps: WorkflowStep[] = [
  {
    label: "01",
    title: "User intent",
    description: "The interface captures a question, workflow request, or document task."
  },
  {
    label: "02",
    title: "Retrieval or tools",
    description: "RAG, mock search, office tools, or architecture data provide grounded context."
  },
  {
    label: "03",
    title: "Model reasoning",
    description: "The backend keeps prompts, providers, permissions, and model calls isolated."
  },
  {
    label: "04",
    title: "Visible result",
    description: "The UI exposes answers, sources, steps, and final structured outputs."
  }
];

export const portfolioProjects: HomepageProject[] = [
  {
    name: "Portfolio Chat",
    description: "A live assistant surface for explaining the portfolio, architecture, and project phases.",
    tags: ["Next.js", "FastAPI", "DeepSeek"],
    href: "/",
    proof: "Shows frontend state, API round trip, session memory, and error handling.",
    imageSrc: "/homepage/project/aigc.png"
  },
  {
    name: "Knowledge Agent",
    description: "A RAG product track with document lifecycle, permissions, retrieval quality, and citations.",
    tags: ["RAG", "Chroma", "RBAC"],
    href: "/agents/knowledge",
    proof: "Demonstrates enterprise-style retrieval architecture and debug visibility.",
    imageSrc: "/homepage/project/particles.png"
  },
  {
    name: "Agent Workflows",
    description: "Browser and Office demos that reveal planning, tool calls, and final outputs.",
    tags: ["Agents", "Tools", "SSE"],
    href: "/agents/browser",
    proof: "Shows workflow decomposition instead of hiding work behind a single answer.",
    imageSrc: "/homepage/project/su7.png"
  }
];

export const techStack: HomepageTech[] = [
  { name: "Next.js", category: "frontend" },
  { name: "TypeScript", category: "frontend", imageSrc: "/homepage/tech/typescript.png" },
  { name: "Tailwind CSS", category: "frontend" },
  { name: "FastAPI", category: "backend" },
  { name: "Pydantic", category: "backend" },
  { name: "DeepSeek", category: "ai" },
  { name: "RAG", category: "ai" },
  { name: "Chroma", category: "storage" },
  { name: "Redis", category: "storage" },
  { name: "Docker", category: "delivery", imageSrc: "/homepage/tech/docker.png" }
];
