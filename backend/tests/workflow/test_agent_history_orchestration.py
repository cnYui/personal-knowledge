from app.schemas.agent import GraphHistoryResult
from app.services.agent_tools import GraphHistoryTool
from app.workflow.dsl import WorkflowNodeSpec
from app.workflow.nodes.agent_node import AgentNode


def build_agent_node_for_test() -> AgentNode:
    return AgentNode(WorkflowNodeSpec(id='agent', type='agent'))


def test_agent_node_graph_history_tool_schema_includes_entity_target_type():
    node = build_agent_node_for_test()

    schemas = node._tool_schemas()
    history_schema = next(item for item in schemas if item['function']['name'] == 'graph_history_tool')

    assert history_schema['function']['parameters']['properties']['target_type']['enum'] == [
        'memory',
        'entity',
        'relation_topic',
    ]


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