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
  /** Off-centre camera target, measured in world units. */
  lookX: number;
  lookY: number;
  /** Camera roll in radians; a few degrees read as a composed shot. */
  roll: number;
};

/**
 * A transition is authored once and sampled with sin(pi * t), so forward and
 * reverse scrolling trace exactly the same arc and both ends settle at zero.
 */
export type AICoreTransitionPose = {
  arcX: number;
  arcY: number;
  dolly: number;
  spin: number;
  roll: number;
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
    // A steeper plane keeps the node below the core instead of across its face.
    orbit: { radius: 1.38, speed: 0.058, phase: 1.55, tiltX: 0.55, tiltZ: -0.12 },
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
    orbit: { radius: 1.58, speed: 0.054, phase: 2.92, tiltX: -0.45, tiltZ: 0.28 },
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
    radius: 0.18,
    orbit: { radius: 1.5, speed: 0.057, phase: 4.24, tiltX: 0.6, tiltZ: 0.12 },
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
    orbit: { radius: 1.66, speed: 0.052, phase: 5.48, tiltX: -0.38, tiltZ: -0.3 },
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
    orbit: { radius: 1.8, speed: 0.049, phase: 0.62, tiltX: -0.42, tiltZ: 0.34 },
    spin: 0.19
  }
];

// Six authored poses. Scroll progress interpolates continuously between them.
// Positions are not hard-coded in pixels: the controller derives the on-screen
// anchor from DOM landmarks, then converts it into a world position for the camera.
export const aiCoreScenes: AICoreScenePose[] = [
  {
    id: "hero",
    scale: 0.82,
    distance: 9.4,
    yaw: 0.02,
    pitch: 0.05,
    rotation: [0.06, -0.1, 0],
    orbitSpread: 1,
    separation: 0,
    orbitSpeed: 0.95,
    labelOpacity: 1,
    connections: 0,
    halo: 0.95,
    energy: 0.45,
    lookX: 0,
    lookY: 0.02,
    roll: 0
  },
  {
    id: "capabilities",
    scale: 0.8,
    distance: 10.2,
    yaw: 0.24,
    pitch: 0.14,
    rotation: [0.12, 0.52, -0.04],
    orbitSpread: 1.03,
    separation: 0.04,
    orbitSpeed: 0.85,
    labelOpacity: 0.92,
    connections: 0.3,
    halo: 0.6,
    energy: 0.6,
    lookX: 0.05,
    lookY: -0.01,
    roll: -0.018
  },
  {
    id: "projects",
    scale: 0.78,
    distance: 11.2,
    yaw: -0.46,
    pitch: -0.02,
    rotation: [-0.04, -0.58, 0.06],
    orbitSpread: 0.94,
    separation: 0,
    orbitSpeed: 0.7,
    labelOpacity: 0.82,
    connections: 0,
    halo: 0.38,
    energy: 0.38,
    lookX: -0.04,
    lookY: 0,
    roll: 0.02
  },
  {
    id: "building",
    scale: 0.82,
    distance: 10.6,
    yaw: 0.4,
    pitch: 0.18,
    rotation: [0.15, 0.2, 0.02],
    orbitSpread: 1.04,
    separation: 0.14,
    orbitSpeed: 0.58,
    labelOpacity: 1,
    connections: 0.85,
    halo: 0.7,
    energy: 0.78,
    lookX: 0.06,
    lookY: 0.02,
    roll: -0.012
  },
  {
    id: "exploring",
    scale: 0.8,
    distance: 11,
    yaw: -0.3,
    pitch: 0.06,
    rotation: [0.03, -0.48, -0.06],
    orbitSpread: 0.98,
    separation: 0.02,
    orbitSpeed: 0.76,
    labelOpacity: 0.9,
    connections: 0.12,
    halo: 0.5,
    energy: 0.52,
    lookX: -0.03,
    lookY: 0.01,
    roll: 0.016
  },
  {
    id: "journey",
    scale: 0.72,
    distance: 11.8,
    yaw: 0.04,
    pitch: 0.05,
    rotation: [0.05, 0.04, 0],
    orbitSpread: 0.96,
    separation: 0,
    orbitSpeed: 0.55,
    labelOpacity: 0.95,
    connections: 0.2,
    halo: 0.75,
    energy: 0.45,
    lookX: 0,
    lookY: 0.015,
    roll: 0
  }
];

/**
 * Five authored in-between beats. `dolly` is a multiplier on the camera
 * distance at mid-transition, `spin` adds yaw and `roll` tilts the shot.
 * Every value returns to zero at both ends, which keeps reverse scroll exact.
 */
export const aiCoreTransitions: AICoreTransitionPose[] = [
  { arcX: 0.018, arcY: -0.012, dolly: -0.1, spin: 0.3, roll: 0.012 },
  { arcX: -0.02, arcY: 0.018, dolly: 0.24, spin: -0.5, roll: -0.02 },
  { arcX: 0.02, arcY: 0.014, dolly: 0.2, spin: 0.28, roll: 0.014 },
  { arcX: -0.018, arcY: 0.31, dolly: 0.78, spin: -0.5, roll: -0.026 },
  { arcX: 0.012, arcY: -0.008, dolly: 0.1, spin: 0.22, roll: 0.01 }
];

export const aiCoreNodeIndex = new Map(aiCoreNodes.map((node, index) => [node.id, index]));
