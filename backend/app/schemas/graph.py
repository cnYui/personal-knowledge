from pydantic import BaseModel


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
