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


def build_aggregator():
    return GraphHistoryEntityAggregator(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
    )


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

    aggregator = build_aggregator()

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

    aggregator = build_aggregator()

    events = aggregator.collect_entity_events(db_session, canonical_name='OpenAI', top_k_events=1)

    assert len(events) == 1


def test_collect_entity_events_returns_latest_first(db_session):
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

    aggregator = build_aggregator()

    events = aggregator.collect_entity_events(db_session, canonical_name='OpenAI', top_k_events=10)

    assert events[0]['version'] >= events[-1]['version']


def test_count_entity_events_counts_all_versions_across_more_than_ten_matching_memories(db_session):
    memories = [
        Memory(
            title=f'OpenAI Note {index}',
            title_status='ready',
            content=f'OpenAI event {index}',
            group_id='default',
        )
        for index in range(11)
    ]
    db_session.add_all(memories)
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(
                memory_id=memory.id,
                episode_uuid=f'openai-note-v{index + 1}',
                version=index + 1,
                chunk_index=0,
                is_latest=True,
            )
            for index, memory in enumerate(memories)
        ]
    )
    db_session.commit()

    aggregator = build_aggregator()

    assert aggregator.count_entity_events(db_session, canonical_name='OpenAI') == 11


def test_collect_entity_events_uses_stable_memory_id_tiebreaker_for_tied_rows(db_session):
    tied_time = datetime(2026, 4, 7, 0, 0, tzinfo=timezone.utc)
    memory_a = Memory(
        id='aaa-memory',
        title='OpenAI Alpha',
        title_status='ready',
        content='OpenAI alpha event',
        group_id='default',
    )
    memory_b = Memory(
        id='zzz-memory',
        title='OpenAI Zeta',
        title_status='ready',
        content='OpenAI zeta event',
        group_id='default',
    )
    db_session.add_all([memory_a, memory_b])
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(
                memory_id=memory_a.id,
                episode_uuid='alpha-v1',
                version=1,
                chunk_index=0,
                is_latest=True,
                created_at=tied_time,
            ),
            MemoryGraphEpisode(
                memory_id=memory_b.id,
                episode_uuid='zeta-v1',
                version=1,
                chunk_index=0,
                is_latest=True,
                created_at=tied_time,
            ),
        ]
    )
    db_session.commit()

    aggregator = build_aggregator()

    events = aggregator.collect_entity_events(db_session, canonical_name='OpenAI', top_k_events=10)

    assert [event['memory_id'] for event in events] == ['aaa-memory', 'zzz-memory']


def test_collect_entity_events_returns_empty_for_no_matches(db_session):
    aggregator = build_aggregator()

    events = aggregator.collect_entity_events(db_session, canonical_name='Missing')

    assert events == []