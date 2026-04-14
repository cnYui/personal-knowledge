import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.routers.chat as chat_router
from app.main import app
from app.core.model_errors import ModelAPIError
from app.schemas.chat import ChatReference
from app.workflow.engine.citation_postprocessor import CitationResult


class StubCitationPostProcessor:
    def __init__(self, sentence_citations: list[dict] | None = None) -> None:
        self.sentence_citations = sentence_citations or []

    async def process(self, *, answer: str, reference_store, include_reference_section: bool = True):
        snapshot = reference_store.snapshot()
        citations = []
        for evidence in snapshot.get('graph_evidence', []):
            if evidence.get('fact'):
                label = evidence['fact']
            elif evidence.get('name') and evidence.get('summary'):
                label = f"{evidence['name']}：{evidence['summary']}"
            elif evidence.get('summary'):
                label = evidence['summary']
            else:
                label = evidence.get('name') or evidence.get('type')
            citations.append(
                {
                    'index': len(citations) + 1,
                    'type': evidence.get('type') or 'graph_evidence',
                    'label': label,
                    'source': evidence,
                }
            )
        return CitationResult(
            answer=answer,
            cited_answer=answer,
            citations=citations,
            sentence_citations=list(self.sentence_citations),
            used_general_fallback=False,
        )


def stub_citation_postprocessor(monkeypatch, sentence_citations: list[dict] | None = None) -> None:
    monkeypatch.setattr(
        chat_router.service,
        'citation_postprocessor',
        StubCitationPostProcessor(sentence_citations),
    )


def build_expected_trace(trace: dict, references: list[ChatReference]):
    def build_label(reference: ChatReference) -> str:
        if reference.fact:
            return reference.fact
        if reference.name and reference.summary:
            return f'{reference.name}：{reference.summary}'
        if reference.summary:
            return reference.summary
        return reference.name or reference.type

    return {
        **trace,
        'canvas': {
            'execution_path': ['begin', 'agent', 'message'],
            'events': [
                {'event': 'node_finished', 'node_id': 'agent', 'node_type': None},
                {'event': 'node_finished', 'node_id': 'message', 'node_type': None},
            ],
        },
        'tool_loop': {
            'forced_retrieval': False,
            'tool_rounds_exceeded': False,
            'tool_steps': [],
        },
        'citation': {
            'count': len(references),
            'used_general_fallback': False,
            'items': [
                {
                    'index': index + 1,
                    'type': reference.type,
                    'label': build_label(reference),
                }
                for index, reference in enumerate(references)
            ],
        },
        'reference_store': {
            'chunk_count': 0,
            'doc_count': 0,
            'graph_evidence_count': len(references),
        },
    }


def build_stub_canvas(*, answer: str, references: list[ChatReference], trace: dict):
    graph_evidence = [reference.model_dump() for reference in references]

    class StubReferenceStore:
        def snapshot(self):
            return {'chunks': [], 'doc_aggs': [], 'graph_evidence': graph_evidence}

    class StubCanvas:
        def __init__(self) -> None:
            self.execution_path = ['begin', 'agent', 'message']
            self.reference_store = StubReferenceStore()
            self._runtime_event_sink = None

        def set_runtime_event_sink(self, sink):
            self._runtime_event_sink = sink

        async def run(self):
            yield SimpleNamespace(event='workflow_started', node_id=None, payload={})
            yield SimpleNamespace(
                event='node_finished',
                node_id='agent',
                payload={
                    'output': {
                        'answer': answer,
                        'references': references,
                        'agent_trace': trace,
                    }
                },
            )
            yield SimpleNamespace(
                event='node_finished',
                node_id='message',
                payload={
                    'output': {
                        'content': answer,
                        'references': references,
                    }
                },
            )
            yield SimpleNamespace(event='workflow_finished', node_id=None, payload={})

    return StubCanvas()


