import pytest

from app.workflow.engine.tool_loop import ToolLoopEngine


class FakeToolCall:
    def __init__(self, tool_id: str, name: str, arguments: str) -> None:
        self.id = tool_id
        self.function = type('Function', (), {'name': name, 'arguments': arguments})()


class FakeMessage:
    def __init__(self, content: str = '', tool_calls=None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []


class FakeResponse:
    def __init__(self, message: FakeMessage) -> None:
        self.choices = [type('Choice', (), {'message': message})()]


class FakeCompletions:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses[len(self.calls) - 1]


class FakeLLMClient:
    def __init__(self, responses):
        self.chat = type(
            'Chat',
            (),
            {'completions': FakeCompletions(responses)},
        )()


@pytest.mark.asyncio
async def test_tool_loop_returns_direct_answer_without_tool_call():
    client = FakeLLMClient([FakeResponse(FakeMessage(content='直接答案'))])
    engine = ToolLoopEngine(client, max_rounds=2)

    result = await engine.run(
        messages=[{'role': 'user', 'content': '你好'}],
        tool_schemas=[],
        tool_registry={},
    )

    assert result.answer == '直接答案'
    assert result.steps == []
    assert result.exceeded_max_rounds is False


@pytest.mark.asyncio
async def test_tool_loop_executes_tool_then_returns_answer():
    client = FakeLLMClient(
        [
            FakeResponse(
                FakeMessage(
                    tool_calls=[FakeToolCall('tool-1', 'graph_retrieval_tool', '{"query":"Alice 喜欢什么？"}')]
                )
            ),
            FakeResponse(FakeMessage(content='Alice 喜欢绿茶。')),
        ]
    )
    engine = ToolLoopEngine(client, max_rounds=2)

    async def fake_tool(query: str):
        return {'context': '关系: Alice likes green tea'}

    result = await engine.run(
        messages=[{'role': 'user', 'content': 'Alice 喜欢什么？'}],
        tool_schemas=[{'type': 'function', 'function': {'name': 'graph_retrieval_tool'}}],
        tool_registry={'graph_retrieval_tool': fake_tool},
    )

    assert result.answer == 'Alice 喜欢绿茶。'
    assert len(result.steps) == 1
    assert result.steps[0].tool_name == 'graph_retrieval_tool'
    assert result.steps[0].arguments == {'query': 'Alice 喜欢什么？'}
    assert result.steps[0].result == {'context': '关系: Alice likes green tea'}
    assert result.exceeded_max_rounds is False


@pytest.mark.asyncio
async def test_tool_loop_marks_exceeded_max_rounds():
    client = FakeLLMClient(
        [
            FakeResponse(
                FakeMessage(
                    tool_calls=[FakeToolCall('tool-1', 'graph_retrieval_tool', '{"query":"q1"}')]
                )
            ),
            FakeResponse(
                FakeMessage(
                    tool_calls=[FakeToolCall('tool-2', 'graph_retrieval_tool', '{"query":"q2"}')]
                )
            ),
        ]
    )
    engine = ToolLoopEngine(client, max_rounds=1)

    async def fake_tool(query: str):
        return {'query': query}

    result = await engine.run(
        messages=[{'role': 'user', 'content': '测试'}],
        tool_schemas=[{'type': 'function', 'function': {'name': 'graph_retrieval_tool'}}],
        tool_registry={'graph_retrieval_tool': fake_tool},
    )

    assert result.exceeded_max_rounds is True
    assert result.answer == ''
    assert len(result.steps) == 1
