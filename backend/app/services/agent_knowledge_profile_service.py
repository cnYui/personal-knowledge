from dataclasses import dataclass
from datetime import datetime

from app.core.database import SessionLocal
from app.repositories.agent_knowledge_profile_repository import AgentKnowledgeProfileRepository


@dataclass
class AgentKnowledgeProfileSnapshot:
    status: str
    major_topics: list[str]
    high_frequency_entities: list[str]
    high_frequency_relations: list[str]
    recent_focuses: list[str]
    rendered_overlay: str
    updated_at: datetime | None
    error_message: str | None


class AgentKnowledgeProfileService:
    def __init__(
        self,
        *,
        repository: AgentKnowledgeProfileRepository | None = None,
        session_factory=SessionLocal,
    ) -> None:
        self.repository = repository or AgentKnowledgeProfileRepository()
        self.session_factory = session_factory

    def get_latest_ready_snapshot(self) -> AgentKnowledgeProfileSnapshot | None:
        db = self.session_factory()
        try:
            profile = self.repository.get_latest_ready_profile(db)
            if profile is None:
                return None
            return AgentKnowledgeProfileSnapshot(
                status=str(profile.status or 'ready'),
                major_topics=list(profile.major_topics or []),
                high_frequency_entities=list(profile.high_frequency_entities or []),
                high_frequency_relations=list(profile.high_frequency_relations or []),
                recent_focuses=list(profile.recent_focuses or []),
                rendered_overlay=str(profile.rendered_overlay or ''),
                updated_at=profile.updated_at,
                error_message=profile.error_message,
            )
        finally:
            db.close()

    def get_latest_snapshot(self) -> AgentKnowledgeProfileSnapshot | None:
        db = self.session_factory()
        try:
            profile = self.repository.get_latest_profile(db)
            if profile is None:
                return None
            return AgentKnowledgeProfileSnapshot(
                status=str(profile.status or 'building'),
                major_topics=list(profile.major_topics or []),
                high_frequency_entities=list(profile.high_frequency_entities or []),
                high_frequency_relations=list(profile.high_frequency_relations or []),
                recent_focuses=list(profile.recent_focuses or []),
                rendered_overlay=str(profile.rendered_overlay or ''),
                updated_at=profile.updated_at,
                error_message=profile.error_message,
            )
        finally:
            db.close()

    def get_latest_ready_overlay(self) -> str:
        snapshot = self.get_latest_ready_snapshot()
        if snapshot is None:
            return ''
        return snapshot.rendered_overlay.strip()

    def compose_system_prompt(self, base_prompt: str) -> str:
        overlay = self.get_latest_ready_overlay()
        if not overlay:
            return base_prompt
        return f'{base_prompt.rstrip()}\n\n{overlay.strip()}'


agent_knowledge_profile_service = AgentKnowledgeProfileService()
