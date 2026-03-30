# Agentic Graph RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the current Graphiti-backed chat flow from a fixed graph RAG pipeline into a strict-mode Agentic RAG with a single `graph_retrieval_tool` and an `AgentService` orchestration layer.

**Architecture:** Keep the external chat API stable while inserting `AgentService` between `ChatService` and the current graph RAG logic. Split `KnowledgeGraphService` into retrieval and answer-generation responsibilities, expose retrieval as a structured tool, and enforce strict prompt rules so non-chitchat questions must retrieve graph evidence before answering.

**Tech Stack:** FastAPI, SQLAlchemy, Graphiti, OpenAI-compatible chat completions, pytest, SSE streaming

---

## File Structure

### New Files
- `backend/app/services/agent_service.py` - Orchestrates strict-mode agent flow and final answer generation
- `backend/app/services/agent_prompts.py` - Centralizes strict-mode agent prompts and routing helpers
- `backend/app/services/agent_tools/__init__.py` - Tool package marker
- `backend/app/services/agent_tools/graph_retrieval_tool.py` - Wraps graph retrieval as a structured tool
- `backend/app/schemas/agent.py` - Structured tool output schemas for agent/tool communication
- `backend/tests/services/test_agent_service.py` - Tests agent routing and strict-mode behavior
- `backend/tests/services/test_graph_retrieval_tool.py` - Tests tool output shape and empty-result behavior

### Modified Files
- `backend/app/services/knowledge_graph_service.py` - Split retrieval from answer generation and keep compatibility wrappers
- `backend/app/services/chat_service.py` - Route chat and stream calls through `AgentService`
- `backend/app/routers/chat.py` - Only if constructor wiring changes; keep API paths stable
- `backend/app/schemas/chat.py` - Only if references or response metadata need additive fields
- `backend/tests/test_chat_api.py` - Update chat endpoint assertions to cover agent path

### Optional Follow-Up Files (only if needed during implementation)
- `backend/app/core/config.py` - Add feature flag or prompt model setting if prompt control should be configurable
- `backend/tests/integration/test_agentic_rag_flow.py` - Add end-to-end integration coverage if unit-level mocking proves insufficient

---

## Task 1: Define Agent Tool Schemas and Prompt Constants

**Files:**
- Create: `backend/app/schemas/agent.py`
- Create: `backend/app/services/agent_prompts.py`
- Test: `backend/tests/services/test_graph_retrieval_tool.py`

- [ ] **Step 1: Write the failing schema test**

Create `backend/tests/services/test_graph_retrieval_tool.py` with:

```python
from app.schemas.agent import GraphRetrievalResult


def test_graph_retrieval_result_defaults():
    result = GraphRetrievalResult(context='', references=[])

    assert result.context == ''
    assert result.references == []
    assert result.has_enough_evidence is False
    assert result.empty_reason == ''
    assert result.retrieved_edge_count == 0
    assert result.group_id == 'default'
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend
pytest tests/services/test_graph_retrieval_tool.py::test_graph_retrieval_result_defaults -v
```

Expected: FAIL with `ModuleNotFoundError` or `cannot import name 'GraphRetrievalResult'`

- [ ] **Step 3: Create the schema file**

Create `backend/app/schemas/agent.py` with:

```python
from pydantic import BaseModel, Field

from app.schemas.chat import ChatReference


class GraphRetrievalResult(BaseModel):
    context: str
    references: list[ChatReference] = Field(default_factory=list)
    has_enough_evidence: bool = False
    empty_reason: str = ''
    retrieved_edge_count: int = 0
    group_id: str = 'default'
```

- [ ] **Step 4: Create strict-mode prompt helpers**

Create `backend/app/services/agent_prompts.py` with:

```python
STRICT_AGENT_SYSTEM_PROMPT = """你是个人知识库助手。

规则：
1. 除明显寒暄外，必须先调用 graph_retrieval_tool 获取证据。
2. 如果没有证据，不允许编造事实。
3. 回答必须基于检索到的 context 与 references。
4. 如证据不足，明确告知用户当前图谱中没有足够信息。
5. 请始终使用中文回答。
"""

CHITCHAT_PREFIXES = (
    '你好',
    '嗨',
    'hello',
    'hi',
    '早上好',
    '晚上好',
)
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
cd backend
pytest tests/services/test_graph_retrieval_tool.py::test_graph_retrieval_result_defaults -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/schemas/agent.py app/services/agent_prompts.py tests/services/test_graph_retrieval_tool.py
git commit -m "feat: add agent tool schemas and strict prompts"
```

---

