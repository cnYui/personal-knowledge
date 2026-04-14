import pytest
from unittest.mock import AsyncMock

from app.schemas.agent import GraphRetrievalResult
from app.schemas.chat import ChatReference
from app.workflow.canvas import Canvas
from app.workflow.dsl import WorkflowDSL, WorkflowNodeSpec
from app.workflow.engine.tool_loop import ToolLoopEngine
from app.workflow.nodes.agent_node import AgentNode
from app.workflow.runtime_context import RuntimeContext


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


@pytest.mark.anyio
async def test_agent_node_can_answer_greeting_without_retrieval():
    class FailingGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            raise AssertionError('graph retrieval should not be called for direct greeting answer')

    client = FakeLLMClient([FakeResponse(FakeMessage(content='你好！今天有什么我可以帮你的吗？'))])
    spec = WorkflowNodeSpec(id='agent', type='agent')
    node = AgentNode(
        spec,
        graph_retrieval_tool=FailingGraphRetrievalTool(),
        llm_client=client,
        knowledge_profile_service=type('ProfileService', (), {'compose_system_prompt': staticmethod(lambda base: f'{base}\n\n[overlay]')})(),
    )
    node._extract_focus_points = AsyncMock(return_value='你好')
    context = RuntimeContext(query='你好')
    canvas = Canvas(WorkflowDSL(entry_node_id='agent', nodes=[spec]), context=context)

    result = await node.execute(context, canvas)

    assert result['answer'] == '你好！今天有什么我可以帮你的吗？'
    assert result['references'] == []
    assert result['agent_trace'].retrieval_rounds == 0
    assert result['agent_trace'].final_action == 'direct_general_answer'
    assert result['agent_trace'].steps[0].step_type == 'answer'
    assert result['agent_trace'].steps[0].action == 'answer_directly'
    first_call = client.chat.completions.calls[0]
    assert first_call['messages'][0]['role'] == 'system'
    assert '[overlay]' in first_call['messages'][0]['content']


@pytest.mark.anyio
async def test_agent_node_uses_tool_loop_and_reference_store_for_grounded_answer():
    references = [ChatReference(type='relationship', fact='Alice likes green tea')]
    retrieval_result = GraphRetrievalResult(
        context='关系: Alice likes green tea',
        references=references,
        has_enough_evidence=True,
        retrieved_edge_count=1,
        group_id='team-a',
    )
    call_log = []

    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            call_log.append((query, group_id))
            return retrieval_result

    client = FakeLLMClient(
        [
            FakeResponse(
                FakeMessage(
                    tool_calls=[
                        FakeToolCall('tool-1', 'graph_retrieval_tool', '{"query":"Alice 喜欢什么？"}')
                    ]
                )
            ),
            FakeResponse(FakeMessage(content='Alice 喜欢绿茶。')),
        ]
    )
    engine = ToolLoopEngine(client, max_rounds=2)
    spec = WorkflowNodeSpec(id='agent', type='agent', config={'group_id': 'team-a'})
    node = AgentNode(
        spec,
        graph_retrieval_tool=StubGraphRetrievalTool(),
        tool_loop_engine=engine,
    )
    node._extract_focus_points = AsyncMock(return_value='Alice / 喜欢 / 绿茶')
    context = RuntimeContext(query='Alice 喜欢什么？')
    canvas = Canvas(WorkflowDSL(entry_node_id='agent', nodes=[spec]), context=context)

    result = await node.execute(context, canvas)

    assert result['answer'] == 'Alice 喜欢绿茶。'
    assert result['references'] == references
    assert result['agent_trace'].retrieval_rounds == 1
    assert result['agent_trace'].final_action == 'kb_grounded_answer'
    assert call_log == [('Alice 喜欢什么？', 'team-a')]
    snapshot = canvas.reference_store.snapshot()
    assert snapshot['graph_evidence'] == [
        {'type': 'relationship', 'name': None, 'summary': None, 'fact': 'Alice likes green tea'}
    ]


@pytest.mark.anyio
async def test_agent_node_prefixes_general_fallback_when_evidence_is_insufficient():
    references = [ChatReference(type='entity', name='Alice', summary='用户的朋友')]
    retrieval_result = GraphRetrievalResult(
        context='',
        references=references,
        has_enough_evidence=False,
        empty_reason='图谱中没有足够信息',
        retrieved_edge_count=0,
    )

    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            return retrieval_result

    client = FakeLLMClient(
        [
            FakeResponse(
                FakeMessage(
                    tool_calls=[
                        FakeToolCall('tool-1', 'graph_retrieval_tool', '{"query":"Alice 最近怎么样？"}')
                    ]
                )
            ),
            FakeResponse(FakeMessage(content='从通用知识来看，Alice 的近况需要更多上下文才能准确判断。')),
        ]
    )
    engine = ToolLoopEngine(client, max_rounds=2)
    spec = WorkflowNodeSpec(id='agent', type='agent')
    node = AgentNode(
        spec,
        graph_retrieval_tool=StubGraphRetrievalTool(),
        tool_loop_engine=engine,
    )
    node._extract_focus_points = AsyncMock(return_value='Alice / 近况')
    context = RuntimeContext(query='Alice 最近怎么样？')
    canvas = Canvas(WorkflowDSL(entry_node_id='agent', nodes=[spec]), context=context)

    result = await node.execute(context, canvas)

    assert result['answer'].startswith('知识库中未找到充分证据，以下内容为通用模型补充回答。')
    assert 'Alice 的近况需要更多上下文' in result['answer']
    assert result['references'] == references
    assert result['agent_trace'].final_action == 'kb_plus_general_answer'
    assert result['agent_trace'].steps[-1].step_type == 'fallback'


