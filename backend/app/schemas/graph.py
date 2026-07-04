"""Graph API schemas."""

from pydantic import BaseModel


class GraphNode(BaseModel):
    id: int
    ip: str
    is_victim: bool
    is_source: bool
    degree: float


class GraphEdge(BaseModel):
    source: int
    target: int
    weight: float


class LiveGraphResponse(BaseModel):
    victim_ip: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    is_attack: bool | None = None
    probability: float | None = None
    num_flows: int
