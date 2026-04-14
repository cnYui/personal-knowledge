from app.services.graph_history_relation_topic_resolver import GraphHistoryRelationTopicResolver


def test_relation_topic_resolver_extracts_relation_target():
    resolver = GraphHistoryRelationTopicResolver()

    result = resolver.resolve(
        target_value='OpenAI 和 Microsoft 的关系如何变化',
        constraints={'source_entity': 'OpenAI', 'target_entity': 'Microsoft', 'relation_type': 'partnership'},
    )

    assert result.target_kind == 'relation'
    assert result.source_entity == 'OpenAI'
    assert result.target_entity == 'Microsoft'
    assert result.relation_type == 'partnership'


def test_relation_topic_resolver_extracts_topic_target():
    resolver = GraphHistoryRelationTopicResolver()

    result = resolver.resolve(
        target_value='AI safety 主题如何演化',
        constraints={'topic_scope': 'AI safety'},
    )

    assert result.target_kind == 'topic'
    assert result.topic_scope == 'AI safety'