## Task 2: Split Graph Retrieval from Answer Generation

**Files:**
- Modify: `backend/app/services/knowledge_graph_service.py`
- Test: `backend/tests/services/test_graph_retrieval_tool.py`

- [ ] **Step 1: Add a failing retrieval-layer test**

Append to `backend/tests/services/test_graph_retrieval_tool.py`:

```python
import pytest
from types import SimpleNamespace

from app.services.knowledge_graph_service import KnowledgeGraphService


@pytest.mark.asyncio
async def test_retrieve_graph_context_returns_structured_result(monkeypatch):
    service = KnowledgeGraphService()

    edge = SimpleNamespace(
        fact='Alice likes green tea',
        source_node=SimpleNamespace(name='Alice', summary='喜欢喝茶'),
        target_node=SimpleNamespace(name='Green Tea', summary='一种饮品'),
    )

    async def fake_search(query: str, group_id: str = 'default', limit: int = 5):
        return [edge]

    monkeypatch.setattr(service.graphiti_client, 'search', fake_search)

    result = await service.retrieve_graph_context('Alice 喜欢什么？')

    assert result.has_enough_evidence is True
    assert result.retrieved_edge_count == 1
    assert '关系: Alice likes green tea' in result.context
    assert len(result.references) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend
pytest tests/services/test_graph_retrieval_tool.py::test_retrieve_graph_context_returns_structured_result -v
```

Expected: FAIL with `AttributeError: 'KnowledgeGraphService' object has no attribute 'retrieve_graph_context'`

- [ ] **Step 3: Extract graph retrieval into its own method**

Add to `backend/app/services/knowledge_graph_service.py`:

```python
from app.schemas.agent import GraphRetrievalResult
from app.schemas.chat import ChatReference


async def retrieve_graph_context(self, query: str, group_id: str = 'default') -> GraphRetrievalResult:
    edges = await self.graphiti_client.search(query, group_id=group_id, limit=5)

    context_parts: list[str] = []
    references: list[ChatReference] = []

    for edge in edges:
        if getattr(edge, 'fact', None):
            context_parts.append(f'关系: {edge.fact}')
            references.append(ChatReference(type='relationship', fact=edge.fact))

        for attr in ('source_node', 'target_node'):
            node = getattr(edge, attr, None)
            if node and getattr(node, 'name', None) and getattr(node, 'summary', None):
                context_parts.append(f'实体: {node.name}\n描述: {node.summary}')
                references.append(ChatReference(type='entity', name=node.name, summary=node.summary))

    if not context_parts:
        return GraphRetrievalResult(
            context='',
            references=[],
            has_enough_evidence=False,
            empty_reason='图谱中没有足够信息',
            retrieved_edge_count=0,
            group_id=group_id,
        )

    return GraphRetrievalResult(
        context='\n\n'.join(context_parts),
        references=references,
        has_enough_evidence=True,
        empty_reason='',
        retrieved_edge_count=len(edges),
        group_id=group_id,
    )
```

- [ ] **Step 4: Add a dedicated answer method without retrieval**

Add to `backend/app/services/knowledge_graph_service.py`:

```python
async def answer_with_context(self, query: str, retrieval_result: GraphRetrievalResult) -> dict:
    if not retrieval_result.has_enough_evidence:
        return {
            'answer': '抱歉，我在知识图谱中没有找到足够相关的信息。',
            'references': retrieval_result.references,
        }

    system_prompt = """你是一个知识助手，必须基于给定证据回答问题。
如果证据不足，明确说明，不允许编造。请用中文回答。"""

    user_prompt = f"""【知识图谱上下文】\n{retrieval_result.context}\n\n【用户问题】\n{query}\n\n请基于上述上下文回答问题。"""

    response = self.llm_client.chat.completions.create(
        model='step-1-8k',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        max_tokens=1024,
        temperature=0.3,
    )
    answer = response.choices[0].message.content
    return {'answer': answer, 'references': retrieval_result.references}
```

- [ ] **Step 5: Preserve compatibility wrappers**

Update `ask()` to become:

```python
async def ask(self, query: str, group_id: str = 'default') -> dict:
    retrieval_result = await self.retrieve_graph_context(query, group_id)
    return await self.answer_with_context(query, retrieval_result)
```