@pytest.mark.anyio
async def test_agent_node_can_call_retrieval_tool_multiple_rounds():
    query_to_result = {
        '星期一收集什么垃圾？': GraphRetrievalResult(
            context='关系: 星期一收集不可燃垃圾',
            references=[ChatReference(type='relationship', fact='星期一收集不可燃垃圾')],
            has_enough_evidence=True,
            retrieved_edge_count=1,
        ),
        '星期五收集什么垃圾？': GraphRetrievalResult(
            context='关系: 星期五收集可燃垃圾',
            references=[ChatReference(type='relationship', fact='星期五收集可燃垃圾')],
            has_enough_evidence=True,
            retrieved_edge_count=1,
        ),
    }
    retrieval_calls = []

    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            retrieval_calls.append((query, group_id))
            return query_to_result[query]

    client = FakeLLMClient(
        [
            FakeResponse(
                FakeMessage(
                    tool_calls=[
                        FakeToolCall('tool-1', 'graph_retrieval_tool', '{"query":"星期一收集什么垃圾？"}')
                    ]
                )
            ),
            FakeResponse(
                FakeMessage(
                    tool_calls=[
                        FakeToolCall('tool-2', 'graph_retrieval_tool', '{"query":"星期五收集什么垃圾？"}')
                    ]
                )
            ),
            FakeResponse(FakeMessage(content='星期一收集不可燃垃圾，星期五收集可燃垃圾。')),
        ]
    )
    engine = ToolLoopEngine(client, max_rounds=3)
    spec = WorkflowNodeSpec(id='agent', type='agent')
    node = AgentNode(
        spec,
        graph_retrieval_tool=StubGraphRetrievalTool(),
        tool_loop_engine=engine,
    )
    node._extract_focus_points = AsyncMock(return_value='星期一 / 星期五 / 垃圾收集')
    context = RuntimeContext(query='星期一和星期五分别收集什么垃圾？')
    canvas = Canvas(WorkflowDSL(entry_node_id='agent', nodes=[spec]), context=context)

    result = await node.execute(context, canvas)

    assert result['answer'] == '星期一收集不可燃垃圾，星期五收集可燃垃圾。'
    assert len(result['references']) == 2
    assert result['agent_trace'].retrieval_rounds == 2
    assert result['agent_trace'].final_action == 'kb_grounded_answer'
    assert retrieval_calls == [
        ('星期一收集什么垃圾？', 'default'),
        ('星期五收集什么垃圾？', 'default'),
    ]


@pytest.mark.anyio
async def test_agent_node_can_still_ground_answer_after_max_rounds_with_evidence():
    references = [ChatReference(type='relationship', fact='向量空间是线性代数中的基本结构')]
    retrieval_result = GraphRetrievalResult(
        context='关系: 向量空间是线性代数中的基本结构',
        references=references,
        has_enough_evidence=True,
        retrieved_edge_count=1,
    )
    call_log = []

    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            call_log.append(('retrieve', query, group_id))
            return retrieval_result

    class StubKnowledgeGraphService:
        async def answer_with_context(self, query: str, provided_result: GraphRetrievalResult):
            call_log.append(('answer', query, provided_result))
            return {'answer': '根据知识图谱，向量空间是定义了加法和数乘运算的集合。', 'references': provided_result.references}

    client = FakeLLMClient(
        [
            FakeResponse(
                FakeMessage(
                    tool_calls=[
                        FakeToolCall('tool-1', 'graph_retrieval_tool', '{"query":"什么是向量空间？"}')
                    ]
                )
            ),
            FakeResponse(
                FakeMessage(
                    tool_calls=[
                        FakeToolCall('tool-2', 'graph_retrieval_tool', '{"query":"向量空间的定义"}')
                    ]
                )
            ),
        ]
    )
    engine = ToolLoopEngine(client, max_rounds=1)
    spec = WorkflowNodeSpec(id='agent', type='agent')
    node = AgentNode(
        spec,
        graph_retrieval_tool=StubGraphRetrievalTool(),
        knowledge_graph_service=StubKnowledgeGraphService(),
        tool_loop_engine=engine,
    )
    node._extract_focus_points = AsyncMock(return_value='向量空间 / 定义')
    context = RuntimeContext(query='什么是向量空间？')
    canvas = Canvas(WorkflowDSL(entry_node_id='agent', nodes=[spec]), context=context)

    result = await node.execute(context, canvas)

    assert result['answer'] == '根据知识图谱，向量空间是定义了加法和数乘运算的集合。'
    assert result['references'] == references
    assert result['agent_trace'].final_action == 'kb_grounded_answer'
    assert result['agent_trace'].retrieval_rounds == 1
    assert call_log == [
        ('retrieve', '什么是向量空间？', 'default'),
        ('answer', '什么是向量空间？', retrieval_result),
    ]