def test_send_chat_message_returns_answer_and_persists_messages_via_agent(monkeypatch):
    call_log = []
    trace = {'mode': 'graph_rag', 'retrieval_rounds': 1, 'final_action': 'kb_grounded_answer', 'steps': []}
    references = [ChatReference(type='entity', name='向量空间', summary='线性代数中的基本概念')]

    def fake_create_chat_canvas(*, query: str, group_id: str = 'default', **kwargs):
        call_log.append((query, group_id))
        return build_stub_canvas(
            answer='这是代理返回的答案。',
            references=references,
            trace=trace,
        )

    monkeypatch.setattr(chat_router.service.canvas_factory, 'create_chat_canvas', fake_create_chat_canvas)
    stub_citation_postprocessor(monkeypatch, [{'sentence_index': 0, 'citation_indexes': [1]}])
    with TestClient(app) as client:
        client.delete("/api/chat/messages")

        response = client.post("/api/chat/messages", json={"message": "什么是向量空间？"})

        assert response.status_code == 200
        assert response.json() == {
            'answer': '这是代理返回的答案。',
            'references': [
                {'type': 'entity', 'name': '向量空间', 'summary': '线性代数中的基本概念', 'fact': None}
            ],
            'citation_section': ['向量空间：线性代数中的基本概念'],
            'sentence_citations': [{'sentence_index': 0, 'citation_indexes': [1]}],
            'agent_trace': build_expected_trace(trace, references),
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
    trace = {'mode': 'graph_rag', 'retrieval_rounds': 1, 'final_action': 'kb_grounded_answer', 'steps': []}
    references = [ChatReference(type='relationship', fact='向量空间可用于表示向量集合')]

    def fake_create_chat_canvas(*, query: str, group_id: str = 'default', **kwargs):
        call_log.append((query, group_id))
        return build_stub_canvas(
            answer='这是仅用于 RAG 查询的答案。',
            references=references,
            trace=trace,
        )

    monkeypatch.setattr(chat_router.service.canvas_factory, 'create_chat_canvas', fake_create_chat_canvas)
    stub_citation_postprocessor(monkeypatch)
    with TestClient(app) as client:
        client.delete("/api/chat/messages")

        response = client.post("/api/chat/rag", json={"message": "向量空间有什么用途？"})

        assert response.status_code == 200
        assert response.json() == {
            'answer': '这是仅用于 RAG 查询的答案。',
            'references': [
                {'type': 'relationship', 'name': None, 'summary': None, 'fact': '向量空间可用于表示向量集合'}
            ],
            'citation_section': ['向量空间可用于表示向量集合'],
            'sentence_citations': [],
            'agent_trace': build_expected_trace(trace, references),
        }
        assert call_log == [('向量空间有什么用途？', 'default')]

        messages_response = client.get("/api/chat/messages")
        assert messages_response.status_code == 200
        assert messages_response.json() == []


def test_rag_query_uses_model_api_exception_handler(monkeypatch):
    def fake_create_chat_canvas(*, query: str, group_id: str = 'default', **kwargs):
        raise ModelAPIError(
            error_code='MODEL_API_KEY_MISSING',
            message='尚未配置 API Key，请先前往设置页面完成配置。',
            status_code=400,
            details='对话模型 缺少可用的 deepseek API Key。',
            provider='deepseek',
            retryable=False,
        )

    monkeypatch.setattr(chat_router.service.canvas_factory, 'create_chat_canvas', fake_create_chat_canvas)
    with TestClient(app) as client:
        response = client.post("/api/chat/rag", json={"message": "解释一下 Transformer"})

    assert response.status_code == 400
    assert response.json() == {
        'error_code': 'MODEL_API_KEY_MISSING',
        'message': '尚未配置 API Key，请先前往设置页面完成配置。',
        'details': '对话模型 缺少可用的 deepseek API Key。',
        'provider': 'deepseek',
        'retryable': False,
    }


def test_rag_stream_uses_agent_stream_path_and_returns_sse_payload(monkeypatch):
    call_log = []
    trace = {'mode': 'graph_rag', 'retrieval_rounds': 1, 'final_action': 'kb_grounded_answer', 'steps': []}
    references = [ChatReference(type='relationship', fact='向量空间可用于表示向量集合')]

    def fake_create_chat_canvas(*, query: str, group_id: str = 'default', **kwargs):
        call_log.append((query, group_id))
        return build_stub_canvas(
            answer='这是流式代理答案。',
            references=references,
            trace=trace,
        )

    monkeypatch.setattr(chat_router.service.canvas_factory, 'create_chat_canvas', fake_create_chat_canvas)
    stub_citation_postprocessor(monkeypatch)
    with TestClient(app) as client:
        with client.stream("POST", "/api/chat/stream", json={"message": "向量空间有什么用途？"}) as response:
            assert response.status_code == 200
            assert response.headers['content-type'].startswith('text/event-stream')
            body = ''.join(response.iter_text())

    assert call_log == [('向量空间有什么用途？', 'default')]
    assert '"type": "timeline"' in body
    assert '"title": "理解问题"' in body
    assert '"title": "整理引用与轨迹"' in body
    assert '"type": "trace"' in body
    assert json.dumps(build_expected_trace(trace, references), ensure_ascii=False) in body
    assert '"type": "references"' in body
    assert '"type": "citation_section"' in body
    assert '"type": "sentence_citations"' in body
    assert '"type": "content"' in body
    assert '这是流式代理答案。' in body
    assert '"type": "done"' in body


def test_rag_stream_returns_structured_model_error_payload(monkeypatch):
    def fake_create_chat_canvas(*, query: str, group_id: str = 'default', **kwargs):
        raise ModelAPIError(
            error_code='MODEL_API_QUOTA_EXCEEDED',
            message='当前 API Key 可用额度已用完，请更换 Key 或检查账号额度。',
            status_code=402,
            details='402 insufficient quota',
            provider='deepseek',
            retryable=False,
        )

    monkeypatch.setattr(chat_router.service.canvas_factory, 'create_chat_canvas', fake_create_chat_canvas)
    with TestClient(app) as client:
        with client.stream("POST", "/api/chat/stream", json={"message": "你好"}) as response:
            assert response.status_code == 200
            body = ''.join(response.iter_text())

    assert body == ''.join(
        [
            "data: "
            + json.dumps(
                {
                    'type': 'error',
                    'content': '当前 API Key 可用额度已用完，请更换 Key 或检查账号额度。',
                    'error_code': 'MODEL_API_QUOTA_EXCEEDED',
                    'message': '当前 API Key 可用额度已用完，请更换 Key 或检查账号额度。',
                    'details': '402 insufficient quota',
                    'provider': 'deepseek',
                    'retryable': False,
                },
                ensure_ascii=False,
            )
            + "\n\n"
        ]
    )
