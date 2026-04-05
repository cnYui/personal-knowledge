from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DailyReviewOverview(BaseModel):
    recommended_count: int = 0
    recent_memory_count: int = 0
    recent_graph_added_count: int = 0
    active_topics: list[str] = Field(default_factory=list)


class DailyReviewReason(BaseModel):
    code: str
    label: str


class DailyReviewCard(BaseModel):
    id: str
    title: str
    summary: str
    content: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    graph_status: str = 'not_added'
    graph_added_at: datetime | None = None
    score: int = 0
    tags: list[str] = Field(default_factory=list)
    reasons: list[DailyReviewReason] = Field(default_factory=list)


class DailyReviewTopic(BaseModel):
    topic: str
    count: int = 0
    last_seen_at: datetime | None = None
    summary: str


class DailyReviewResponse(BaseModel):
    overview: DailyReviewOverview
    recommended: list[DailyReviewCard] = Field(default_factory=list)
    topic_focuses: list[DailyReviewTopic] = Field(default_factory=list)
    graph_highlights: list[DailyReviewCard] = Field(default_factory=list)
    needs_refinement: list[DailyReviewCard] = Field(default_factory=list)
