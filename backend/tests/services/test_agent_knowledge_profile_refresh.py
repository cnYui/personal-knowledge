from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from graphiti_core.errors import GroupsEdgesNotFoundError

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


@pytest.mark.anyio
async def test_extract_candidates_queries_recent_memory_group_ids(monkeypatch):
    requested_group_ids: list[str] = []

    async def fake_get_by_group_ids(driver, group_ids, limit):
        requested_group_ids.extend(group_ids)
        return []

    async def fake_get_by_uuids(driver, uuids):
        return []

    monkeypatch.setattr(
        'app.services.agent_knowledge_profile_refresh.EntityEdge.get_by_group_ids',
        fake_get_by_group_ids,
    )
    monkeypatch.setattr(
        'app.services.agent_knowledge_profile_refresh.EntityNode.get_by_uuids',
        fake_get_by_uuids,
    )

    memory_repository = SimpleNamespace(
        list_recent_graph_added=lambda db, limit: [
            SimpleNamespace(title='Team Knowledge', content='Graph context', group_id='team-a'),
            SimpleNamespace(title='More Team Notes', content='Extra graph context', group_id='team-a'),
        ]
    )
    graphiti_client = SimpleNamespace(
        _ensure_runtime_client=AsyncMock(),
        client=SimpleNamespace(driver=object()),
    )
    session = SimpleNamespace(close=lambda: None)
    service = AgentKnowledgeProfileRefreshService(
        memory_repository=memory_repository,
        graphiti_client=graphiti_client,
        session_factory=lambda: session,
    )

    await service._extract_candidates()

    assert requested_group_ids == ['team-a']


@pytest.mark.anyio
async def test_extract_candidates_silently_falls_back_when_graph_has_no_edges(monkeypatch, caplog):
    async def fake_get_by_group_ids(driver, group_ids, limit):
        raise GroupsEdgesNotFoundError(group_ids)

    async def fake_get_by_uuids(driver, uuids):
        return []

    monkeypatch.setattr(
        'app.services.agent_knowledge_profile_refresh.EntityEdge.get_by_group_ids',
        fake_get_by_group_ids,
    )
    monkeypatch.setattr(
        'app.services.agent_knowledge_profile_refresh.EntityNode.get_by_uuids',
        fake_get_by_uuids,
    )

    memory_repository = SimpleNamespace(
        list_recent_graph_added=lambda db, limit: [
            SimpleNamespace(title='Alpha Topic', content='Alpha beta gamma', group_id='team-a'),
        ]
    )
    graphiti_client = SimpleNamespace(
        _ensure_runtime_client=AsyncMock(),
        client=SimpleNamespace(driver=object()),
    )
    session = SimpleNamespace(close=lambda: None)
    service = AgentKnowledgeProfileRefreshService(
        memory_repository=memory_repository,
        graphiti_client=graphiti_client,
        session_factory=lambda: session,
    )

    with caplog.at_level('WARNING'):
        candidates = await service._extract_candidates()

    assert 'Failed to extract graph candidates for knowledge profile' not in caplog.text
    assert 'Alpha' in candidates.top_entities