Update `ask_stream()` to call `retrieve_graph_context()` first, yield references, then stream answer from the same context.

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
cd backend
pytest tests/services/test_graph_retrieval_tool.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/services/knowledge_graph_service.py tests/services/test_graph_retrieval_tool.py
git commit -m "refactor: split graph retrieval from answer generation"
```

---

## Task 3: Wrap Graph Retrieval as an Agent Tool

**Files:**
- Create: `backend/app/services/agent_tools/__init__.py`
- Create: `backend/app/services/agent_tools/graph_retrieval_tool.py`
- Test: `backend/tests/services/test_graph_retrieval_tool.py`

- [ ] **Step 1: Add the failing tool test**

Append to `backend/tests/services/test_graph_retrieval_tool.py`:

```python
import pytest

from app.schemas.agent import GraphRetrievalResult
from app.services.agent_tools.graph_retrieval_tool import GraphRetrievalTool


@pytest.mark.asyncio
async def test_graph_retrieval_tool_delegates_to_service(monkeypatch):
    tool = GraphRetrievalTool()
    expected = GraphRetrievalResult(
        context='关系: Alice likes green tea',
        references=[],
        has_enough_evidence=True,
        retrieved_edge_count=1,
    )

    async def fake_retrieve(query: str, group_id: str = 'default'):
        return expected

    monkeypatch.setattr(tool.knowledge_graph_service, 'retrieve_graph_context', fake_retrieve)

    result = await tool.run('Alice 喜欢什么？')

    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend
pytest tests/services/test_graph_retrieval_tool.py::test_graph_retrieval_tool_delegates_to_service -v
```

Expected: FAIL with `ModuleNotFoundError` for `graph_retrieval_tool`

- [ ] **Step 3: Create the tool package files**

Create `backend/app/services/agent_tools/__init__.py`:

```python
from app.services.agent_tools.graph_retrieval_tool import GraphRetrievalTool

__all__ = ['GraphRetrievalTool']
```

Create `backend/app/services/agent_tools/graph_retrieval_tool.py`:

```python
from app.schemas.agent import GraphRetrievalResult
from app.services.knowledge_graph_service import KnowledgeGraphService


class GraphRetrievalTool:
    name = 'graph_retrieval_tool'
    description = 'Search the Graphiti temporal knowledge graph and return evidence for answering the user question.'

    def __init__(self, knowledge_graph_service: KnowledgeGraphService | None = None) -> None:
        self.knowledge_graph_service = knowledge_graph_service or KnowledgeGraphService()

    async def run(self, query: str, group_id: str = 'default') -> GraphRetrievalResult:
        return await self.knowledge_graph_service.retrieve_graph_context(query, group_id=group_id)
```

- [ ] **Step 4: Run the tool tests**

Run:

```bash
cd backend
pytest tests/services/test_graph_retrieval_tool.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/agent_tools/__init__.py app/services/agent_tools/graph_retrieval_tool.py tests/services/test_graph_retrieval_tool.py
git commit -m "feat: add graph retrieval agent tool"
```

---

## Task 4: Add AgentService and Route Chat Through It

**Files:**
- Create: `backend/app/services/agent_service.py`
- Modify: `backend/app/services/chat_service.py`
- Test: `backend/tests/services/test_agent_service.py`
- Test: `backend/tests/test_chat_api.py`

- [ ] **Step 1: Write the failing AgentService test**

Create `backend/tests/services/test_agent_service.py` with:

```python
import pytest
from app.schemas.agent import GraphRetrievalResult
from app.services.agent_service import AgentService


@pytest.mark.asyncio
async def test_agent_service_uses_tool_for_non_chitchat(monkeypatch):
    service = AgentService()
    retrieval_result = GraphRetrievalResult(
        context='关系: Alice likes green tea',
        references=[],
        has_enough_evidence=True,
        retrieved_edge_count=1,
    )

    async def fake_run(query: str, group_id: str = 'default'):
        return retrieval_result

    async def fake_answer(query: str, retrieval_result: GraphRetrievalResult):
        return {'answer': 'Alice 喜欢绿茶', 'references': retrieval_result.references}

    monkeypatch.setattr(service.graph_tool, 'run', fake_run)
    monkeypatch.setattr(service.knowledge_graph_service, 'answer_with_context', fake_answer)

    result = await service.ask('Alice 喜欢什么？')

    assert result['answer'] == 'Alice 喜欢绿茶'
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend
pytest tests/services/test_agent_service.py::test_agent_service_uses_tool_for_non_chitchat -v
```

Expected: FAIL with `ModuleNotFoundError` for `agent_service`

- [ ] **Step 3: Implement AgentService**

Create `backend/app/services/agent_service.py` with:

```python
from app.schemas.agent import GraphRetrievalResult
from app.services.agent_prompts import CHITCHAT_PREFIXES
from app.services.agent_tools import GraphRetrievalTool
from app.services.knowledge_graph_service import KnowledgeGraphService


