"""Graph-related schemas for memory operations and visualization."""

from pydantic import BaseModel


# Memory graph operation schemas
class AddToGraphResponse(BaseModel):
    message: str
    memory_id: str
    graph_status: str


class BatchAddToGraphRequest(BaseModel):
    memory_ids: list[str]


class BatchAddToGraphResponse(BaseModel):
    message: str
    queued_count: int
    memory_ids: list[str]


class GraphStatusResponse(BaseModel):
    memory_id: str
    graph_status: str
    graph_episode_uuid: str | None
    graph_added_at: str | None
    graph_error: str | None


# Graph visualization schemas
class GraphNode(BaseModel):
    """Graph node representation."""

    id: str
    label: str
    type: str  # 'entity', 'episode'
    summary: str | None = None


class GraphEdge(BaseModel):
    """Graph edge representation."""

    id: str
    source: str
    target: str
    label: str
    fact: str | None = None


class GraphData(BaseModel):
    """Complete graph data."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: dict[str, int]
