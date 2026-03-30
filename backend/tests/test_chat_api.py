from fastapi.testclient import TestClient
import json

import app.routers.chat as chat_router
from app.main import app
from app.schemas.chat import ChatReference


def test_send_chat_message_returns_answer_and_persists_messages_via_agent(monkeypatch):
    call_log = []

    async def fake_ask(message: str, group_id: str = 'default'):
        call_log.append((message, group_id))
        return {
            'answer': '这是代理返回的答案。',
            'references': [ChatReference(type='entity', name='向量空间', summary='线性代数中的基本概念')],
            'agent_trace': {'mode': 'graph_rag', 'retrieval_rounds': 1, 'final_action': 'answer', 'steps': []},
        }

    monkeypatch.setattr(chat_router.service.agent_service, 'ask', fake_ask)
    client = TestClient(app)
    client.delete("/api/chat/messages")

    response = client.post("/api/chat/messages", json={"message": "什么是向量空间？"})

    assert response.status_code == 200
    assert response.json() == {
        'answer': '这是代理返回的答案。',
        'references': [
            {'type': 'entity', 'name': '向量空间', 'summary': '线性代数中的基本概念', 'fact': None}
        ],
        'agent_trace': {'mode': 'graph_rag', 'retrieval_rounds': 1, 'final_action': 'answer', 'steps': []},
    }
    assert call_log == [('什么是向量空间？', 'default')]

    messages_response = client.get("/api/chat/messages")
    assert messages_response.status_code == 200
    assert messages_response.json()[-2:] == [
        {'id': messages_response.json()[-2]['id'], 'role': 'user', 'content': '什么是向量空间？', 'created_at': messages_response.json()[-2]['created_at']},
        {'id': messages_response.json()[-1]['id'], 'role': 'assistant', 'content': '这是代理返回的答案。', 'created_at': messages_response.json()[-1]['created_at']},
    ]


def test_rag_query_returns_agent_answer_without_persisting_messages(monkeypatch):
    call_log = []

    async def fake_ask(message: str, group_id: str = 'default'):
        call_log.append((message, group_id))
        return {
            'answer': '这是仅用于 RAG 查询的答案。',
            'references': [ChatReference(type='relationship', fact='向量空间可用于表示向量集合')],
            'agent_trace': {'mode': 'graph_rag', 'retrieval_rounds': 1, 'final_action': 'answer', 'steps': []},
        }

    monkeypatch.setattr(chat_router.service.agent_service, 'ask', fake_ask)
    client = TestClient(app)
    client.delete("/api/chat/messages")

    response = client.post("/api/chat/rag", json={"message": "向量空间有什么用途？"})

    assert response.status_code == 200
    assert response.json() == {
        'answer': '这是仅用于 RAG 查询的答案。',
        'references': [
            {'type': 'relationship', 'name': None, 'summary': None, 'fact': '向量空间可用于表示向量集合'}
        ],
        'agent_trace': {'mode': 'graph_rag', 'retrieval_rounds': 1, 'final_action': 'answer', 'steps': []},
    }
    assert call_log == [('向量空间有什么用途？', 'default')]

    messages_response = client.get("/api/chat/messages")
    assert messages_response.status_code == 200
    assert messages_response.json() == []


def test_rag_stream_uses_agent_stream_path_and_returns_sse_payload(monkeypatch):
    call_log = []

    async def fake_ask_stream(message: str, group_id: str = 'default'):
        call_log.append((message, group_id))
        yield {'type': 'trace', 'content': {'mode': 'graph_rag', 'retrieval_rounds': 1, 'final_action': 'answer', 'steps': []}}
        yield {
            'type': 'references',
            'content': [
                {'type': 'relationship', 'name': None, 'summary': None, 'fact': '向量空间可用于表示向量集合'}
            ],
        }
        yield {'type': 'content', 'content': '这是流式代理答案。'}
        yield {'type': 'done', 'content': ''}

    monkeypatch.setattr(chat_router.service.agent_service, 'ask_stream', fake_ask_stream)
    client = TestClient(app)

    with client.stream("POST", "/api/chat/stream", json={"message": "向量空间有什么用途？"}) as response:
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('text/event-stream')
        body = ''.join(response.iter_text())

    assert call_log == [('向量空间有什么用途？', 'default')]
    assert body == ''.join(
        [
            f"data: {json.dumps({'type': 'trace', 'content': {'mode': 'graph_rag', 'retrieval_rounds': 1, 'final_action': 'answer', 'steps': []}}, ensure_ascii=False)}\n\n",
            f"data: {json.dumps({'type': 'references', 'content': [{'type': 'relationship', 'name': None, 'summary': None, 'fact': '向量空间可用于表示向量集合'}]}, ensure_ascii=False)}\n\n",
            f"data: {json.dumps({'type': 'content', 'content': '这是流式代理答案。'}, ensure_ascii=False)}\n\n",
            f"data: {json.dumps({'type': 'done', 'content': ''}, ensure_ascii=False)}\n\n",
        ]
    )
