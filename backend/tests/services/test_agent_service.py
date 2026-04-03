import json

import pytest

from app.schemas.chat import ChatReference
from app.services.agent_service import AgentService
from app.services.chat_service import ChatService


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_agent_service_ask_delegates_to_canvas_runtime(monkeypatch):
    service = AgentService()

    async def fake_run_chat_canvas(query: str, *, group_id: str = 'default'):
        assert query == '你好'
        assert group_id == 'default'
        return {
            'answer': '你好！',
            'references': [],
            'agent_trace': {
                'mode': 'graph_rag',
                'retrieval_rounds': 0,
                'final_action': 'direct_general_answer',
                'steps': [],
            },
        }

    monkeypatch.setattr(service, '_run_chat_canvas', fake_run_chat_canvas)

    result = await service.ask('你好')

    assert result['answer'] == '你好！'
    assert result['references'] == []
    assert result['agent_trace']['final_action'] == 'direct_general_answer'


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_agent_service_stream_wraps_canvas_output(monkeypatch):
    references = [ChatReference(type='relationship', fact='星期一收集不可燃垃圾')]
    service = AgentService()

    async def fake_run_chat_canvas(query: str, *, group_id: str = 'default'):
        assert query == '星期一收集什么垃圾？'
        assert group_id == 'default'
        return {
            'answer': '根据图谱证据，星期一收集不可燃垃圾。',
            'references': references,
            'agent_trace': {
                'mode': 'graph_rag',
                'retrieval_rounds': 1,
                'final_action': 'kb_grounded_answer',
                'steps': [],
            },
        }

    monkeypatch.setattr(service, '_run_chat_canvas', fake_run_chat_canvas)

    chunks = [chunk async for chunk in service.ask_stream('星期一收集什么垃圾？')]

    assert chunks == [
        {
            'type': 'trace',
            'content': {
                'mode': 'graph_rag',
                'retrieval_rounds': 1,
                'final_action': 'kb_grounded_answer',
                'steps': [],
            },
        },
        {
            'type': 'references',
            'content': [reference.model_dump() for reference in references],
        },
        {
            'type': 'content',
            'content': '根据图谱证据，星期一收集不可燃垃圾。',
        },
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
async def test_chat_service_rag_stream_uses_agent_service_stream():
    class StubAgentService:
        def __init__(self) -> None:
            self.ask_stream_calls = []

        async def ask_stream(self, query: str, group_id: str = 'default'):
            self.ask_stream_calls.append((query, group_id))
            yield {
                'type': 'trace',
                'content': {
                    'mode': 'graph_rag',
                    'retrieval_rounds': 0,
                    'final_action': 'direct_general_answer',
                    'steps': [],
                },
            }
            yield {'type': 'references', 'content': []}
            yield {'type': 'content', 'content': '这是流式代理回答。'}
            yield {'type': 'done', 'content': ''}

    agent_service = StubAgentService()
    service = ChatService(agent_service=agent_service)

    chunks = [chunk async for chunk in service.rag_stream('你好')]

    assert agent_service.ask_stream_calls == [('你好', 'default')]
    assert chunks == [
        f"data: {json.dumps({'type': 'trace', 'content': {'mode': 'graph_rag', 'retrieval_rounds': 0, 'final_action': 'direct_general_answer', 'steps': []}}, ensure_ascii=False)}\n\n",
        f"data: {json.dumps({'type': 'references', 'content': []}, ensure_ascii=False)}\n\n",
        f"data: {json.dumps({'type': 'content', 'content': '这是流式代理回答。'}, ensure_ascii=False)}\n\n",
        f"data: {json.dumps({'type': 'done', 'content': ''}, ensure_ascii=False)}\n\n",
    ]
