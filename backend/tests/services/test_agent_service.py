import json

import pytest

import app.services.agent_service as agent_service_module
from app.schemas.agent import GraphRetrievalResult
from app.schemas.chat import ChatReference
from app.services.agent_service import AgentService
from app.services.chat_service import ChatService


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_agent_service_chitchat_skips_graph_retrieval():
    class FailingGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            raise AssertionError('graph retrieval should not be called for chitchat')

    class FailingKnowledgeGraphService:
        async def answer_with_context(self, query: str, retrieval_result: GraphRetrievalResult):
            raise AssertionError('answer_with_context should not be called for chitchat')

    service = AgentService(
        graph_retrieval_tool=FailingGraphRetrievalTool(),
        knowledge_graph_service=FailingKnowledgeGraphService(),
    )

    result = await service.ask('你好呀')

    assert result['references'] == []
    assert '个人知识库助手' in result['answer']
    assert result['agent_trace'].mode == 'chitchat'
    assert result['agent_trace'].final_action == 'chitchat_answer'


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_agent_service_chitchat_with_custom_tool_does_not_require_kg_initialization(
    monkeypatch,
):
    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            raise AssertionError('graph retrieval should not be called for chitchat')

    class FailingKnowledgeGraphService:
        def __init__(self) -> None:
            raise AssertionError('KnowledgeGraphService should not initialize for chitchat')

    monkeypatch.setattr(
        agent_service_module,
        'KnowledgeGraphService',
        FailingKnowledgeGraphService,
    )

    service = AgentService(graph_retrieval_tool=StubGraphRetrievalTool())

    result = await service.ask('你好呀')

    assert result['references'] == []
    assert '个人知识库助手' in result['answer']


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_agent_service_knowledge_path_uses_graph_tool_then_answer_with_context():
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
            call_log.append(('retrieve', query, group_id))
            return retrieval_result

    class StubKnowledgeGraphService:
        async def answer_with_context(self, query: str, provided_result: GraphRetrievalResult):
            call_log.append(('answer', query, provided_result))
            return {'answer': 'Alice 喜欢绿茶。', 'references': provided_result.references}

    service = AgentService(
        graph_retrieval_tool=StubGraphRetrievalTool(),
        knowledge_graph_service=StubKnowledgeGraphService(),
    )

    result = await service.ask('Alice 喜欢什么？', group_id='team-a')

    assert result['answer'] == 'Alice 喜欢绿茶。'
    assert result['references'] == references
    assert result['agent_trace'].mode == 'graph_rag'
    assert result['agent_trace'].retrieval_rounds == 1
    assert call_log == [
        ('retrieve', 'Alice 喜欢什么？', 'team-a'),
        ('answer', 'Alice 喜欢什么？', retrieval_result),
    ]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_agent_service_empty_evidence_returns_controlled_answer_and_references():
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

    class StubKnowledgeGraphService:
        async def answer_with_context(self, query: str, provided_result: GraphRetrievalResult):
            assert provided_result.has_enough_evidence is False
            return {
                'answer': '抱歉，我在知识图谱中没有找到足够相关的信息。',
                'references': provided_result.references,
            }

    service = AgentService(
        graph_retrieval_tool=StubGraphRetrievalTool(),
        knowledge_graph_service=StubKnowledgeGraphService(),
    )

    result = await service.ask('Alice 最近怎么样？')

    assert result['answer'] == '抱歉，我在知识图谱中没有找到足够相关的信息。'
    assert result['references'] == references
    assert result['agent_trace'].final_action == 'answer'


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_agent_service_rewrites_query_and_retries_after_empty_retrieval():
    rewritten_result = GraphRetrievalResult(
        context='关系: Monday collects non-burnable trash',
        references=[ChatReference(type='relationship', fact='星期一收集不可燃垃圾')],
        has_enough_evidence=True,
        retrieved_edge_count=1,
        group_id='default',
    )
    call_log = []

    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            call_log.append(('retrieve', query, group_id))
            if query == '星期一收集什么垃圾？':
                return GraphRetrievalResult(
                    context='',
                    references=[],
                    has_enough_evidence=False,
                    empty_reason='图谱中没有足够信息',
                    retrieved_edge_count=0,
                    group_id=group_id,
                )
            if query == '星期一收集哪一类垃圾':
                return rewritten_result
            raise AssertionError(f'unexpected query: {query}')

    class StubKnowledgeGraphService:
        def __init__(self) -> None:
            async def fake_create(*args, **kwargs):
                call_log.append(('planner', kwargs['messages'][1]['content']))
                return type(
                    'Response',
                    (),
                    {
                        'choices': [
                            type(
                                'Choice',
                                (),
                                {
                                    'message': type(
                                        'Message',
                                        (),
                                        {
                                            'content': '{"action":"rewrite","rewritten_query":"星期一收集哪一类垃圾","reason":"将口语化问题改写为更适合图谱检索的表达。"}'
                                        },
                                    )()
                                },
                            )()
                        ]
                    },
                )()

            self.llm_client = type(
                'Client',
                (),
                {
                    'chat': type(
                        'Chat',
                        (),
                        {
                            'completions': type(
                                'Completions',
                                (),
                                {'create': fake_create},
                            )()
                        },
                    )()
                },
            )()

        async def answer_with_context(self, query: str, provided_result: GraphRetrievalResult):
            call_log.append(('answer', query, provided_result))
            return {
                'answer': '根据给定的上下文，星期一收集不可燃垃圾。',
                'references': provided_result.references,
            }

    service = AgentService(
        graph_retrieval_tool=StubGraphRetrievalTool(),
        knowledge_graph_service=StubKnowledgeGraphService(),
        max_retrieval_rounds=2,
    )

    result = await service.ask('星期一收集什么垃圾？')

    assert result['answer'] == '根据给定的上下文，星期一收集不可燃垃圾。'
    assert result['references'] == rewritten_result.references
    assert result['agent_trace'].retrieval_rounds == 2
    assert result['agent_trace'].steps[1].step_type == 'planner'
    assert result['agent_trace'].steps[1].action == 'rewrite'
    assert call_log == [
        ('retrieve', '星期一收集什么垃圾？', 'default'),
        (
            'planner',
            '原始用户问题：星期一收集什么垃圾？\n本轮检索问题：星期一收集什么垃圾？\n当前轮次：1\n命中边数量：0\n是否有足够证据：False\n空结果原因：图谱中没有足够信息\n请判断是否值得改写问题后再检索一次。',
        ),
        ('retrieve', '星期一收集哪一类垃圾', 'default'),
        ('answer', '星期一收集什么垃圾？', rewritten_result),
    ]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_agent_service_stops_retry_when_planner_gives_up():
    call_log = []
    empty_result = GraphRetrievalResult(
        context='',
        references=[],
        has_enough_evidence=False,
        empty_reason='图谱中没有足够信息',
        retrieved_edge_count=0,
        group_id='default',
    )

    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            call_log.append(('retrieve', query, group_id))
            return empty_result

    class StubKnowledgeGraphService:
        def __init__(self) -> None:
            async def fake_create(*args, **kwargs):
                call_log.append(('planner', kwargs['messages'][1]['content']))
                return type(
                    'Response',
                    (),
                    {
                        'choices': [
                            type(
                                'Choice',
                                (),
                                {
                                    'message': type(
                                        'Message',
                                        (),
                                        {
                                            'content': '{"action":"give_up","rewritten_query":"","reason":"这个问题已经足够清楚，继续改写意义不大。"}'
                                        },
                                    )()
                                },
                            )()
                        ]
                    },
                )()

            self.llm_client = type(
                'Client',
                (),
                {
                    'chat': type(
                        'Chat',
                        (),
                        {
                            'completions': type(
                                'Completions',
                                (),
                                {'create': fake_create},
                            )()
                        },
                    )()
                },
            )()

        async def answer_with_context(self, query: str, provided_result: GraphRetrievalResult):
            call_log.append(('answer', query, provided_result))
            return {
                'answer': '抱歉，我在知识图谱中没有找到足够相关的信息。',
                'references': provided_result.references,
            }

    service = AgentService(
        graph_retrieval_tool=StubGraphRetrievalTool(),
        knowledge_graph_service=StubKnowledgeGraphService(),
        max_retrieval_rounds=2,
    )

    result = await service.ask('Alice 最近怎么样？')

    assert result['answer'] == '抱歉，我在知识图谱中没有找到足够相关的信息。'
    assert result['references'] == []
    assert result['agent_trace'].retrieval_rounds == 1
    assert result['agent_trace'].steps[1].action == 'give_up'
    assert call_log == [
        ('retrieve', 'Alice 最近怎么样？', 'default'),
        (
            'planner',
            '原始用户问题：Alice 最近怎么样？\n本轮检索问题：Alice 最近怎么样？\n当前轮次：1\n命中边数量：0\n是否有足够证据：False\n空结果原因：图谱中没有足够信息\n请判断是否值得改写问题后再检索一次。',
        ),
        ('answer', 'Alice 最近怎么样？', empty_result),
    ]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_agent_service_stream_uses_knowledge_graph_stream_helper_and_keeps_references_first():
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
            call_log.append(('retrieve', query, group_id))
            return retrieval_result

    class StubKnowledgeGraphService:
        async def answer_with_context(self, query: str, provided_result: GraphRetrievalResult):
            raise AssertionError('answer_with_context should not be used for non-chitchat streaming')

        async def answer_with_context_stream(self, query: str, provided_result: GraphRetrievalResult):
            call_log.append(('stream', query, provided_result))
            yield {'type': 'content', 'content': 'Alice '}
            yield {'type': 'content', 'content': '喜欢绿茶。'}
            yield {'type': 'done', 'content': ''}

    service = AgentService(
        graph_retrieval_tool=StubGraphRetrievalTool(),
        knowledge_graph_service=StubKnowledgeGraphService(),
    )

    chunks = [chunk async for chunk in service.ask_stream('Alice 喜欢什么？', group_id='team-a')]

    assert call_log == [
        ('retrieve', 'Alice 喜欢什么？', 'team-a'),
        ('stream', 'Alice 喜欢什么？', retrieval_result),
    ]
    assert chunks[0]['type'] == 'trace'
    assert chunks[0]['content']['mode'] == 'graph_rag'
    assert chunks[1:] == [
        {'type': 'references', 'content': [reference.model_dump() for reference in references]},
        {'type': 'content', 'content': 'Alice '},
        {'type': 'content', 'content': '喜欢绿茶。'},
        {'type': 'done', 'content': ''},
    ]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_chat_service_send_message_uses_agent_service_and_preserves_repository_writes():
    references = [ChatReference(type='relationship', fact='Alice likes green tea')]

    class StubRepository:
        def __init__(self) -> None:
            self.create_calls = []

        def create(self, db, role: str, content: str):
            self.create_calls.append((db, role, content))
            return None

    class StubAgentService:
        def __init__(self) -> None:
            self.ask_calls = []

        async def ask(self, query: str, group_id: str = 'default'):
            self.ask_calls.append((query, group_id))
            return {'answer': '这是代理回答。', 'references': references, 'agent_trace': None}

    repository = StubRepository()
    agent_service = StubAgentService()
    service = ChatService(repository=repository, agent_service=agent_service)
    db = object()

    result = await service.send_message(db, '什么是向量空间？')

    assert result.answer == '这是代理回答。'
    assert result.references == references
    assert result.agent_trace is None
    assert agent_service.ask_calls == [('什么是向量空间？', 'default')]
    assert repository.create_calls == [
        (db, 'user', '什么是向量空间？'),
        (db, 'assistant', '这是代理回答。'),
    ]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_chat_service_rag_query_uses_agent_service_without_repository_writes():
    references = [ChatReference(type='entity', name='Alice', summary='喜欢喝茶')]

    class StubRepository:
        def __init__(self) -> None:
            self.create_calls = []

        def create(self, db, role: str, content: str):
            self.create_calls.append((db, role, content))
            return None

    class StubAgentService:
        def __init__(self) -> None:
            self.ask_calls = []

        async def ask(self, query: str, group_id: str = 'default'):
            self.ask_calls.append((query, group_id))
            return {'answer': 'Alice 很喜欢喝茶。', 'references': references, 'agent_trace': None}

    repository = StubRepository()
    agent_service = StubAgentService()
    service = ChatService(repository=repository, agent_service=agent_service)

    result = await service.rag_query('Alice 喜欢什么？')

    assert result.answer == 'Alice 很喜欢喝茶。'
    assert result.references == references
    assert result.agent_trace is None
    assert agent_service.ask_calls == [('Alice 喜欢什么？', 'default')]
    assert repository.create_calls == []


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_chat_service_rag_stream_uses_agent_service_stream():
    class StubAgentService:
        def __init__(self) -> None:
            self.ask_stream_calls = []

        async def ask_stream(self, query: str, group_id: str = 'default'):
            self.ask_stream_calls.append((query, group_id))
            yield {'type': 'trace', 'content': {'mode': 'chitchat', 'retrieval_rounds': 0, 'final_action': 'chitchat_answer', 'steps': []}}
            yield {'type': 'references', 'content': []}
            yield {'type': 'content', 'content': '这是流式代理回答。'}
            yield {'type': 'done', 'content': ''}

    agent_service = StubAgentService()
    service = ChatService(agent_service=agent_service)

    chunks = [chunk async for chunk in service.rag_stream('你好')]

    assert agent_service.ask_stream_calls == [('你好', 'default')]
    assert chunks == [
        f"data: {json.dumps({'type': 'trace', 'content': {'mode': 'chitchat', 'retrieval_rounds': 0, 'final_action': 'chitchat_answer', 'steps': []}}, ensure_ascii=False)}\n\n",
        f"data: {json.dumps({'type': 'references', 'content': []}, ensure_ascii=False)}\n\n",
        f"data: {json.dumps({'type': 'content', 'content': '这是流式代理回答。'}, ensure_ascii=False)}\n\n",
        f"data: {json.dumps({'type': 'done', 'content': ''}, ensure_ascii=False)}\n\n",
    ]
