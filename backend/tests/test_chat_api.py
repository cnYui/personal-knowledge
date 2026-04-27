import json
from contextlib import contextmanager
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.routers.chat as chat_router
import app.workflow.nodes.agent_node as agent_node_module
from app.main import app
from app.core.model_errors import ModelAPIError
from app.schemas.agent import GraphRetrievalResult
from app.schemas.chat import ChatReference
from app.services.chat_service import ChatService
from app.workflow.canvas_factory import CanvasFactory
from app.workflow.engine.citation_postprocessor import CitationResult


@contextmanager
def client_without_lifespan():
    """避免启动真实后台 worker，API 契约测试只验证路由与响应。"""
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()


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


class StubKnowledgeProfileService:
    @staticmethod
    def compose_system_prompt(base: str) -> str:
        return f'{base}\n\n[overlay]'


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


class StubKnowledgeGraphService:
    def __init__(self, *, llm_client, grounded_answer: str = '这是知识库回答。') -> None:
        self.llm_client = llm_client
        self._dialog_model = 'deepseek-chat'
        self.grounded_answer = grounded_answer

    def _ensure_dialog_client(self) -> None:
        return

    async def answer_with_context(self, query: str, retrieval_result: GraphRetrievalResult) -> dict:
        return {'answer': self.grounded_answer, 'references': retrieval_result.references}


def configure_real_canvas_chat_service(
    monkeypatch,
    *,
    llm_responses: list[FakeResponse],
    graph_retrieval_tool,
    grounded_answer: str = '这是知识库回答。',
) -> None:
    llm_client = FakeLLMClient(llm_responses)
    knowledge_graph_service = StubKnowledgeGraphService(
        llm_client=llm_client,
        grounded_answer=grounded_answer,
    )
    chat_router.service = ChatService(
        canvas_factory=CanvasFactory(
            knowledge_graph_service=knowledge_graph_service,
            graph_retrieval_tool=graph_retrieval_tool,
        ),
    )
    monkeypatch.setattr(agent_node_module, 'agent_knowledge_profile_service', StubKnowledgeProfileService())


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
    with client_without_lifespan() as client:
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
    with client_without_lifespan() as client:
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
    with client_without_lifespan() as client:
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
    with client_without_lifespan() as client:
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
    with client_without_lifespan() as client:
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


def test_rag_query_real_canvas_probe_sufficient_skips_tool_loop(monkeypatch):
    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            return GraphRetrievalResult(
                context='关系: OpenAI 发布了新的模型更新',
                references=[ChatReference(type='relationship', fact='OpenAI 发布了新的模型更新')],
                has_enough_evidence=True,
                retrieved_edge_count=1,
                group_id=group_id,
            )

    configure_real_canvas_chat_service(
        monkeypatch,
        llm_responses=[FakeResponse(FakeMessage(content='OpenAI / 模型更新'))],
        graph_retrieval_tool=StubGraphRetrievalTool(),
        grounded_answer='根据知识库，OpenAI 最近发布了新的模型更新。',
    )
    stub_citation_postprocessor(monkeypatch)

    with client_without_lifespan() as client:
        response = client.post("/api/chat/rag", json={"message": "OpenAI 最近有什么动态？"})

    assert response.status_code == 200
    payload = response.json()
    assert payload['answer'] == '根据知识库，OpenAI 最近发布了新的模型更新。'
    assert payload['agent_trace']['final_action'] == 'kb_grounded_answer'
    assert payload['agent_trace']['retrieval_rounds'] == 1
    assert payload['agent_trace']['tool_loop']['forced_retrieval'] is True
    assert payload['agent_trace']['tool_loop']['probe_decision'] == 'sufficient'
    assert payload['agent_trace']['tool_loop']['tool_steps'] == []


def test_rag_query_real_canvas_probe_no_hit_retry_then_direct_general(monkeypatch):
    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            return GraphRetrievalResult(
                context='',
                references=[],
                has_enough_evidence=False,
                empty_reason='图谱中没有足够信息',
                retrieved_edge_count=0,
                group_id=group_id,
            )

    configure_real_canvas_chat_service(
        monkeypatch,
        llm_responses=[
            FakeResponse(FakeMessage(content='OpenAI / 最近动态')),
            FakeResponse(FakeMessage(content='这是基于通用模型的回答。')),
        ],
        graph_retrieval_tool=StubGraphRetrievalTool(),
    )
    stub_citation_postprocessor(monkeypatch)

    with client_without_lifespan() as client:
        response = client.post("/api/chat/rag", json={"message": "OpenAI 最近有什么动态？"})

    assert response.status_code == 200
    payload = response.json()
    assert payload['answer'] == '这是基于通用模型的回答。'
    assert payload['references'] == []
    assert payload['agent_trace']['final_action'] == 'direct_general_answer'
    assert payload['agent_trace']['retrieval_rounds'] == 2
    assert payload['agent_trace']['tool_loop']['forced_retrieval'] is True
    assert payload['agent_trace']['tool_loop']['probe_decision'] == 'no_hit'
    assert payload['agent_trace']['tool_loop']['probe_queries'] == ['OpenAI 最近有什么动态？', 'OpenAI / 最近动态']
    assert payload['agent_trace']['tool_loop']['tool_steps'] == []


def test_rag_query_real_canvas_probe_insufficient_enters_tool_loop(monkeypatch):
    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            if query == '什么是向量空间？':
                return GraphRetrievalResult(
                    context='实体: 向量空间\n描述: 线性代数基础对象',
                    references=[ChatReference(type='entity', name='向量空间', summary='线性代数基础对象')],
                    has_enough_evidence=False,
                    empty_reason='证据不足',
                    retrieved_edge_count=1,
                    group_id=group_id,
                )
            return GraphRetrievalResult(
                context='关系: 向量空间定义了加法和数乘运算',
                references=[ChatReference(type='relationship', fact='向量空间定义了加法和数乘运算')],
                has_enough_evidence=True,
                retrieved_edge_count=1,
                group_id=group_id,
            )

    configure_real_canvas_chat_service(
        monkeypatch,
        llm_responses=[
            FakeResponse(FakeMessage(content='向量空间 / 定义')),
            FakeResponse(
                FakeMessage(
                    tool_calls=[
                        FakeToolCall('tool-1', 'graph_retrieval_tool', '{"query":"向量空间的定义"}')
                    ]
                )
            ),
            FakeResponse(FakeMessage(content='向量空间是定义了加法和数乘运算的集合。')),
        ],
        graph_retrieval_tool=StubGraphRetrievalTool(),
    )
    stub_citation_postprocessor(monkeypatch)

    with client_without_lifespan() as client:
        response = client.post("/api/chat/rag", json={"message": "什么是向量空间？"})

    assert response.status_code == 200
    payload = response.json()
    assert payload['answer'] == '向量空间是定义了加法和数乘运算的集合。'
    assert payload['agent_trace']['final_action'] == 'kb_grounded_answer'
    assert payload['agent_trace']['retrieval_rounds'] == 2
    assert payload['agent_trace']['tool_loop']['forced_retrieval'] is True
    assert payload['agent_trace']['tool_loop']['probe_decision'] == 'insufficient'
    assert len(payload['agent_trace']['tool_loop']['tool_steps']) == 1
    assert payload['agent_trace']['tool_loop']['tool_steps'][0]['arguments']['query'] == '向量空间的定义'
