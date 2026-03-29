from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    title: str = Field(default='标题生成中', min_length=1, max_length=255)
    content: str = Field(min_length=1)
    group_id: str = Field(default='default', min_length=1, max_length=64)
    title_status: Literal['pending', 'ready', 'failed'] = 'pending'


class MemoryUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    title_status: Literal['pending', 'ready', 'failed'] | None = None


class MemoryRead(BaseModel):
    id: str
    title: str
    title_status: Literal['pending', 'ready', 'failed']
    content: str
    group_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    graph_status: str = 'not_added'
    graph_episode_uuid: str | None = None
    graph_added_at: datetime | None = None

    model_config = {"from_attributes": True}
