from __future__ import annotations

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


class ModelConfigRead(BaseModel):
    dialog: RuntimeModelConfigStatus
    knowledge_build: RuntimeModelConfigStatus


class ModelConfigUpdate(BaseModel):
    dialog_api_key: str | None = Field(default=None)
    knowledge_build_api_key: str | None = Field(default=None)
