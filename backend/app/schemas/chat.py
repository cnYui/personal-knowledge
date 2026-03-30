from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatReference(BaseModel):
    """Reference from knowledge graph"""

    type: Literal['entity', 'relationship']
    name: str | None = None
    summary: str | None = None
    fact: str | None = None


class ChatResponse(BaseModel):
    answer: str
    references: list[ChatReference] = Field(default_factory=list)
    agent_trace: dict[str, Any] | None = None


class ChatMessageRead(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