class AgentService:
    def __init__(self,
                 graph_tool: GraphRetrievalTool | None = None,
                 knowledge_graph_service: KnowledgeGraphService | None = None) -> None:
        self.graph_tool = graph_tool or GraphRetrievalTool()
        self.knowledge_graph_service = knowledge_graph_service or KnowledgeGraphService()

    def is_chitchat(self, message: str) -> bool:
        normalized = message.strip().lower()
        return any(normalized.startswith(prefix.lower()) for prefix in CHITCHAT_PREFIXES)

    async def ask(self, message: str, group_id: str = 'default') -> dict:
        if self.is_chitchat(message):
            return {'answer': '你好，很高兴和你聊天。你也可以直接问我知识库里的问题。', 'references': []}

        retrieval_result = await self.graph_tool.run(message, group_id=group_id)
        return await self.knowledge_graph_service.answer_with_context(message, retrieval_result)

    async def ask_stream(self, message: str, group_id: str = 'default'):
        retrieval_result = await self.graph_tool.run(message, group_id=group_id)
        yield {'type': 'references', 'content': [ref.model_dump() for ref in retrieval_result.references]}
        if not retrieval_result.has_enough_evidence:
            yield {'type': 'content', 'content': '抱歉，我在知识图谱中没有找到足够相关的信息。'}
            yield {'type': 'done', 'content': ''}
            return
        async for chunk in self.knowledge_graph_service.answer_with_context_stream(message, retrieval_result):
            yield chunk
```

- [ ] **Step 4: Route ChatService through AgentService**

Update `backend/app/services/chat_service.py` to:

```python
from app.services.agent_service import AgentService


class ChatService:
    def __init__(self, repository: ChatRepository | None = None, knowledge_graph_service: KnowledgeGraphService | None = None, agent_service: AgentService | None = None) -> None:
        self.repository = repository or ChatRepository()
        self.knowledge_graph_service = knowledge_graph_service or KnowledgeGraphService()
        self.agent_service = agent_service or AgentService(knowledge_graph_service=self.knowledge_graph_service)

    async def send_message(self, db: Session, message: str) -> ChatResponse:
        self.repository.create(db, 'user', message)
        result = await self.agent_service.ask(message)
        self.repository.create(db, 'assistant', str(result['answer']))
        return ChatResponse(answer=str(result['answer']), references=list(result['references']))

    async def rag_query(self, message: str) -> ChatResponse:
        result = await self.agent_service.ask(message)
        return ChatResponse(answer=str(result['answer']), references=list(result['references']))

    async def rag_stream(self, message: str):
        async for chunk in self.agent_service.ask_stream(message):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
```

- [ ] **Step 5: Update the API smoke test**

Replace `backend/tests/test_chat_api.py` with:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_send_chat_message_returns_answer_and_references():
    client = TestClient(app)

    response = client.post('/api/chat/messages', json={'message': '什么是向量空间？'})

    assert response.status_code == 200
    payload = response.json()
    assert 'answer' in payload
    assert 'references' in payload
```

- [ ] **Step 6: Run service and API tests**

Run:

```bash
cd backend
pytest tests/services/test_agent_service.py tests/test_chat_api.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/services/agent_service.py app/services/chat_service.py tests/services/test_agent_service.py tests/test_chat_api.py
git commit -m "feat: route chat through strict agent service"
```

---

## Task 5: Add Streaming Answer Helper and Regression Coverage

**Files:**
- Modify: `backend/app/services/knowledge_graph_service.py`
- Modify: `backend/app/services/agent_service.py`
- Test: `backend/tests/services/test_agent_service.py`

- [ ] **Step 1: Add the failing stream test**

Append to `backend/tests/services/test_agent_service.py`:

```python
import pytest
from app.schemas.agent import GraphRetrievalResult
from app.services.agent_service import AgentService


@pytest.mark.asyncio
async def test_agent_service_streams_references_then_content(monkeypatch):
    service = AgentService()
    retrieval_result = GraphRetrievalResult(
        context='关系: Alice likes green tea',
        references=[],
        has_enough_evidence=True,
        retrieved_edge_count=1,
    )

    async def fake_run(query: str, group_id: str = 'default'):
        return retrieval_result

    async def fake_stream(query: str, retrieval_result: GraphRetrievalResult):
        yield {'type': 'content', 'content': 'Alice '}
        yield {'type': 'content', 'content': '喜欢绿茶'}
        yield {'type': 'done', 'content': ''}

    monkeypatch.setattr(service.graph_tool, 'run', fake_run)
    monkeypatch.setattr(service.knowledge_graph_service, 'answer_with_context_stream', fake_stream)

    chunks = []
    async for chunk in service.ask_stream('Alice 喜欢什么？'):
        chunks.append(chunk)

    assert chunks[0]['type'] == 'references'
    assert chunks[1]['content'] == 'Alice '
    assert chunks[-1]['type'] == 'done'
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend
pytest tests/services/test_agent_service.py::test_agent_service_streams_references_then_content -v
```

