import pytest

from app.core.database import Base
from app.models.memory import Memory, MemoryGraphEpisode
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository
from app.repositories.memory_repository import MemoryRepository
from app.schemas.agent import GraphHistoryQuery
from app.services.graph_history_entity_aggregator import GraphHistoryEntityAggregator
from app.services.graph_history_entity_resolver import GraphHistoryEntityResolver
from app.services.graph_history_service import GraphHistoryService
from tests.conftest import TestingSessionLocal, test_engine


def build_service(db_session, **kwargs):
    return GraphHistoryService(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
        db_factory=lambda: db_session,
        **kwargs,
    )


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


def test_get_memory_timeline_returns_ok_result_with_resolved_target(db_session):
    service = build_service(db_session)
    memory = Memory(title='Python Note', title_status='ready', content='v2 body', group_id='default')
    db_session.add(memory)
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v1', version=1, chunk_index=0, is_latest=False),
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v2', version=2, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    result = service.query(
        GraphHistoryQuery(target_type='memory', target_value=memory.id, mode='timeline', question='它如何变化？')
    )

    assert result.status == 'ok'
    assert result.resolved_target.memory_id == memory.id
    assert result.resolved_target.memory_title == 'Python Note'
    assert result.resolved_target.latest_version == 2
    assert result.resolved_target.version_count == 2
    assert [item.version for item in result.timeline] == [2, 1]
    assert result.timeline[0].summary_excerpt == 'Python Note v2'


def test_query_relation_topic_timeline_returns_minimal_result(db_session):
    service = build_service(db_session)

    result = service.query(
        GraphHistoryQuery(target_type='relation_topic', target_value='entity-1', mode='timeline', question='关系历史？')
    )

    assert result.status == 'ok'
    assert result.target_type == 'relation_topic'
    assert result.summary == '围绕 entity-1 的历史查询已进入 minimal 模式。'


