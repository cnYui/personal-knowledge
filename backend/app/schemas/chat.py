from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    answer: str
    references: list[str] = Field(default_factory=list)


class ChatMessageRead(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
