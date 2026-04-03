from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.database import Base
from app.models.agent_knowledge_profile import AgentKnowledgeProfile
from app.services.agent_knowledge_profile_refresh import (
    AgentKnowledgeProfileRefreshScheduler,
    AgentKnowledgeProfileRefreshService,
    PROFILE_TYPE,
    ProfileCandidateSummary,
)
from app.repositories.agent_knowledge_profile_repository import AgentKnowledgeProfileRepository
from tests.conftest import TestingSessionLocal, test_engine


@pytest.mark.anyio
async def test_refresh_service_renders_overlay_from_model_output():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        db.query(AgentKnowledgeProfile).delete()
        db.commit()
    finally:
        db.close()

    service = AgentKnowledgeProfileRefreshService(session_factory=TestingSessionLocal)
    service._extract_candidates = AsyncMock(
        return_value=ProfileCandidateSummary(
            top_entities=['UI', 'UX'],
            top_relations=['属于'],
            recent_entities=['冒烟测试'],
            recent_titles=['UI UX 概念与区别'],
        )
    )
    service._compress_profile = AsyncMock(
        return_value={
            'major_topics': ['前端开发'],
            'high_frequency_entities': ['UI', 'UX'],
            'high_frequency_relations': ['属于'],
            'recent_focuses': ['冒烟测试'],
        }
    )

    await service.refresh_global_profile()

    db = TestingSessionLocal()
    try:
        snapshot = AgentKnowledgeProfileRepository().get_latest_ready_profile(db, profile_type=PROFILE_TYPE)
        assert snapshot is not None
        assert '主要主题：前端开发' in snapshot.rendered_overlay
        assert snapshot.major_topics == ['前端开发']
        assert snapshot.recent_focuses == ['冒烟测试']
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.mark.anyio
async def test_refresh_scheduler_debounces_requests():
    refresh_service = SimpleNamespace(refresh_global_profile=AsyncMock())
    scheduler = AgentKnowledgeProfileRefreshScheduler(
        refresh_service=refresh_service,
        debounce_seconds=0,
    )

    scheduler.request_refresh(reason='a')
    scheduler.request_refresh(reason='b')
    await scheduler._task

    refresh_service.refresh_global_profile.assert_awaited_once()
