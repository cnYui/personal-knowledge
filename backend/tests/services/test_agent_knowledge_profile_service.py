from app.core.database import Base
from app.models.agent_knowledge_profile import AgentKnowledgeProfile
from app.repositories.agent_knowledge_profile_repository import AgentKnowledgeProfileRepository
from app.services.agent_knowledge_profile_service import AgentKnowledgeProfileService
from tests.conftest import TestingSessionLocal, test_engine


def test_agent_knowledge_profile_service_returns_latest_ready_overlay():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        repo = AgentKnowledgeProfileRepository()
        profile = repo.create_building_profile(db)
        repo.mark_profile_ready(
            db,
            profile,
            major_topics=['测试'],
            high_frequency_entities=['UI'],
            high_frequency_relations=['属于'],
            recent_focuses=['冒烟测试'],
            rendered_overlay='当前知识图谱知识画像（自动生成）：\n- 主要主题：测试',
        )
    finally:
        db.close()

    service = AgentKnowledgeProfileService(
        repository=AgentKnowledgeProfileRepository(),
        session_factory=TestingSessionLocal,
    )
    overlay = service.get_latest_ready_overlay()
    composed = service.compose_system_prompt('base prompt')

    assert '主要主题：测试' in overlay
    assert composed.endswith(overlay)

    Base.metadata.drop_all(bind=test_engine)


def test_agent_knowledge_profile_service_returns_base_prompt_when_no_profile():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        db.query(AgentKnowledgeProfile).delete()
        db.commit()
    finally:
        db.close()

    service = AgentKnowledgeProfileService(
        repository=AgentKnowledgeProfileRepository(),
        session_factory=TestingSessionLocal,
    )

    assert service.get_latest_ready_overlay() == ''
    assert service.compose_system_prompt('base prompt') == 'base prompt'

    Base.metadata.drop_all(bind=test_engine)
