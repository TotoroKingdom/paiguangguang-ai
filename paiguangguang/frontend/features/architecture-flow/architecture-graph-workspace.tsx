"use client";

import "@xyflow/react/dist/style.css";

import { useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeProps,
  Position,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";

import { ApiError } from "@/lib/api";
import { getSystemArchitectureGraph } from "@/lib/architecture";
import type { ArchitectureGraphData, ArchitectureGraphEdge, ArchitectureGraphNode, ArchitectureGraphNodeData } from "@/types/architecture";

type ArchitectureFlowNodeData = ArchitectureGraphNodeData & {
  onSelect?: (nodeId: string) => void;
};

type ArchitectureFlowNode = Node<ArchitectureFlowNodeData, "architectureNode">;

const nodePalette: Record<string, string> = {
  frontend: "border-tide/35 bg-tide/10 text-ink",
  ui: "border-brass/40 bg-brass/10 text-ink",
  api: "border-clay/35 bg-clay/10 text-ink",
  service: "border-ink/15 bg-white text-ink",
  ai: "border-moss/35 bg-moss/10 text-ink",
  storage: "border-ink/15 bg-paper text-ink",
  "vector-store": "border-moss/40 bg-moss/10 text-ink",
};

function mapGraphNode(node: ArchitectureGraphNode, onSelect: (nodeId: string) => void): ArchitectureFlowNode {
  return {
    id: node.id,
    type: "architectureNode",
    position: node.position,
    data: {
      ...node.data,
      onSelect,
    },
  };
}

function mapGraphEdge(edge: ArchitectureGraphEdge): Edge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: "smoothstep",
    animated: edge.animated,
  };
}

function formatNodeType(value: string) {
  return value.replace(/-/g, " ");
}

function ArchitectureNode({ id, data, selected }: NodeProps<ArchitectureFlowNode>) {
  const paletteClass = nodePalette[data.type] || "border-ink/15 bg-white text-ink";

  return (
    <div
      className={[
        "relative min-w-[220px] max-w-[260px] rounded-2xl border px-4 py-3 shadow-sm transition",
        paletteClass,
        selected ? "ring-2 ring-tide/40 shadow-md" : "",
        "cursor-pointer",
      ].join(" ")}
      onClick={() => data.onSelect?.(id)}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-3 !w-3 !border-2 !border-white !bg-tide"
      />
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold leading-6 text-ink">{data.title}</p>
            <p className="mt-1 text-[11px] uppercase tracking-[0.2em] text-ink/55">
              {formatNodeType(data.type)}
            </p>
          </div>
          <span className="rounded-full border border-ink/10 bg-white/70 px-2.5 py-1 text-[11px] font-semibold text-ink/70">
            {data.phase}
          </span>
        </div>
        <p className="text-xs leading-6 text-ink/70">{data.description}</p>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-3 !w-3 !border-2 !border-white !bg-brass"
      />
    </div>
  );
}

