import pytest

from app.workflow.canvas import Canvas
from app.workflow.dsl import WorkflowDSL, WorkflowNodeSpec
from app.workflow.nodes.message_node import MessageNode
from app.workflow.runtime_context import RuntimeContext


@pytest.mark.asyncio
async def test_message_node_reads_answer_from_node_output():
    spec = WorkflowNodeSpec(
        id='message',
        type='message',
        config={'source_ref': 'node:agent'},
    )
    context = RuntimeContext()
    context.set_node_output(
        'agent',
        {
            'answer': '这是最终答案。',
            'references': [{'type': 'relationship', 'fact': 'Alice likes green tea'}],
        },
    )
    canvas = Canvas(WorkflowDSL(entry_node_id='message', nodes=[spec]), context=context)

    result = await MessageNode(spec).execute(context, canvas)

    assert result == {
        'content': '这是最终答案。',
        'references': [{'type': 'relationship', 'fact': 'Alice likes green tea'}],
    }
    assert context.get_global('workflow.message')['content'] == '这是最终答案。'
