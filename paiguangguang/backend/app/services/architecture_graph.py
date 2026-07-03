from __future__ import annotations

from app.schemas.architecture import (
    ArchitectureGraphData,
    ArchitectureGraphEdge,
    ArchitectureGraphNode,
    ArchitectureGraphNodeData,
    ArchitectureGraphPosition,
)


def _node(
    node_id: str,
    *,
    title: str,
    node_type: str,
    phase: str,
    description: str,
    x: int,
    y: int,
) -> ArchitectureGraphNode:
    return ArchitectureGraphNode(
        id=node_id,
        position=ArchitectureGraphPosition(x=x, y=y),
        data=ArchitectureGraphNodeData(
            title=title,
            type=node_type,
            phase=phase,
            description=description,
        ),
    )


def _edge(source: str, target: str) -> ArchitectureGraphEdge:
    return ArchitectureGraphEdge(
        id=f"{source}__to__{target}",
        source=source,
        target=target,
    )


class ArchitectureGraphService:
    def get_system_graph(self) -> ArchitectureGraphData:
        nodes = [
            _node(
                "frontend-shell",
                title="Frontend App Shell",
                node_type="frontend",
                phase="Frontend",
                description="Next.js app router shell that hosts the portfolio and agent surfaces.",
                x=80,
                y=160,
            ),
            _node(
                "portfolio-chat-ui",
                title="Portfolio Chat UI",
                node_type="ui",
                phase="Frontend",
                description="Interactive V1 chat surface for the portfolio narrative and project walkthrough.",
                x=320,
                y=60,
            ),
            _node(
                "knowledge-agent-ui",
                title="Knowledge Agent UI",
                node_type="ui",
                phase="Frontend",
                description="V2 workspace for document ingestion, retrieval, answer generation, and citations.",
                x=320,
                y=260,
            ),
            _node(
                "fastapi-router",
                title="FastAPI API Router",
                node_type="api",
                phase="Backend",
                description="Single API entry point that routes chat, RAG, and architecture requests.",
                x=600,
                y=160,
            ),
            _node(
                "portfolio-chat-service",
                title="Portfolio Chat Service",
                node_type="service",
                phase="Backend",
                description="Formats the system prompt, manages session memory, and calls DeepSeek for V1 chat.",
                x=860,
                y=20,
            ),
            _node(
                "rag-ingestion-service",
                title="RAG Ingestion Service",
                node_type="service",
                phase="Backend",
                description="Normalizes text, creates chunks, stores records, and writes embeddings to Chroma.",
                x=860,
                y=170,
            ),
            _node(
                "rag-query-service",
                title="RAG Query Service",
                node_type="service",
                phase="Backend",
                description="Retrieves relevant chunks, assembles context, and orchestrates grounded answers.",
                x=860,
                y=320,
            ),
            _node(
                "deepseek-client",
                title="DeepSeek Client",
                node_type="ai",
                phase="AI",
                description="HTTP client wrapper used by chat and RAG query flows to call the model API.",
                x=1120,
                y=40,
            ),
            _node(
                "rag-document-repository",
                title="RAG Document Repository",
                node_type="storage",
                phase="Storage",
                description="In-memory document and ingestion store used for registration and chunk metadata.",
                x=1120,
                y=190,
            ),
            _node(
                "chroma-rag-store",
                title="Chroma Retrieval Layer",
                node_type="vector-store",
                phase="Storage",
                description="Persistent vector store used for similarity search over ingested chunks.",
                x=1120,
                y=340,
            ),
        ]

        edges = [
            _edge("frontend-shell", "portfolio-chat-ui"),
            _edge("frontend-shell", "knowledge-agent-ui"),
            _edge("portfolio-chat-ui", "fastapi-router"),
            _edge("knowledge-agent-ui", "fastapi-router"),
            _edge("fastapi-router", "portfolio-chat-service"),
            _edge("fastapi-router", "rag-ingestion-service"),
            _edge("fastapi-router", "rag-query-service"),
            _edge("portfolio-chat-service", "deepseek-client"),
            _edge("rag-ingestion-service", "rag-document-repository"),
            _edge("rag-ingestion-service", "chroma-rag-store"),
            _edge("rag-query-service", "chroma-rag-store"),
            _edge("rag-query-service", "deepseek-client"),
        ]

        return ArchitectureGraphData(nodes=nodes, edges=edges)


_ARCHITECTURE_GRAPH_SERVICE = ArchitectureGraphService()


def get_architecture_graph_service() -> ArchitectureGraphService:
    return _ARCHITECTURE_GRAPH_SERVICE
