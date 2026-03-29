from typing import Literal

from pydantic import BaseModel


class MemoryUploadResponse(BaseModel):
    id: str
    title: str
    title_status: Literal['pending', 'ready', 'failed']
    content: str
    group_id: str
    images_count: int
    processing_status: str
