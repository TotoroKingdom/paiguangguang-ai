from __future__ import annotations

from pydantic import BaseModel, Field


class ArchitectureGraphPosition(BaseModel):
    x: int
    y: int


class ArchitectureGraphNodeData(BaseModel):
    title: str = Field(min_length=1)
    type: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    description: str = Field(min_length=1)


class ArchitectureGraphNode(BaseModel):
    id: str = Field(min_length=1)
    type: str = "default"
    position: ArchitectureGraphPosition
    data: ArchitectureGraphNodeData


class ArchitectureGraphEdge(BaseModel):
    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    type: str = "smoothstep"
    animated: bool = False


class ArchitectureGraphData(BaseModel):
    nodes: list[ArchitectureGraphNode]
    edges: list[ArchitectureGraphEdge]
