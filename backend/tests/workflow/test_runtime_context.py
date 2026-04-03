from app.workflow.runtime_context import RuntimeContext


def test_runtime_context_initializes_sys_globals():
    context = RuntimeContext(query='hello', user_id='u-1', files=['a.txt'])

    assert context.get_global('sys.query') == 'hello'
    assert context.get_global('sys.user_id') == 'u-1'
    assert context.get_global('sys.files') == ['a.txt']
    assert context.get_global('sys.history') == []
    assert context.get_global('sys.date')


def test_runtime_context_tracks_history_and_node_outputs():
    context = RuntimeContext()

    context.append_history('user', '你好')
    context.set_node_output('begin', {'ok': True})

    assert context.history == [{'role': 'user', 'content': '你好'}]
    assert context.get_node_output('begin') == {'ok': True}
    snapshot = context.snapshot()
    assert snapshot['history'][0]['content'] == '你好'
    assert snapshot['node_outputs']['begin'] == {'ok': True}
