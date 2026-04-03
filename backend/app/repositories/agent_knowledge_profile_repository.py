from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_knowledge_profile import AgentKnowledgeProfile


class AgentKnowledgeProfileRepository:
    def get_latest_ready_profile(
        self,
        db: Session,
        *,
        profile_type: str = 'global_agent_overlay',
    ) -> AgentKnowledgeProfile | None:
        query = (
            select(AgentKnowledgeProfile)
            .where(
                AgentKnowledgeProfile.profile_type == profile_type,
                AgentKnowledgeProfile.status == 'ready',
            )
            .order_by(AgentKnowledgeProfile.updated_at.desc(), AgentKnowledgeProfile.id.desc())
        )
        return db.scalar(query)

    def get_latest_profile(
        self,
        db: Session,
        *,
        profile_type: str = 'global_agent_overlay',
    ) -> AgentKnowledgeProfile | None:
        query = (
            select(AgentKnowledgeProfile)
            .where(AgentKnowledgeProfile.profile_type == profile_type)
            .order_by(AgentKnowledgeProfile.updated_at.desc(), AgentKnowledgeProfile.id.desc())
        )
        return db.scalar(query)

    def create_building_profile(
        self,
        db: Session,
        *,
        profile_type: str = 'global_agent_overlay',
    ) -> AgentKnowledgeProfile:
        profile = AgentKnowledgeProfile(
            profile_type=profile_type,
            major_topics=[],
            high_frequency_entities=[],
            high_frequency_relations=[],
            recent_focuses=[],
            rendered_overlay='',
            status='building',
            error_message=None,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    def mark_profile_ready(
        self,
        db: Session,
        profile: AgentKnowledgeProfile,
        *,
        major_topics: list[str],
        high_frequency_entities: list[str],
        high_frequency_relations: list[str],
        recent_focuses: list[str],
        rendered_overlay: str,
    ) -> AgentKnowledgeProfile:
        profile.major_topics = major_topics
        profile.high_frequency_entities = high_frequency_entities
        profile.high_frequency_relations = high_frequency_relations
        profile.recent_focuses = recent_focuses
        profile.rendered_overlay = rendered_overlay
        profile.status = 'ready'
        profile.error_message = None
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    def mark_profile_failed(
        self,
        db: Session,
        profile: AgentKnowledgeProfile,
        *,
        error_message: str,
    ) -> AgentKnowledgeProfile:
        profile.status = 'failed'
        profile.error_message = error_message
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
