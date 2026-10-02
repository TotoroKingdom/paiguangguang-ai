// Shared geometry keeps the HTML labels and the scene nodes on the same orbit.
export const AI_CORE_CAMERA = { distance: 5.7, fov: 40 };
export const AI_CORE_ORBIT_RADIUS = 1.62;
export const AI_CORE_VIEW_HEIGHT = 2 * AI_CORE_CAMERA.distance * Math.tan(AI_CORE_CAMERA.fov * Math.PI / 360);

export const aiCoreNodes = [
  { id: "llm", label: "LLM", angle: 90, color: "#9ba8dc", labelColor: "#505f96", radius: 0.145 },
  { id: "rag", label: "RAG", angle: 162, color: "#8cbac8", labelColor: "#426c79", radius: 0.135 },
  { id: "tool", label: "TOOL", angle: 18, color: "#92aed6", labelColor: "#4b6590", radius: 0.13 },
  { id: "memory", label: "MEMORY", angle: 234, color: "#b3a0ce", labelColor: "#75608e", radius: 0.14 },
  { id: "agent", label: "AGENT", angle: 306, color: "#a39cd5", labelColor: "#655c95", radius: 0.15 },
].map((node) => ({
  ...node,
  position: [
    Math.cos(node.angle * Math.PI / 180) * AI_CORE_ORBIT_RADIUS,
    Math.sin(node.angle * Math.PI / 180) * AI_CORE_ORBIT_RADIUS,
    0,
  ] as [number, number, number],
}));
