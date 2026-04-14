import pytest

from app.workflow.dsl import WorkflowNodeSpec
from app.workflow.nodes.begin_node import BeginNode
from app.workflow.runtime_context import RuntimeContext


@pytest.mark.anyio
async def test_begin_node_exposes_runtime_inputs():
    node = BeginNode(WorkflowNodeSpec(id='begin', type='begin'))
    context = RuntimeContext(query='hello', history=[{'role': 'user', 'content': 'hi'}], files=['f1'], user_id='u1')

    result = await node.execute(context, canvas=None)

    assert result == {
        'query': 'hello',
        'history': [{'role': 'user', 'content': 'hi'}],
        'files': ['f1'],
        'user_id': 'u1',
    }
    assert context.get_global('workflow.begin')['query'] == 'hello'
