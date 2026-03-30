from types import SimpleNamespace

import pytest

from app.schemas.agent import GraphRetrievalResult
from app.schemas.chat import ChatReference
from app.services.agent_tools.graph_retrieval_tool import GraphRetrievalTool
from app.services.knowledge_graph_service import KnowledgeGraphService


def test_graph_retrieval_result_defaults():
    result = GraphRetrievalResult(context='')

    assert result.context == ''
    assert result.references == []
    assert result.has_enough_evidence is False
    assert result.empty_reason == ''
    assert result.retrieved_edge_count == 0
    assert result.group_id == 'default'


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_retrieve_graph_context_returns_structured_result(monkeypatch):
    edge = SimpleNamespace(
        fact='Alice likes green tea',
        source_node=SimpleNamespace(name='Alice', summary='喜欢喝茶'),
        target_node=SimpleNamespace(name='Green Tea', summary='一种饮品'),
    )

    async def fake_search(query: str, group_id: str = 'default', limit: int = 5):
        return [edge]

    service = KnowledgeGraphService.__new__(KnowledgeGraphService)
    service.graphiti_client = SimpleNamespace(search=fake_search)

    result = await service.retrieve_graph_context('Alice 喜欢什么？')

    assert result.has_enough_evidence is True
    assert result.retrieved_edge_count == 1
    assert '关系: Alice likes green tea' in result.context
    assert len(result.references) == 3


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_answer_with_context_uses_retrieval_context_and_returns_references(monkeypatch):
    service = KnowledgeGraphService.__new__(KnowledgeGraphService)
    references = [
        ChatReference(type='relationship', fact='Alice likes green tea'),
        ChatReference(type='entity', name='Alice', summary='喜欢喝茶'),
    ]
    retrieval_result = GraphRetrievalResult(
        context='关系: Alice likes green tea\n\n实体: Alice\n描述: 喜欢喝茶',
        references=references,
        has_enough_evidence=True,
        retrieved_edge_count=1,
        group_id='team-a',
    )
    captured = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='Alice 喜欢绿茶。'))]
        )

    service.llm_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=fake_create)
        )
    )

    result = await service.answer_with_context('Alice 喜欢什么？', retrieval_result)

    assert result == {'answer': 'Alice 喜欢绿茶。', 'references': references}
    assert captured['model'] == 'step-1-8k'
    assert captured['max_tokens'] == 1024
    assert captured['temperature'] == 0.3
    assert captured['messages'][0]['role'] == 'system'
    assert '必须基于给定证据回答问题' in captured['messages'][0]['content']
    assert retrieval_result.context in captured['messages'][1]['content']
    assert 'Alice 喜欢什么？' in captured['messages'][1]['content']


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_ask_reuses_retrieval_and_answer_methods(monkeypatch):
    service = KnowledgeGraphService.__new__(KnowledgeGraphService)
    retrieval_result = GraphRetrievalResult(
        context='关系: Alice likes green tea',
        references=[ChatReference(type='relationship', fact='Alice likes green tea')],
        has_enough_evidence=True,
        retrieved_edge_count=1,
    )
    call_log = []

    async def fake_retrieve(query: str, group_id: str = 'default'):
        call_log.append(('retrieve', query, group_id))
        return retrieval_result

    async def fake_answer(query: str, provided_result: GraphRetrievalResult):
        call_log.append(('answer', query, provided_result))
        return {'answer': 'Alice 喜欢绿茶。', 'references': provided_result.references}

    monkeypatch.setattr(service, 'retrieve_graph_context', fake_retrieve)
    monkeypatch.setattr(service, 'answer_with_context', fake_answer)

    result = await service.ask('Alice 喜欢什么？', group_id='team-a')

    assert result == {
        'answer': 'Alice 喜欢绿茶。',
        'references': retrieval_result.references,
    }
    assert call_log == [
        ('retrieve', 'Alice 喜欢什么？', 'team-a'),
        ('answer', 'Alice 喜欢什么？', retrieval_result),
    ]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_ask_preserves_references_when_answer_generation_fails(monkeypatch):
    service = KnowledgeGraphService.__new__(KnowledgeGraphService)
    references = [ChatReference(type='relationship', fact='Alice likes green tea')]
    retrieval_result = GraphRetrievalResult(
        context='关系: Alice likes green tea',
        references=references,
        has_enough_evidence=True,
        retrieved_edge_count=1,
    )

    async def fake_retrieve(query: str, group_id: str = 'default'):
        return retrieval_result

    async def fake_answer(query: str, provided_result: GraphRetrievalResult):
        raise RuntimeError('llm unavailable')

    monkeypatch.setattr(service, 'retrieve_graph_context', fake_retrieve)
    monkeypatch.setattr(service, 'answer_with_context', fake_answer)

    result = await service.ask('Alice 喜欢什么？')

    assert result == {
        'answer': '抱歉，处理您的问题时出现错误：llm unavailable',
        'references': references,
    }


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_graph_retrieval_tool_delegates_to_service():
    expected = GraphRetrievalResult(
        context='关系: Alice likes green tea',
        references=[],
        has_enough_evidence=True,
        retrieved_edge_count=1,
    )
    call_log = []

    class StubKnowledgeGraphService:
        async def retrieve_graph_context(self, query: str, group_id: str = 'default'):
            call_log.append((query, group_id))
            return expected

    tool = GraphRetrievalTool(knowledge_graph_service=StubKnowledgeGraphService())

    result = await tool.run('Alice 喜欢什么？', group_id='team-a')

    assert result == expected
    assert call_log == [('Alice 喜欢什么？', 'team-a')]
