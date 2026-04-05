from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyFieldStatus(BaseModel):
    configured: bool
    masked_value: str = ''


class RuntimeModelConfig(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str


class RuntimeModelConfigStatus(BaseModel):
    provider: str
    base_url: str
    model: str
    api_key: ApiKeyFieldStatus


class AgentKnowledgeProfileRead(BaseModel):
    available: bool
    status: str
    major_topics: list[str] = Field(default_factory=list)
    high_frequency_entities: list[str] = Field(default_factory=list)
    high_frequency_relations: list[str] = Field(default_factory=list)
    recent_focuses: list[str] = Field(default_factory=list)
    rendered_overlay: str = ''
    updated_at: datetime | None = None
    error_message: str | None = None


class ModelConfigRead(BaseModel):
    dialog: RuntimeModelConfigStatus
    knowledge_build: RuntimeModelConfigStatus
    knowledge_profile: AgentKnowledgeProfileRead


class ModelConfigUpdate(BaseModel):
    dialog_api_key: str | None = Field(default=None)
    knowledge_build_api_key: str | None = Field(default=None)
