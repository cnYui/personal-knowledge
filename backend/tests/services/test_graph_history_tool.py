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


def test_graph_history_query_supports_entity_constraints():
    query = GraphHistoryQuery(
        target_type='entity',
        target_value='OpenAI',
        mode='timeline',
        constraints={
            'entity_match_mode': 'alias',
            'top_k_events': 5,
            'include_related_memories': True,
            'disambiguation_policy': 'fail',
            'time_range': {'start': '2024-01-01', 'end': '2024-12-31'},
        },
    )

    assert query.target_type == 'entity'
    assert query.constraints['entity_match_mode'] == 'alias'
    assert query.constraints['top_k_events'] == 5
    assert query.constraints['include_related_memories'] is True


def test_graph_history_result_supports_entity_resolved_target_and_new_statuses():
    result = GraphHistoryResult(
        target_type='entity',
        target_value='Apple',
        mode='timeline',
        status='ambiguous_target',
        resolved_target=GraphHistoryResolvedTarget(
            entity_id='entity-apple',
            canonical_name=None,
            matched_alias=None,
            candidate_count=2,
        ),
    )

    assert result.status == 'ambiguous_target'
    assert result.resolved_target is not None
    assert result.resolved_target.entity_id == 'entity-apple'
    assert result.resolved_target.candidate_count == 2


def test_graph_history_result_supports_insufficient_evidence_status():
    result = GraphHistoryResult(
        target_type='entity',
        target_value='OpenAI',
        mode='summarize',
        status='insufficient_evidence',
    )

    assert result.status == 'insufficient_evidence'


def test_graph_history_tool_passes_entity_constraints_to_service():
    captured = {}

    class StubService:
        def query(self, payload):
            captured['payload'] = payload
            return GraphHistoryResult(target_type='entity', target_value='OpenAI', mode='timeline', status='ok')

    tool = GraphHistoryTool(history_service=StubService())
    tool.run(
        target_type='entity',
        target_value='OpenAI',
        mode='timeline',
        constraints={'entity_match_mode': 'alias', 'top_k_events': 5},
    )

    assert captured['payload'].constraints['entity_match_mode'] == 'alias'
    assert captured['payload'].constraints['top_k_events'] == 5


def test_graph_history_tool_description_mentions_entity_history():
    assert 'entity' in GraphHistoryTool.description


def test_agent_node_graph_history_tool_schema_includes_entity_target_type():
    node = AgentNode(spec=WorkflowNodeSpec(id='agent-1', type='agent', config={}))

    schema = node._graph_history_tool_schema()

    assert schema['function']['name'] == 'graph_history_tool'
    assert schema['function']['parameters']['properties']['target_type']['enum'] == ['memory', 'entity', 'relation_topic']