from app.schemas.agent import GraphHistoryQuery, GraphHistoryResolvedTarget, GraphHistoryResult
from app.services.agent_tools import GraphHistoryTool
from app.workflow.dsl import WorkflowNodeSpec
from app.workflow.nodes.agent_node import AgentNode


def test_graph_history_query_and_result_defaults():
    query = GraphHistoryQuery(target_type='memory', target_value='memory-1', mode='timeline', question='它怎么变过？')
    result = GraphHistoryResult(target_type='memory', target_value='memory-1', mode='timeline', status='ok')

    assert query.constraints == {}
    assert result.timeline == []
    assert result.comparisons == []
    assert result.summary == ''
    assert result.evidence == []
    assert result.warnings == []


def test_graph_history_tool_delegates_to_service():
    captured = {}

    class StubService:
        def query(self, payload):
            captured['payload'] = payload
            return GraphHistoryResult(
                target_type='memory',
                target_value='memory-1',
                mode='timeline',
                status='ok',
            )

    tool = GraphHistoryTool(history_service=StubService())
    result = tool.run(target_type='memory', target_value='memory-1', mode='timeline', question='它怎么变过？')

    assert isinstance(captured['payload'], GraphHistoryQuery)
    assert captured['payload'].target_type == 'memory'
    assert captured['payload'].target_value == 'memory-1'
    assert captured['payload'].mode == 'timeline'
    assert captured['payload'].question == '它怎么变过？'
    assert captured['payload'].constraints == {}
    assert result.status == 'ok'


def test_graph_history_schema_supports_entity_and_relation_topic_fields():
    query = GraphHistoryQuery(
        target_type='relation_topic',
        target_value='合作关系',
        mode='summarize',
        constraints={'source_entity': 'OpenAI'},
    )
    resolved = GraphHistoryResolvedTarget(
        canonical_name='OpenAI',
        matched_alias='openai',
        candidate_count=1,
        entity_id='entity-openai',
    )
    result = GraphHistoryResult(
        target_type='entity',
        target_value='OpenAI',
        mode='timeline',
        status='ambiguous_target',
        resolved_target=resolved,
        warnings=['need disambiguation'],
    )

    assert query.target_type == 'relation_topic'
    assert result.status == 'ambiguous_target'
    assert result.resolved_target.entity_id == 'entity-openai'


def test_graph_history_tool_passes_entity_constraints_to_service():
    captured = {}

    class StubService:
        def query(self, payload):
            captured['payload'] = payload
            return GraphHistoryResult(
                target_type='entity',
                target_value='OpenAI',
                mode='timeline',
                status='ok',
            )

    tool = GraphHistoryTool(history_service=StubService())
    tool.run(
        target_type='entity',
        target_value='OpenAI',
        mode='timeline',
        constraints={'entity_match_mode': 'alias'},
    )

    assert captured['payload'].constraints['entity_match_mode'] == 'alias'


def test_graph_history_tool_description_mentions_entity_history():
    assert 'entity' in GraphHistoryTool.description


def test_agent_node_graph_history_tool_schema_includes_entity_target_type():
    node = AgentNode(WorkflowNodeSpec(id='agent', type='agent'))

    schema = node._graph_history_tool_schema()

    assert schema['function']['name'] == 'graph_history_tool'
    assert schema['function']['parameters']['properties']['target_type']['enum'] == [
        'memory',
        'entity',
        'relation_topic',
    ]
