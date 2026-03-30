from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.chat import ChatReference


class GraphRetrievalResult(BaseModel):
    context: str
    references: list[ChatReference] = Field(default_factory=list)
    has_enough_evidence: bool = False
    empty_reason: str = ''
    retrieved_edge_count: int = 0
    group_id: str = 'default'


class AgentPlanningDecision(BaseModel):
    action: Literal['rewrite', 'give_up'] = 'give_up'
    rewritten_query: str = ''
    reason: str = ''


class AgentTraceStep(BaseModel):
    step_type: Literal['chitchat', 'retrieval', 'planner', 'answer']
    query: str = ''
    message: str = ''
    evidence_found: bool | None = None
    retrieved_edge_count: int | None = None
    rewritten_query: str = ''
    action: str = ''


class AgentTrace(BaseModel):
    mode: Literal['chitchat', 'graph_rag'] = 'graph_rag'
    retrieval_rounds: int = 0
    final_action: str = ''
    steps: list[AgentTraceStep] = Field(default_factory=list)
