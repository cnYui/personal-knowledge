"""Prompt configuration schemas."""

from pydantic import BaseModel, Field


class PromptConfig(BaseModel):
    """Prompt configuration model."""

    key: str = Field(..., description='Prompt identifier key')
    content: str = Field(..., description='Prompt content')
    description: str | None = Field(None, description='Prompt description')


class PromptConfigUpdate(BaseModel):
    """Prompt configuration update model."""

    content: str = Field(..., min_length=1, description='New prompt content')
