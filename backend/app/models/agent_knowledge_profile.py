from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentKnowledgeProfile(Base):
    __tablename__ = "agent_knowledge_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_type: Mapped[str] = mapped_column(String(64), nullable=False, server_default='global_agent_overlay')
    major_topics: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    high_frequency_entities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    high_frequency_relations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recent_focuses: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rendered_overlay: Mapped[str] = mapped_column(Text, nullable=False, server_default='')
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default='building')
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