def test_query_entity_timeline_returns_aggregated_events(db_session):
    service = build_service(
        db_session,
        entity_resolver=GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI', 'Open AI']}),
        entity_aggregator=GraphHistoryEntityAggregator(
            memory_repository=MemoryRepository(),
            episode_repository=MemoryGraphEpisodeRepository(),
        ),
    )
    memory_a = Memory(title='OpenAI Funding', title_status='ready', content='OpenAI completed funding', group_id='default')
    memory_b = Memory(title='OpenAI Board', title_status='ready', content='OpenAI board changed', group_id='default')
    db_session.add_all([memory_a, memory_b])
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory_a.id, episode_uuid='openai-funding-v1', version=1, chunk_index=0, is_latest=True),
            MemoryGraphEpisode(memory_id=memory_b.id, episode_uuid='openai-board-v2', version=2, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    result = service.query(
        GraphHistoryQuery(
            target_type='entity',
            target_value='Open AI',
            mode='timeline',
            question='这个实体如何演化？',
            constraints={'top_k_events': 10},
        )
    )

    assert result.status == 'ok'
    assert result.resolved_target is not None
    assert result.resolved_target.canonical_name == 'OpenAI'
    assert result.resolved_target.matched_alias == 'Open AI'
    assert len(result.timeline) == 2
    assert {item.summary_excerpt for item in result.timeline} == {'OpenAI Funding v1', 'OpenAI Board v2'}


def test_query_entity_returns_ambiguous_target_when_resolver_cannot_disambiguate(db_session):
    service = build_service(
        db_session,
        entity_resolver=GraphHistoryEntityResolver(alias_map={'Apple Inc.': ['Apple'], 'Apple Fruit': ['Apple']}),
        entity_aggregator=GraphHistoryEntityAggregator(
            memory_repository=MemoryRepository(),
            episode_repository=MemoryGraphEpisodeRepository(),
        ),
    )

    result = service.query(
        GraphHistoryQuery(target_type='entity', target_value='Apple', mode='timeline', question='Apple 如何变化？')
    )

    assert result.status == 'ambiguous_target'
    assert result.resolved_target is not None
    assert result.resolved_target.canonical_name is None
    assert result.resolved_target.candidate_count == 2
    assert result.timeline == []


def test_query_entity_summarize_uses_full_event_count_even_when_top_k_truncates_timeline(db_session):
    service = build_service(
        db_session,
        entity_resolver=GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI']}),
        entity_aggregator=GraphHistoryEntityAggregator(
            memory_repository=MemoryRepository(),
            episode_repository=MemoryGraphEpisodeRepository(),
        ),
    )
    memory_a = Memory(title='OpenAI Funding', title_status='ready', content='OpenAI completed funding', group_id='default')
    memory_b = Memory(title='OpenAI Board', title_status='ready', content='OpenAI board changed', group_id='default')
    db_session.add_all([memory_a, memory_b])
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory_a.id, episode_uuid='openai-funding-v1', version=1, chunk_index=0, is_latest=True),
            MemoryGraphEpisode(memory_id=memory_b.id, episode_uuid='openai-board-v2', version=2, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    result = service.query(
        GraphHistoryQuery(
            target_type='entity',
            target_value='OpenAI',
            mode='summarize',
            question='总结这个实体的历史',
            constraints={'top_k_events': 1},
        )
    )

    assert result.status == 'ok'
    assert result.resolved_target is not None
    assert result.resolved_target.canonical_name == 'OpenAI'
    assert result.resolved_target.version_count == 2
    assert len(result.timeline) == 1
    assert result.summary == 'OpenAI 共关联 2 条历史事件。'


def test_query_entity_compare_requires_at_least_two_events(db_session):
    service = build_service(
        db_session,
        entity_resolver=GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI']}),
        entity_aggregator=GraphHistoryEntityAggregator(
            memory_repository=MemoryRepository(),
            episode_repository=MemoryGraphEpisodeRepository(),
        ),
    )
    memory = Memory(title='OpenAI Funding', title_status='ready', content='OpenAI completed funding', group_id='default')
    db_session.add(memory)
    db_session.commit()
    db_session.add(
        MemoryGraphEpisode(memory_id=memory.id, episode_uuid='openai-funding-v1', version=1, chunk_index=0, is_latest=True)
    )
    db_session.commit()

    result = service.query(
        GraphHistoryQuery(target_type='entity', target_value='OpenAI', mode='compare', question='比较历史')
    )

    assert result.status == 'insufficient_history'
    assert result.resolved_target is not None
    assert result.resolved_target.canonical_name == 'OpenAI'
    assert result.resolved_target.version_count == 1
    assert len(result.timeline) == 1
    assert result.timeline[0].summary_excerpt == 'OpenAI Funding v1'
    assert result.comparisons == []


def test_query_entity_compare_returns_comparison_for_latest_two_events(db_session):
    service = build_service(
        db_session,
        entity_resolver=GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI', 'Open AI']}),
        entity_aggregator=GraphHistoryEntityAggregator(
            memory_repository=MemoryRepository(),
            episode_repository=MemoryGraphEpisodeRepository(),
        ),
    )
    memory_a = Memory(title='OpenAI Funding', title_status='ready', content='OpenAI completed funding', group_id='default')
    memory_b = Memory(title='OpenAI Board', title_status='ready', content='OpenAI board changed', group_id='default')
    db_session.add_all([memory_a, memory_b])
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory_a.id, episode_uuid='openai-funding-v1', version=1, chunk_index=0, is_latest=True),
            MemoryGraphEpisode(memory_id=memory_b.id, episode_uuid='openai-board-v2', version=2, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    result = service.query(
        GraphHistoryQuery(target_type='entity', target_value='Open AI', mode='compare', question='比较历史')
    )

    assert result.status == 'ok'
    assert result.resolved_target is not None
    assert result.resolved_target.canonical_name == 'OpenAI'
    assert result.resolved_target.matched_alias == 'Open AI'
    assert result.resolved_target.version_count == 2
    assert len(result.timeline) == 2
    assert len(result.comparisons) == 1
    assert result.comparisons[0].from_version == 1
    assert result.comparisons[0].to_version == 2
    assert result.comparisons[0].change_summary == '从 v1 演进到 v2'


def test_query_entity_summarize_counts_events_across_more_than_ten_matching_memories(db_session):
    service = build_service(
        db_session,
        entity_resolver=GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI']}),
        entity_aggregator=GraphHistoryEntityAggregator(
            memory_repository=MemoryRepository(),
            episode_repository=MemoryGraphEpisodeRepository(),
        ),
    )
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

    result = service.query(
        GraphHistoryQuery(
            target_type='entity',
            target_value='OpenAI',
            mode='summarize',
            question='总结这个实体的历史',
            constraints={'top_k_events': 1},
        )
    )

    assert result.status == 'ok'
    assert result.resolved_target is not None
    assert result.resolved_target.canonical_name == 'OpenAI'
    assert result.resolved_target.version_count == 11
    assert len(result.timeline) == 1
    assert result.summary == 'OpenAI 共关联 11 条历史事件。'


def test_query_entity_returns_not_found_when_resolver_cannot_match_target(db_session):
    service = build_service(
        db_session,
        entity_resolver=GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI']}),
        entity_aggregator=GraphHistoryEntityAggregator(
            memory_repository=MemoryRepository(),
            episode_repository=MemoryGraphEpisodeRepository(),
        ),
    )

    result = service.query(
        GraphHistoryQuery(target_type='entity', target_value='Anthropic', mode='timeline', question='实体历史？')
    )

    assert result.status == 'not_found'
    assert result.resolved_target is None
    assert result.timeline == []


def test_query_entity_returns_insufficient_evidence_when_no_events_are_found(db_session):
    service = build_service(
        db_session,
        entity_resolver=GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI']}),
        entity_aggregator=GraphHistoryEntityAggregator(
            memory_repository=MemoryRepository(),
            episode_repository=MemoryGraphEpisodeRepository(),
        ),
    )

    result = service.query(
        GraphHistoryQuery(target_type='entity', target_value='OpenAI', mode='timeline', question='实体历史？')
    )

    assert result.status == 'insufficient_evidence'
    assert result.resolved_target is not None
    assert result.resolved_target.canonical_name == 'OpenAI'
    assert result.resolved_target.matched_alias == 'OpenAI'
    assert result.timeline == []


def test_graph_history_service_supports_relation_topic_summarize():
    service = GraphHistoryService(
        db_factory=lambda: object(),
        relation_topic_resolver=type(
            'Resolver',
            (),
            {
                'resolve': lambda self, target_value, constraints=None: type(
                    'Resolved',
                    (),
                    {
                        'status': 'ok',
                        'target_kind': 'relation',
                        'target_value': target_value,
                        'warnings': ['minimal relation mode'],
                    },
                )()
            },
        )(),
    )

    result = service.query(
        GraphHistoryQuery(
            target_type='relation_topic',
            target_value='OpenAI 和微软关系变化',
            mode='summarize',
            constraints={'source_entity': 'OpenAI', 'target_entity': '微软'},
        )
    )

    assert result.status == 'ok'
    assert result.target_type == 'relation_topic'
    assert result.warnings == ['minimal relation mode']


def test_query_returns_not_found_when_memory_does_not_exist(db_session):
    service = build_service(db_session)

    result = service.query(
        GraphHistoryQuery(target_type='memory', target_value='missing-memory', mode='timeline', question='它如何变化？')
    )

    assert result.status == 'not_found'
    assert result.resolved_target is None
    assert result.timeline == []


def test_compare_requires_at_least_two_versions(db_session):
    service = build_service(db_session)
    memory = Memory(title='Single', title_status='ready', content='only body', group_id='default')
    db_session.add(memory)
    db_session.commit()
    db_session.add(MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v1', version=1, chunk_index=0, is_latest=True))
    db_session.commit()

    result = service.query(
        GraphHistoryQuery(target_type='memory', target_value=memory.id, mode='compare', question='最新和上一个有什么不同？')
    )

    assert result.status == 'insufficient_history'
    assert result.comparisons == []
    assert result.warnings == ['该 memory 只有一个版本，无法进行历史比较。']


def test_compare_requires_history_rows_when_memory_has_zero_versions(db_session):
    service = build_service(db_session)
    memory = Memory(title='Empty History', title_status='ready', content='body', group_id='default')
    db_session.add(memory)
    db_session.commit()

    result = service.query(
        GraphHistoryQuery(target_type='memory', target_value=memory.id, mode='compare', question='比较历史')
    )

    assert result.status == 'insufficient_history'
    assert result.timeline == []
    assert result.comparisons == []
    assert result.warnings == ['该 memory 暂无图谱历史版本，无法进行历史比较。']


def test_compare_returns_previous_and_latest_version_comparison(db_session):
    service = build_service(db_session)
    memory = Memory(title='Versioned', title_status='ready', content='v2 body', group_id='default')
    db_session.add(memory)
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v1', version=1, chunk_index=0, is_latest=False),
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v2', version=2, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    result = service.query(
        GraphHistoryQuery(target_type='memory', target_value=memory.id, mode='compare', question='最新和上一个有什么不同？')
    )

    assert result.status == 'ok'
    assert len(result.comparisons) == 1
    assert result.comparisons[0].from_version == 1
    assert result.comparisons[0].to_version == 2
    assert result.comparisons[0].change_summary == '从 v1 演进到 v2'


def test_summarize_returns_expected_summary_and_comparison(db_session):
    service = build_service(db_session)
    memory = Memory(title='Python Note', title_status='ready', content='v3 body', group_id='default')
    db_session.add(memory)
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v1', version=1, chunk_index=0, is_latest=False),
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v2', version=2, chunk_index=0, is_latest=False),
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v3', version=3, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    result = service.query(
        GraphHistoryQuery(target_type='memory', target_value=memory.id, mode='summarize', question='总结一下演进')
    )

    assert result.status == 'ok'
    assert result.summary == 'Python Note 共经历 3 个版本，当前为 v3。'
    assert len(result.comparisons) == 1
    assert result.comparisons[0].from_version == 2
    assert result.comparisons[0].to_version == 3
