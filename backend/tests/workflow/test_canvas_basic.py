import pytest

from app.workflow.canvas import Canvas


class BeginNode:
    def __init__(self, spec):
        self.spec = spec

    async def execute(self, context, canvas):
        context.set_global('workflow.begin_ran', True)
        return {'message': 'begin'}


class EndNode:
    def __init__(self, spec):
        self.spec = spec

    def execute(self, context, canvas):
        assert context.get_global('workflow.begin_ran') is True
        canvas.reference_store.merge(chunks=[{'id': 'chunk-1', 'text': 'hello'}])
        return {'message': 'end'}


@pytest.mark.anyio
async def test_canvas_runs_registered_nodes_in_order():
    dsl = {
        'entry_node_id': 'begin',
        'nodes': [
            {'id': 'begin', 'type': 'begin', 'downstream': ['end']},
            {'id': 'end', 'type': 'end', 'downstream': []},
        ],
    }
    canvas = Canvas(dsl)
    canvas.register_node_type('begin', BeginNode)
    canvas.register_node_type('end', EndNode)

    events = [event async for event in canvas.run()]

    assert [event.event for event in events] == [
        'workflow_started',
        'node_started',
        'node_finished',
        'node_started',
        'node_finished',
        'workflow_finished',
    ]
    assert canvas.execution_path == ['begin', 'end']
    assert canvas.context.get_node_output('begin') == {'message': 'begin'}
    assert canvas.context.get_node_output('end') == {'message': 'end'}
    assert canvas.reference_store.snapshot()['chunks'] == [{'id': 'chunk-1', 'text': 'hello'}]


def test_canvas_requires_registered_node_type():
    dsl = {
        'entry_node_id': 'begin',
        'nodes': [{'id': 'begin', 'type': 'begin', 'downstream': []}],
    }
    canvas = Canvas(dsl)

    with pytest.raises(KeyError, match='Node type "begin" is not registered'):
        canvas._instantiate_node('begin')