Expected: FAIL with `AttributeError` for `answer_with_context_stream`

- [ ] **Step 3: Add streaming answer helper**

Add to `backend/app/services/knowledge_graph_service.py`:

```python
async def answer_with_context_stream(self, query: str, retrieval_result: GraphRetrievalResult):
    if not retrieval_result.has_enough_evidence:
        yield {'type': 'content', 'content': '抱歉，我在知识图谱中没有找到足够相关的信息。'}
        yield {'type': 'done', 'content': ''}
        return

    system_prompt = """你是一个知识助手，必须基于给定证据回答问题。
如果证据不足，明确说明，不允许编造。请用中文回答。"""

    user_prompt = f"""【知识图谱上下文】\n{retrieval_result.context}\n\n【用户问题】\n{query}\n\n请基于上述上下文回答问题。"""

    stream = self.llm_client.chat.completions.create(
        model='step-1-8k',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        max_tokens=1024,
        temperature=0.3,
        stream=True,
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield {'type': 'content', 'content': chunk.choices[0].delta.content}

    yield {'type': 'done', 'content': ''}
```

- [ ] **Step 4: Re-run the streaming tests**

Run:

```bash
cd backend
pytest tests/services/test_agent_service.py -v
```

Expected: PASS

- [ ] **Step 5: Run a focused regression suite**

Run:

```bash
cd backend
pytest tests/services/test_graph_retrieval_tool.py tests/services/test_agent_service.py tests/test_chat_api.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/services/knowledge_graph_service.py app/services/agent_service.py tests/services/test_agent_service.py
git commit -m "feat: add streaming support for agentic graph rag"
```

---

## Task 6: Manual Verification and Documentation Notes

**Files:**
- Modify: `backend/RAG_IMPLEMENTATION_SUMMARY.md`
- Test: manual API checks against running backend

- [ ] **Step 1: Update the implementation summary**

Append to `backend/RAG_IMPLEMENTATION_SUMMARY.md`:

```markdown
## Agentic Graph RAG Upgrade

The chat flow now routes through `AgentService`, which enforces strict-mode graph retrieval before answering non-chitchat questions. Graph retrieval is exposed as `graph_retrieval_tool`, while `KnowledgeGraphService` is split into retrieval and answer-generation layers.
```

- [ ] **Step 2: Start the backend locally**

Run:

```bash
cd backend
python -u start.py
```

Expected: FastAPI server starts without import errors

- [ ] **Step 3: Verify non-chitchat agent path**

Run:

```bash
curl -X POST http://localhost:8000/api/chat/rag -H "Content-Type: application/json" -d '{"message":"垃圾收集的时间表是什么？"}'
```

Expected: JSON with `answer` and non-empty `references`

- [ ] **Step 4: Verify chitchat path**

Run:

```bash
curl -X POST http://localhost:8000/api/chat/rag -H "Content-Type: application/json" -d '{"message":"你好"}'
```

Expected: Friendly greeting answer with empty `references`

- [ ] **Step 5: Commit documentation note**

```bash
git add RAG_IMPLEMENTATION_SUMMARY.md
git commit -m "docs: describe strict agentic graph rag flow"
```

---

## Spec Coverage Check

- Agent control layer: covered by Task 4
- Toolized graph retrieval: covered by Task 3
- Split retrieval and answer generation: covered by Task 2
- Strict-mode routing and non-hallucination behavior: covered by Tasks 1 and 4
- Streaming compatibility: covered by Task 5
- P0 logging/verification/regression: covered by Tasks 4, 5, and 6
- P1/P2 ideas are intentionally excluded from implementation tasks in this plan; they remain in the design doc as follow-up roadmap

## Placeholder Scan

- No `TBD`, `TODO`, or unresolved placeholders remain
- Every task lists exact file paths, test commands, and concrete code snippets
- Commit steps are included for each task to preserve frequent checkpoints

## Type Consistency Check

- Tool output type is consistently `GraphRetrievalResult`
- Agent orchestration consistently uses `GraphRetrievalTool.run(...)`
- Chat responses continue to return `ChatResponse(answer=..., references=...)`

