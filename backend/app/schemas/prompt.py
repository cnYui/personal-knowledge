"""Prompt configuration schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class PromptConfig(BaseModel):
    """Prompt configuration model."""

    key: str = Field(..., description='Prompt identifier key')
    content: str = Field(..., description='Prompt content')
    description: str | None = Field(None, description='Prompt description')


class PromptConfigUpdate(BaseModel):
    """Prompt configuration update model."""

    content: str = Field(..., min_length=1, description='New prompt content')


class KnowledgeProfileResponse(BaseModel):
    """Knowledge profile response model."""

    status: str = Field(..., description='Profile status: building, ready, failed')
    major_topics: list[str] = Field(default_factory=list, description='Major knowledge topics')
    high_frequency_entities: list[str] = Field(default_factory=list, description='High frequency entities')
    high_frequency_relations: list[str] = Field(default_factory=list, description='High frequency relations')
    recent_focuses: list[str] = Field(default_factory=list, description='Recent knowledge focuses')
    rendered_overlay: str = Field('', description='Rendered prompt overlay text')
    updated_at: datetime | None = Field(None, description='Last update time')
    error_message: str | None = Field(None, description='Error message if failed')


class ComposedPromptResponse(BaseModel):
    """Composed system prompt response model."""

    base_prompt: str = Field(..., description='Base system prompt')
    overlay: str = Field('', description='Dynamic knowledge profile overlay')
    composed_prompt: str = Field(..., description='Final composed system prompt')
    profile_status: str | None = Field(None, description='Knowledge profile status')
