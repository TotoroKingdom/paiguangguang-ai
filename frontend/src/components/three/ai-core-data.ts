// Shared scene data for the persistent AI Core experience.
// Everything here is plain data so the HTML layer and the WebGL layer stay in sync.

export type AICoreNodeId = "llm" | "rag" | "tool" | "memory" | "agent";

export type AICoreNode = {
  id: AICoreNodeId;
  label: string;
  title: string;
  description: string;
  items: string[];
  color: string;
  accent: string;
  glow: string;
  radius: number;
  orbit: {
    radius: number;
    speed: number;
    phase: number;
    tiltX: number;
    tiltZ: number;
  };
  ring?: boolean;
  spin: number;
};

export type AICoreScenePose = {
  id: string;
  scale: number;
  distance: number;
  yaw: number;
  pitch: number;
  rotation: [number, number, number];
  orbitSpread: number;
  separation: number;
  orbitSpeed: number;
  labelOpacity: number;
  connections: number;
  halo: number;
  energy: number;
};

export const AI_CORE_FOV = 34;
export const AI_CORE_SCENE_IDS = ["hero", "capabilities", "projects", "building", "exploring", "journey"] as const;

export const aiCoreNodes: AICoreNode[] = [
  {
    id: "llm",
    label: "LLM",
    title: "LLM / 推理与生成",
    description: "负责理解问题、组织上下文并生成回答，是系统中语言推理与表达的核心。",
    items: ["模型网关", "流式生成", "结构化输出"],
    color: "#96a6e2",
    accent: "#4d5d9c",
    glow: "#dfe5ff",
    radius: 0.225,
    orbit: { radius: 1.52, speed: 0.11, phase: 1.55, tiltX: 0.18, tiltZ: -0.12 },
    spin: 0.26
  },
  {
    id: "rag",
    label: "RAG",
    title: "RAG / 检索增强",
    description: "把文档、向量与业务知识组织成可检索的上下文，让回答有来源、可追踪。",
    items: ["混合召回", "Rerank", "引用追踪"],
    color: "#82becb",
    accent: "#386d7a",
    glow: "#e0f7fa",
    radius: 0.195,
    orbit: { radius: 1.76, speed: 0.084, phase: 2.92, tiltX: -0.27, tiltZ: 0.22 },
    spin: 0.34
  },
  {
    id: "tool",
    label: "TOOL",
    title: "TOOL / 工具调用",
    description: "把模型能力连接到真实业务接口，在受控、可审计的边界内执行动作。",
    items: ["工具协议", "业务 API", "受控执行"],
    color: "#93b5df",
    accent: "#44658d",
    glow: "#e3efff",
    radius: 0.185,
    orbit: { radius: 1.63, speed: 0.098, phase: 4.24, tiltX: 0.31, tiltZ: 0.1 },
    spin: 0.3
  },
  {
    id: "memory",
    label: "MEMORY",
    title: "MEMORY / 记忆与上下文",
    description: "保存短期会话、长期知识与检查点，让系统在多轮任务中保持连续理解。",
    items: ["短期上下文", "长期记忆", "检查点"],
    color: "#b8a7d8",
    accent: "#6a568c",
    glow: "#f0e9ff",
    radius: 0.21,
    orbit: { radius: 1.89, speed: 0.072, phase: 5.48, tiltX: -0.14, tiltZ: -0.26 },
    ring: true,
    spin: 0.22
  },
  {
    id: "agent",
    label: "AGENT",
    title: "AGENT / 编排与执行",
    description: "编排模型、知识、工具与记忆，把一次回答扩展成可完成的真实任务。",
    items: ["工作流编排", "Human-in-the-loop", "任务审计"],
    color: "#a99ee0",
    accent: "#564b91",
    glow: "#e9e4ff",
    radius: 0.24,
    orbit: { radius: 1.99, speed: 0.062, phase: 0.62, tiltX: 0.1, tiltZ: 0.3 },
    spin: 0.19
  }
];

// Six authored poses. Scroll progress interpolates continuously between them.
// Positions are not hard-coded in pixels: the controller derives the on-screen
// anchor from DOM landmarks, then converts it into a world position for the camera.
export const aiCoreScenes: AICoreScenePose[] = [
  {
    id: "hero",
    scale: 0.8,
    distance: 9.2,
    yaw: 0.02,
    pitch: 0.04,
    rotation: [0.05, -0.1, 0],
    orbitSpread: 1,
    separation: 0,
    orbitSpeed: 1,
    labelOpacity: 1,
    connections: 0,
    halo: 1,
    energy: 0.45
  },
  {
    id: "capabilities",
    scale: 0.82,
    distance: 8.7,
    yaw: 0.2,
    pitch: 0.13,
    rotation: [0.14, 0.4, -0.05],
    orbitSpread: 1.08,
    separation: 0.06,
    orbitSpeed: 0.9,
    labelOpacity: 0.85,
    connections: 0.25,
    halo: 0.62,
    energy: 0.6
  },
  {
    id: "projects",
    scale: 0.74,
    distance: 10.2,
    yaw: -0.4,
    pitch: -0.06,
    rotation: [-0.06, -0.46, 0.08],
    orbitSpread: 1,
    separation: 0,
    orbitSpeed: 0.72,
    labelOpacity: 0.55,
    connections: 0,
    halo: 0.4,
    energy: 0.4
  },
  {
    id: "building",
    scale: 0.86,
    distance: 9.3,
    yaw: 0.3,
    pitch: 0.17,
    rotation: [0.18, 0.1, 0],
    orbitSpread: 1.16,
    separation: 0.28,
    orbitSpeed: 0.55,
    labelOpacity: 1,
    connections: 0.85,
    halo: 0.8,
    energy: 0.8
  },
  {
    id: "exploring",
    scale: 0.78,
    distance: 8.9,
    yaw: 0.62,
    pitch: -0.16,
    rotation: [0.02, 0.66, -0.1],
    orbitSpread: 1.08,
    separation: 0.04,
    orbitSpeed: 0.8,
    labelOpacity: 0.75,
    connections: 0.1,
    halo: 0.55,
    energy: 0.55
  },
  {
    id: "journey",
    scale: 0.8,
    distance: 9.6,
    yaw: 0.04,
    pitch: 0.03,
    rotation: [0.06, 0, 0],
    orbitSpread: 1,
    separation: 0,
    orbitSpeed: 0.78,
    labelOpacity: 1,
    connections: 0.2,
    halo: 0.9,
    energy: 0.5
  }
];

export const aiCoreNodeIndex = new Map(aiCoreNodes.map((node, index) => [node.id, index]));
