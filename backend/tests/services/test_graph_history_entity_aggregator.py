from datetime import datetime, timezone

import pytest

from app.core.database import Base
from app.models.memory import Memory, MemoryGraphEpisode
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository
from app.repositories.memory_repository import MemoryRepository
from app.services.graph_history_entity_aggregator import GraphHistoryEntityAggregator
from tests.conftest import TestingSessionLocal, test_engine


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


def test_entity_aggregator_collects_versions_across_multiple_memories(db_session):
    memory_a = Memory(title='OpenAI Funding', title_status='ready', content='OpenAI completed funding', group_id='default')
    memory_b = Memory(title='OpenAI Board', title_status='ready', content='OpenAI board changed', group_id='default')
    db_session.add_all([memory_a, memory_b])
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory_a.id, episode_uuid='a-v1', version=1, chunk_index=0, is_latest=True),
            MemoryGraphEpisode(memory_id=memory_b.id, episode_uuid='b-v2', version=2, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    aggregator = GraphHistoryEntityAggregator(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
    )

    events = aggregator.collect_entity_events(db_session, canonical_name='OpenAI')

    assert len(events) == 2
    assert {event['memory_title'] for event in events} == {'OpenAI Funding', 'OpenAI Board'}


def test_entity_aggregator_respects_top_k_constraint(db_session):
    memory_a = Memory(title='OpenAI Funding', title_status='ready', content='OpenAI completed funding', group_id='default')
    memory_b = Memory(title='OpenAI Board', title_status='ready', content='OpenAI board changed', group_id='default')
    db_session.add_all([memory_a, memory_b])
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory_a.id, episode_uuid='a-v1', version=1, chunk_index=0, is_latest=True),
            MemoryGraphEpisode(memory_id=memory_b.id, episode_uuid='b-v2', version=2, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    aggregator = GraphHistoryEntityAggregator(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
    )

    events = aggregator.collect_entity_events(db_session, canonical_name='OpenAI', top_k_events=1)

    assert len(events) == 1


def test_collect_entity_events_uses_stable_memory_id_tiebreaker_for_tied_rows(db_session):
    tied_time = datetime(2026, 4, 7, 0, 0, tzinfo=timezone.utc)
    memory_a = Memory(id='aaa-memory', title='OpenAI Alpha', title_status='ready', content='OpenAI alpha event', group_id='default')
    memory_b = Memory(id='zzz-memory', title='OpenAI Zeta', title_status='ready', content='OpenAI zeta event', group_id='default')
    db_session.add_all([memory_a, memory_b])
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory_a.id, episode_uuid='alpha-v1', version=1, chunk_index=0, is_latest=True, created_at=tied_time),
            MemoryGraphEpisode(memory_id=memory_b.id, episode_uuid='zeta-v1', version=1, chunk_index=0, is_latest=True, created_at=tied_time),
        ]
    )
    db_session.commit()

    aggregator = GraphHistoryEntityAggregator(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
    )

    events = aggregator.collect_entity_events(db_session, canonical_name='OpenAI', top_k_events=10)

    assert [event['memory_id'] for event in events] == ['aaa-memory', 'zzz-memory']


def test_count_versions_for_memories_returns_zero_for_empty_input(db_session):
    repo = MemoryGraphEpisodeRepository()

    assert repo.count_versions_for_memories(db_session, []) == 0