function ArchitectureWorkspaceContent() {
  const [nodes, setNodes, onNodesChange] = useNodesState<ArchitectureFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [graph, setGraph] = useState<ArchitectureGraphData | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadGraph() {
      setIsLoading(true);
      setError(null);

      try {
        const data = await getSystemArchitectureGraph();
        if (controller.signal.aborted) {
          return;
        }

        setGraph(data);
        const handleSelect = (nodeId: string) => {
          setSelectedNodeId(nodeId);
        };
        setNodes(data.nodes.map((node) => mapGraphNode(node, handleSelect)));
        setEdges(data.edges.map(mapGraphEdge));
        setSelectedNodeId(data.nodes[0]?.id ?? null);
      } catch (caughtError) {
        if (controller.signal.aborted) {
          return;
        }

        const message =
          caughtError instanceof ApiError
            ? caughtError.message
            : "Unable to load the architecture graph.";
        setError(message);
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadGraph();

    return () => controller.abort();
  }, [setEdges, setNodes]);

  const selectedNode = useMemo(() => {
    if (!graph || !selectedNodeId) {
      return null;
    }

    return graph.nodes.find((node) => node.id === selectedNodeId) ?? null;
  }, [graph, selectedNodeId]);

  const selectedNodeRelations = useMemo(() => {
    if (!graph || !selectedNodeId) {
      return { incoming: 0, outgoing: 0 };
    }

    return graph.edges.reduce(
      (accumulator, edge) => {
        if (edge.source === selectedNodeId) {
          accumulator.outgoing += 1;
        }
        if (edge.target === selectedNodeId) {
          accumulator.incoming += 1;
        }
        return accumulator;
      },
      { incoming: 0, outgoing: 0 }
    );
  }, [graph, selectedNodeId]);

  const nodeTypes = useMemo(
    () => ({
      architectureNode: ArchitectureNode,
    }),
    []
  );

  return (
    <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="border border-ink/10 bg-white/70 px-4 py-3 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Scope</p>
            <p className="mt-1 text-sm text-ink/75">Frontend, backend, AI, and storage layers</p>
          </div>
          <div className="border border-ink/10 bg-white/70 px-4 py-3 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Interaction</p>
            <p className="mt-1 text-sm text-ink/75">Click any node to inspect its detail panel</p>
          </div>
          <div className="border border-ink/10 bg-white/70 px-4 py-3 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Shape</p>
            <p className="mt-1 text-sm text-ink/75">React Flow-compatible nodes and edges</p>
          </div>
        </div>

        <div className="relative h-[42rem] overflow-hidden border border-ink/10 bg-white/70 shadow-sm">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(45,111,115,0.12),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(195,154,61,0.12),transparent_28%)]" />
          {isLoading ? (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-paper/70 backdrop-blur-sm">
              <div className="max-w-sm rounded-2xl border border-ink/10 bg-white px-5 py-4 text-sm leading-7 text-ink/70 shadow-sm">
                Loading the system architecture graph...
              </div>
            </div>
          ) : null}
          {error ? (
            <div className="absolute inset-x-4 top-4 z-10 border border-clay/25 bg-clay/10 px-4 py-3 text-sm leading-7 text-ink shadow-sm">
              {error}
            </div>
          ) : null}
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            proOptions={{ hideAttribution: true }}
            className="relative z-[1]"
            minZoom={0.35}
            maxZoom={1.4}
          >
            <MiniMap
              nodeColor={(node) => {
                const semanticType = (node.data as ArchitectureFlowNodeData | undefined)?.type ?? "service";
                if (semanticType === "frontend") return "#2d6f73";
                if (semanticType === "ui") return "#c39a3d";
                if (semanticType === "api") return "#b65f3b";
                if (semanticType === "ai") return "#66735c";
                if (semanticType === "vector-store") return "#66735c";
                return "#151815";
              }}
              maskColor="rgba(248,244,234,0.75)"
              className="!bg-white/70"
            />
            <Controls position="bottom-left" className="!bg-white/90 !shadow-sm" />
            <Background gap={24} size={1} color="rgba(21,24,21,0.08)" />
          </ReactFlow>
        </div>
      </div>

      <aside className="space-y-4">
        <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Selected Node</p>
          {selectedNode ? (
            <div className="mt-4 space-y-4">
              <div>
                <h2 className="text-2xl font-semibold text-ink">{selectedNode.data.title}</h2>
                <p className="mt-2 text-sm leading-7 text-ink/70">{selectedNode.data.description}</p>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="border border-ink/10 bg-paper/80 px-3 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-clay">Type</p>
                  <p className="mt-1 text-ink">{selectedNode.data.type}</p>
                </div>
                <div className="border border-ink/10 bg-paper/80 px-3 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-clay">Phase</p>
                  <p className="mt-1 text-ink">{selectedNode.data.phase}</p>
                </div>
                <div className="border border-ink/10 bg-paper/80 px-3 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-clay">Incoming</p>
                  <p className="mt-1 text-ink">{selectedNodeRelations.incoming}</p>
                </div>
                <div className="border border-ink/10 bg-paper/80 px-3 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-clay">Outgoing</p>
                  <p className="mt-1 text-ink">{selectedNodeRelations.outgoing}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-dashed border-ink/15 bg-paper/70 p-5 text-sm leading-7 text-ink/60">
              Click any node in the graph to inspect its metadata and relationship counts.
            </div>
          )}
        </div>

        <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Legend</p>
          <div className="mt-4 space-y-3 text-sm leading-7 text-ink/75">
            <div className="border-l-4 border-tide bg-paper px-4 py-3">Frontend and UI surfaces</div>
            <div className="border-l-4 border-brass bg-paper px-4 py-3">Backend services and API entry points</div>
            <div className="border-l-4 border-clay bg-paper px-4 py-3">AI model integration and orchestration</div>
            <div className="border-l-4 border-moss bg-paper px-4 py-3">Storage and retrieval layers</div>
          </div>
        </div>
      </aside>
    </section>
  );
}

export function ArchitectureGraphWorkspace() {
  return (
    <ReactFlowProvider>
      <ArchitectureWorkspaceContent />
    </ReactFlowProvider>
  );
}
