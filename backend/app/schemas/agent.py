from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.chat import ChatReference


class GraphRetrievalResult(BaseModel):
    context: str
    references: list[ChatReference] = Field(default_factory=list)
    has_enough_evidence: bool = False
    empty_reason: str = ''
    retrieved_edge_count: int = 0
    group_id: str = 'default'


class GraphHistoryQuery(BaseModel):
    target_type: Literal['memory', 'entity', 'relation_topic']
    target_value: str
    mode: Literal['timeline', 'compare', 'summarize']
    question: str = ''
    constraints: dict[str, Any] = Field(default_factory=dict)


class GraphHistoryResolvedTarget(BaseModel):
    memory_id: str | None = None
    memory_title: str | None = None
    latest_version: int | None = None
    version_count: int = 0
    entity_id: str | None = None
    canonical_name: str | None = None
    matched_alias: str | None = None
    candidate_count: int = 0


class GraphHistoryTimelineItem(BaseModel):
    version: int
    is_latest: bool
    reference_time: str | None = None
    created_at: str | None = None
    episode_count: int = 0
    summary_excerpt: str = ''


class GraphHistoryComparisonItem(BaseModel):
    from_version: int
    to_version: int
    change_summary: str
    added_points: list[str] = Field(default_factory=list)
    removed_points: list[str] = Field(default_factory=list)
    updated_points: list[str] = Field(default_factory=list)


class GraphHistoryEvidenceItem(BaseModel):
    version: int | None = None
    episode_uuid: str = ''
    fact: str = ''
    reference_time: str | None = None


class GraphHistoryResult(BaseModel):
    target_type: Literal['memory', 'entity', 'relation_topic']
    target_value: str
    resolved_target: GraphHistoryResolvedTarget | None = None
    mode: Literal['timeline', 'compare', 'summarize']
    status: Literal[
        'ok',
        'not_found',
        'insufficient_history',
        'unsupported_target_type',
        'insufficient_evidence',
        'ambiguous_target',
        'error',
    ]
    timeline: list[GraphHistoryTimelineItem] = Field(default_factory=list)
    comparisons: list[GraphHistoryComparisonItem] = Field(default_factory=list)
    summary: str = ''
    evidence: list[GraphHistoryEvidenceItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class AgentTraceStep(BaseModel):
    step_type: Literal['retrieval', 'answer', 'fallback']
    query: str = ''
    message: str = ''
    evidence_found: bool | None = None
    retrieved_edge_count: int | None = None
    rewritten_query: str = ''
    action: str = ''


class AgentTrace(BaseModel):
    mode: Literal['graph_rag'] = 'graph_rag'
    retrieval_rounds: int = 0
    final_action: str = ''
    steps: list[AgentTraceStep] = Field(default_factory=list)
