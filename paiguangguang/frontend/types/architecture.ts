export type ArchitectureGraphPosition = {
  x: number;
  y: number;
};

export type ArchitectureGraphNodeData = {
  title: string;
  type: string;
  phase: string;
  description: string;
};

export type ArchitectureGraphNode = {
  id: string;
  type: string;
  position: ArchitectureGraphPosition;
  data: ArchitectureGraphNodeData;
};

export type ArchitectureGraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  animated: boolean;
};

export type ArchitectureGraphData = {
  nodes: ArchitectureGraphNode[];
  edges: ArchitectureGraphEdge[];
};
