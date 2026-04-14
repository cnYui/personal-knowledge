# Graph History V1 + Overlay Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build V1 of `graph_history_tool` for memory history queries while making dynamic overlay strictly follow current truth and refresh correctly on edit / remove-from-graph / delete.

**Architecture:** Extend the existing graph retrieval stack with a parallel history path: `graph_history_tool` → `GraphHistoryService` → repository methods on `memory_graph_episodes` plus optional Graphiti evidence lookup. Keep default retrieval latest-only via existing `KnowledgeGraphService`, and make overlay generation depend only on current valid graph memories. Add explicit memory graph removal semantics so current truth can shrink without deleting historical rows.

**Tech Stack:** FastAPI, SQLAlchemy ORM, Pydantic, pytest, existing Graphiti client/service stack, existing tool-loop workflow.

---

## Scope Check

The approved spec covers two tightly related subsystems that should still ship together in V1 because neither is complete or testable alone:

1. **History retrieval path**: `graph_history_tool` + `GraphHistoryService` for `target_type=memory`.
2. **Overlay/current-truth lifecycle**: overlay empties or shrinks when current truth changes through edit, remove-from-graph, or delete.

These stay in one plan because the user’s approved V1 explicitly couples “history stays queryable” with “default overlay only summarizes current truth.”

## File Structure

### Files to create

- `backend/app/services/graph_history_service.py`
  - Single-responsibility service for memory-history timeline / compare / summarize orchestration.
- `backend/app/services/agent_tools/graph_history_tool.py`
  - Thin tool wrapper matching the existing `GraphRetrievalTool` pattern.
- `backend/tests/services/test_graph_history_service.py`
  - Service-level tests for timeline / compare / summarize behavior and error states.
- `backend/tests/services/test_graph_history_tool.py`
  - Tool wrapper tests ensuring input is passed through and output is returned unchanged.
- `backend/tests/services/test_memory_service_graph_lifecycle.py`
  - Unit tests for edit / remove-from-graph / delete refresh trigger behavior.

### Files to modify

- `backend/app/schemas/agent.py`
  - Add structured Pydantic models for history tool input/output.
- `backend/app/repositories/memory_graph_episode_repository.py`
  - Add query helpers for memory version timeline and latest/current lookups.
- `backend/app/services/agent_tools/__init__.py`
  - Export the new history tool.
- `backend/app/services/memory_service.py`
  - Inject profile refresh scheduler and episode repository hooks; add remove-from-graph method; refresh overlay on current-truth changes.
- `backend/app/routers/memories.py`
  - Add remove-from-graph endpoint and wire updated service construction.
- `backend/app/schemas/graph.py`
  - Add response schema for remove-from-graph endpoint if no reusable schema exists.
- `backend/app/services/agent_knowledge_profile_refresh.py`
  - Limit overlay candidate extraction to current-truth memories only, and short-circuit to empty overlay when none exist.
- `backend/app/services/agent_knowledge_profile_service.py`
  - Keep composition behavior but add tests around empty-overlay semantics if needed.
- `backend/app/workflow/nodes/agent_node.py`
  - Register a second tool schema for `graph_history_tool` and extend tool routing instructions.
- `backend/app/workflow/canvas_factory.py`
  - Lazily construct and inject `GraphHistoryTool` alongside `GraphRetrievalTool`.
- `backend/tests/repositories/test_memory_graph_episode_repository.py`
  - Add tests for new repository query helpers.
- `backend/tests/services/test_agent_knowledge_profile_refresh.py`
  - Add coverage proving overlay generation ignores non-current memories and becomes empty when current truth is empty.
- `backend/tests/services/test_agent_knowledge_profile_service.py`
  - Add assertions that blank rendered overlay does not alter base prompt.
- `backend/tests/test_memories_graph.py`
  - Add API tests for remove-from-graph endpoint.
- `backend/tests/workflow/...`
  - Update or add focused workflow tests for dual-tool registration if there is already a nearby agent-node/tool-loop test file.

### Files to inspect while implementing

- `backend/app/services/knowledge_graph_service.py`
- `backend/app/services/agent_tools/graph_retrieval_tool.py`
- `backend/app/workflow/engine/tool_loop.py`
- `backend/app/services/agent_knowledge_profile_refresh.py`
- `backend/app/workers/graphiti_ingest_worker.py`
- `docs/superpowers/specs/2026-04-06-graph-history-tool-and-overlay-lifecycle-design.md`

## Implementation Notes Before Starting

- Reuse current naming conventions: service classes in `app/services`, thin wrappers in `app/services/agent_tools`, Pydantic models in `app/schemas/agent.py`.
- Keep V1 narrow:
  - only `target_type="memory"`
  - only `mode in {"timeline", "compare", "summarize"}`
  - only `memory_id` as authoritative `target_value`
- Do **not** implement entity-history, relation/topic-history, or physical Graphiti deletion in this plan.
- For deleted memories in V1, history rows may remain in storage, but business-level history queries should return `not_found` once the memory row is gone.
- For remove-from-graph, keep memory row and historical episode rows, but demote current truth by marking the memory as no longer graph-active and clearing current graph pointers.

---

### Task 1: Add history tool schemas

**Files:**
- Modify: `backend/app/schemas/agent.py`
- Test: `backend/tests/services/test_graph_history_tool.py`

- [ ] **Step 1: Write the failing schema test**

```python
from app.schemas.agent import GraphHistoryQuery, GraphHistoryResult


def test_graph_history_query_and_result_defaults():
    query = GraphHistoryQuery(target_type='memory', target_value='memory-1', mode='timeline', question='它怎么变过？')
    result = GraphHistoryResult(target_type='memory', target_value='memory-1', mode='timeline', status='ok')

    assert query.constraints == {}
    assert result.timeline == []
    assert result.comparisons == []
    assert result.summary == ''
    assert result.evidence == []
    assert result.warnings == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_graph_history_tool.py::test_graph_history_query_and_result_defaults -v`
Expected: FAIL with `ImportError` or missing `GraphHistoryQuery` / `GraphHistoryResult`.

- [ ] **Step 3: Write minimal schema implementation**

```python
from typing import Any, Literal

from pydantic import BaseModel, Field


class GraphHistoryQuery(BaseModel):
    target_type: Literal['memory', 'entity', 'relation_topic']
    target_value: str
    mode: Literal['timeline', 'compare', 'summarize']
    question: str = ''
    constraints: dict[str, Any] = Field(default_factory=dict)


class GraphHistoryResolvedTarget(BaseModel):
    memory_id: str | None = None
    memory_title: str | None = None
    latest_version: int | None = None
    version_count: int = 0


class GraphHistoryTimelineItem(BaseModel):
    version: int
    is_latest: bool
    reference_time: str | None = None
    created_at: str | None = None
    episode_count: int = 0
    summary_excerpt: str = ''


class GraphHistoryComparisonItem(BaseModel):
    from_version: int
    to_version: int
    change_summary: str
    added_points: list[str] = Field(default_factory=list)
    removed_points: list[str] = Field(default_factory=list)
    updated_points: list[str] = Field(default_factory=list)


class GraphHistoryEvidenceItem(BaseModel):
    version: int | None = None
    episode_uuid: str = ''
    fact: str = ''
    reference_time: str | None = None


class GraphHistoryResult(BaseModel):
    target_type: Literal['memory', 'entity', 'relation_topic']
    target_value: str
    resolved_target: GraphHistoryResolvedTarget | None = None
    mode: Literal['timeline', 'compare', 'summarize']
    status: Literal['ok', 'not_found', 'insufficient_history', 'unsupported_target_type', 'error']
    timeline: list[GraphHistoryTimelineItem] = Field(default_factory=list)
    comparisons: list[GraphHistoryComparisonItem] = Field(default_factory=list)
    summary: str = ''
    evidence: list[GraphHistoryEvidenceItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/services/test_graph_history_tool.py::test_graph_history_query_and_result_defaults -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/agent.py backend/tests/services/test_graph_history_tool.py
git commit -m "feat: add graph history schemas"
```

### Task 2: Add repository helpers for memory history timeline

**Files:**
- Modify: `backend/app/repositories/memory_graph_episode_repository.py`
- Test: `backend/tests/repositories/test_memory_graph_episode_repository.py`

- [ ] **Step 1: Write the failing repository tests**

```python
def test_list_versions_for_memory_returns_grouped_latest_first(db_session):
    repo = MemoryGraphEpisodeRepository()
    memory = Memory(title='Versioned', title_status='ready', content='Body', group_id='default')
    db_session.add(memory)
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v1-0', version=1, chunk_index=0, is_latest=False),
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v2-0', version=2, chunk_index=0, is_latest=True),
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v2-1', version=2, chunk_index=1, is_latest=True),
        ]
    )
    db_session.commit()

    versions = repo.list_versions_for_memory(db_session, memory.id)

    assert [item['version'] for item in versions] == [2, 1]
    assert versions[0]['episode_count'] == 2
    assert versions[0]['is_latest'] is True


def test_get_version_rows_for_memory_returns_specific_version_rows(db_session):
    repo = MemoryGraphEpisodeRepository()
    memory = Memory(title='Versioned', title_status='ready', content='Body', group_id='default')
    db_session.add(memory)
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v1-0', version=1, chunk_index=0, is_latest=False),
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v2-0', version=2, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    rows = repo.get_version_rows_for_memory(db_session, memory.id, 1)

    assert [row.episode_uuid for row in rows] == ['ep-v1-0']
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/repositories/test_memory_graph_episode_repository.py -v`
Expected: FAIL with missing repository methods.

- [ ] **Step 3: Write minimal repository implementation**

```python
from sqlalchemy import func, select, update


def list_versions_for_memory(self, db: Session, memory_id: str) -> list[dict]:
    rows = db.execute(
        select(
            MemoryGraphEpisode.version,
            func.max(MemoryGraphEpisode.is_latest.cast(Integer)).label('is_latest'),
            func.max(MemoryGraphEpisode.reference_time).label('reference_time'),
            func.max(MemoryGraphEpisode.created_at).label('created_at'),
            func.count(MemoryGraphEpisode.id).label('episode_count'),
        )
        .where(MemoryGraphEpisode.memory_id == memory_id)
        .group_by(MemoryGraphEpisode.version)
        .order_by(MemoryGraphEpisode.version.desc())
    )
    return [
        {
            'version': item.version,
            'is_latest': bool(item.is_latest),
            'reference_time': item.reference_time,
            'created_at': item.created_at,
            'episode_count': int(item.episode_count or 0),
        }
        for item in rows
    ]


def get_version_rows_for_memory(self, db: Session, memory_id: str, version: int) -> list[MemoryGraphEpisode]:
    return list(
        db.scalars(
            select(MemoryGraphEpisode)
            .where(MemoryGraphEpisode.memory_id == memory_id, MemoryGraphEpisode.version == version)
            .order_by(MemoryGraphEpisode.chunk_index.asc())
        )
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/repositories/test_memory_graph_episode_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/memory_graph_episode_repository.py backend/tests/repositories/test_memory_graph_episode_repository.py
git commit -m "feat: add memory history repository queries"
```

### Task 3: Implement `GraphHistoryService`

**Files:**
- Create: `backend/app/services/graph_history_service.py`
- Test: `backend/tests/services/test_graph_history_service.py`

- [ ] **Step 1: Write the failing service tests**

```python
def test_get_memory_timeline_returns_ok_result_with_resolved_target(db_session):
    service = GraphHistoryService(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
        db_factory=lambda: db_session,
    )
    memory = Memory(title='Python Note', title_status='ready', content='v2 body', group_id='default')
    db_session.add(memory)
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v1', version=1, chunk_index=0, is_latest=False),
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v2', version=2, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    result = service.query(
        GraphHistoryQuery(target_type='memory', target_value=memory.id, mode='timeline', question='它如何变化？')
    )

    assert result.status == 'ok'
    assert result.resolved_target.memory_id == memory.id
    assert [item.version for item in result.timeline] == [2, 1]


def test_compare_requires_at_least_two_versions(db_session):
    service = GraphHistoryService(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
        db_factory=lambda: db_session,
    )
    memory = Memory(title='Single', title_status='ready', content='only body', group_id='default')
    db_session.add(memory)
    db_session.commit()
    db_session.add(MemoryGraphEpisode(memory_id=memory.id, episode_uuid='ep-v1', version=1, chunk_index=0, is_latest=True))
    db_session.commit()

    result = service.query(
        GraphHistoryQuery(target_type='memory', target_value=memory.id, mode='compare', question='最新和上一个有什么不同？')
    )

    assert result.status == 'insufficient_history'
    assert result.comparisons == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_graph_history_service.py -v`
Expected: FAIL with missing `GraphHistoryService`.

- [ ] **Step 3: Write minimal service implementation**

```python
from dataclasses import dataclass

from app.core.database import SessionLocal
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository
from app.repositories.memory_repository import MemoryRepository
from app.schemas.agent import (
    GraphHistoryComparisonItem,
    GraphHistoryQuery,
    GraphHistoryResolvedTarget,
    GraphHistoryResult,
    GraphHistoryTimelineItem,
)


class GraphHistoryService:
    def __init__(
        self,
        *,
        memory_repository: MemoryRepository | None = None,
        episode_repository: MemoryGraphEpisodeRepository | None = None,
        db_factory=None,
    ) -> None:
        self.memory_repository = memory_repository or MemoryRepository()
        self.episode_repository = episode_repository or MemoryGraphEpisodeRepository()
        self.db_factory = db_factory or SessionLocal

    def query(self, payload: GraphHistoryQuery) -> GraphHistoryResult:
        if payload.target_type != 'memory':
            return GraphHistoryResult(
                target_type=payload.target_type,
                target_value=payload.target_value,
                mode=payload.mode,
                status='unsupported_target_type',
            )

        db = self.db_factory()
        try:
            memory = self.memory_repository.get(db, payload.target_value)
            if memory is None:
                return GraphHistoryResult(
                    target_type='memory',
                    target_value=payload.target_value,
                    mode=payload.mode,
                    status='not_found',
                )

            versions = self.episode_repository.list_versions_for_memory(db, memory.id)
            resolved_target = GraphHistoryResolvedTarget(
                memory_id=memory.id,
                memory_title=memory.title,
                latest_version=versions[0]['version'] if versions else None,
                version_count=len(versions),
            )

            timeline = [
                GraphHistoryTimelineItem(
                    version=item['version'],
                    is_latest=item['is_latest'],
                    reference_time=item['reference_time'].isoformat() if item['reference_time'] else None,
                    created_at=item['created_at'].isoformat() if item['created_at'] else None,
                    episode_count=item['episode_count'],
                    summary_excerpt=f"{memory.title} v{item['version']}",
                )
                for item in versions
            ]

            if payload.mode == 'timeline':
                return GraphHistoryResult(
                    target_type='memory',
                    target_value=payload.target_value,
                    mode='timeline',
                    status='ok',
                    resolved_target=resolved_target,
                    timeline=timeline,
                )

            if len(versions) < 2:
                return GraphHistoryResult(
                    target_type='memory',
                    target_value=payload.target_value,
                    mode=payload.mode,
                    status='insufficient_history',
                    resolved_target=resolved_target,
                    timeline=timeline,
                    warnings=['该 memory 只有一个版本，无法进行历史比较。'],
                )

            latest_version = versions[0]['version']
            previous_version = versions[1]['version']
            comparison = GraphHistoryComparisonItem(
                from_version=previous_version,
                to_version=latest_version,
                change_summary=f'从 v{previous_version} 演进到 v{latest_version}',
                added_points=[f'当前标题：{memory.title}'],
                removed_points=[],
                updated_points=[],
            )

            if payload.mode == 'compare':
                return GraphHistoryResult(
                    target_type='memory',
                    target_value=payload.target_value,
                    mode='compare',
                    status='ok',
                    resolved_target=resolved_target,
                    timeline=timeline,
                    comparisons=[comparison],
                )

            return GraphHistoryResult(
                target_type='memory',
                target_value=payload.target_value,
                mode='summarize',
                status='ok',
                resolved_target=resolved_target,
                timeline=timeline,
                comparisons=[comparison],
                summary=f'{memory.title} 共经历 {len(versions)} 个版本，当前为 v{latest_version}。',
            )
        finally:
            close = getattr(db, 'close', None)
            if callable(close):
                close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_graph_history_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_service.py backend/tests/services/test_graph_history_service.py
git commit -m "feat: add graph history service mvp"
```

### Task 4: Add thin `graph_history_tool` wrapper

**Files:**
- Create: `backend/app/services/agent_tools/graph_history_tool.py`
- Modify: `backend/app/services/agent_tools/__init__.py`
- Test: `backend/tests/services/test_graph_history_tool.py`

- [ ] **Step 1: Write the failing tool wrapper test**

```python
def test_graph_history_tool_delegates_to_service():
    captured = {}

    class StubService:
        def query(self, payload):
            captured['payload'] = payload
            return GraphHistoryResult(
                target_type='memory',
                target_value='memory-1',
                mode='timeline',
                status='ok',
            )

    tool = GraphHistoryTool(history_service=StubService())
    result = tool.run(target_type='memory', target_value='memory-1', mode='timeline', question='它怎么变过？')

    assert captured['payload'].target_value == 'memory-1'
    assert result.status == 'ok'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_graph_history_tool.py::test_graph_history_tool_delegates_to_service -v`
Expected: FAIL with missing `GraphHistoryTool`.

- [ ] **Step 3: Write minimal wrapper implementation**

```python
from app.schemas.agent import GraphHistoryQuery, GraphHistoryResult
from app.services.graph_history_service import GraphHistoryService


class GraphHistoryTool:
    name = 'graph_history_tool'
    description = 'Retrieve structured history evidence for a memory from versioned graph knowledge.'

    def __init__(self, history_service: GraphHistoryService | None = None) -> None:
        self.history_service = history_service or GraphHistoryService()

    def run(
        self,
        target_type: str,
        target_value: str,
        mode: str,
        question: str = '',
        constraints: dict | None = None,
    ) -> GraphHistoryResult:
        return self.history_service.query(
            GraphHistoryQuery(
                target_type=target_type,
                target_value=target_value,
                mode=mode,
                question=question,
                constraints=constraints or {},
            )
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_graph_history_tool.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent_tools/graph_history_tool.py backend/app/services/agent_tools/__init__.py backend/tests/services/test_graph_history_tool.py
git commit -m "feat: add graph history tool"
```

### Task 5: Register the history tool in agent workflow

**Files:**
- Modify: `backend/app/workflow/canvas_factory.py`
- Modify: `backend/app/workflow/nodes/agent_node.py`
- Test: `backend/tests/workflow/test_agent_node_history_tool.py`

- [ ] **Step 1: Write the failing workflow test**

```python
@pytest.mark.asyncio
async def test_agent_node_exposes_both_graph_tools():
    node = AgentNode(
        config={},
        graph_retrieval_tool=GraphRetrievalTool(knowledge_graph_service=StubRetrievalService()),
        graph_history_tool=GraphHistoryTool(history_service=StubHistoryService()),
        canvas=StubCanvas(),
        llm_client=StubLLMClient(),
    )

    schema = node._tool_schemas()

    assert {item['function']['name'] for item in schema} == {'graph_retrieval_tool', 'graph_history_tool'}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/workflow/test_agent_node_history_tool.py -v`
Expected: FAIL because `AgentNode` only exposes one tool schema.

- [ ] **Step 3: Implement minimal dual-tool registration**

```python
from app.services.agent_tools.graph_history_tool import GraphHistoryTool


def __init__(..., graph_history_tool: GraphHistoryTool | None = None, ...):
    self.graph_history_tool = graph_history_tool


def _get_graph_history_tool(self) -> GraphHistoryTool:
    if self.graph_history_tool is None:
        self.graph_history_tool = GraphHistoryTool()
    return self.graph_history_tool


def _tool_schemas(self) -> list[dict[str, Any]]:
    return [
        {
            'type': 'function',
            'function': {
                'name': 'graph_retrieval_tool',
                'description': '检索当前有效知识。',
                'parameters': {...},
            },
        },
        {
            'type': 'function',
            'function': {
                'name': 'graph_history_tool',
                'description': '检索某条记忆的历史版本与变化。',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'target_type': {'type': 'string', 'enum': ['memory']},
                        'target_value': {'type': 'string'},
                        'mode': {'type': 'string', 'enum': ['timeline', 'compare', 'summarize']},
                        'question': {'type': 'string'},
                    },
                    'required': ['target_type', 'target_value', 'mode'],
                },
            },
        },
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/workflow/test_agent_node_history_tool.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/workflow/canvas_factory.py backend/app/workflow/nodes/agent_node.py backend/tests/workflow/test_agent_node_history_tool.py
git commit -m "feat: register graph history tool in agent workflow"
```

### Task 6: Make overlay extraction depend on current truth only

**Files:**
- Modify: `backend/app/services/agent_knowledge_profile_refresh.py`
- Test: `backend/tests/services/test_agent_knowledge_profile_refresh.py`

- [ ] **Step 1: Write the failing refresh tests**

```python
@pytest.mark.asyncio
async def test_refresh_uses_only_current_truth_memories(monkeypatch, db_session):
    current_memory = Memory(title='Current', title_status='ready', content='body', group_id='default', graph_status='added')
    stale_memory = Memory(title='Stale', title_status='ready', content='body', group_id='default', graph_status='not_added')
    db_session.add_all([current_memory, stale_memory])
    db_session.commit()

    service = AgentKnowledgeProfileRefreshService(
        memory_repository=MemoryRepository(),
        session_factory=lambda: db_session,
        llm_client=StubProfileLLM(),
    )

    candidates = await service._extract_candidates()

    assert 'Current' in candidates.recent_titles
    assert 'Stale' not in candidates.recent_titles


@pytest.mark.asyncio
async def test_refresh_renders_empty_overlay_when_no_current_truth(monkeypatch, db_session):
    service = AgentKnowledgeProfileRefreshService(
        memory_repository=MemoryRepository(),
        session_factory=lambda: db_session,
        llm_client=StubProfileLLM(),
    )

    await service.refresh_global_profile()

    latest = AgentKnowledgeProfileRepository().get_latest_ready_profile(db_session)
    assert latest.rendered_overlay == ''
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_agent_knowledge_profile_refresh.py -v`
Expected: FAIL because refresh still reads recent graph-added data loosely and always renders a non-empty scaffold.

- [ ] **Step 3: Implement minimal current-truth-only refresh logic**

```python
async def _extract_candidates(self) -> ProfileCandidateSummary:
    db = self.session_factory()
    try:
        recent_memories = self.memory_repository.list_recent_graph_added(db, limit=RECENT_MEMORY_LIMIT)
        recent_memories = [memory for memory in recent_memories if memory.graph_status == 'added']
    finally:
        db.close()

    if not recent_memories:
        return ProfileCandidateSummary(top_entities=[], top_relations=[], recent_entities=[], recent_titles=[])

    ...


def _render_overlay(self, profile: dict[str, list[str]]) -> str:
    if not any(profile.get(key) for key in ('major_topics', 'high_frequency_entities', 'high_frequency_relations', 'recent_focuses')):
        return ''
    sections = [...]
    return '\n'.join(sections)


async def refresh_global_profile(self) -> None:
    ...
    candidates = await self._extract_candidates()
    if not any([candidates.top_entities, candidates.top_relations, candidates.recent_entities, candidates.recent_titles]):
        profile_data = {
            'major_topics': [],
            'high_frequency_entities': [],
            'high_frequency_relations': [],
            'recent_focuses': [],
        }
        rendered_overlay = ''
    else:
        profile_data = await self._compress_profile(candidates)
        rendered_overlay = self._render_overlay(profile_data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_agent_knowledge_profile_refresh.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent_knowledge_profile_refresh.py backend/tests/services/test_agent_knowledge_profile_refresh.py
git commit -m "fix: bind overlay refresh to current truth only"
```

### Task 7: Add remove-from-graph semantics and refresh triggers in `MemoryService`

**Files:**
- Modify: `backend/app/services/memory_service.py`
- Test: `backend/tests/services/test_memory_service_graph_lifecycle.py`

- [ ] **Step 1: Write the failing service lifecycle tests**

```python
@pytest.mark.asyncio
async def test_update_memory_resets_current_truth_and_requests_overlay_refresh(db_session):
    scheduler = StubScheduler()
    memory = Memory(title='Old', title_status='ready', content='Body', group_id='default', graph_status='added')
    db_session.add(memory)
    db_session.commit()

    service = MemoryService(repository=MemoryRepository(), profile_refresh_scheduler=scheduler)
    service.update_memory(db_session, memory.id, MemoryUpdate(title='New'))

    refreshed = db_session.get(Memory, memory.id)
    assert refreshed.graph_status == 'not_added'
    assert scheduler.reasons == ['memory_edited_current_truth_changed']


@pytest.mark.asyncio
async def test_remove_from_graph_keeps_memory_but_clears_graph_current_truth(db_session):
    scheduler = StubScheduler()
    memory = Memory(title='Keep me', title_status='ready', content='Body', group_id='default', graph_status='added', graph_episode_uuid='ep-1')
    db_session.add(memory)
    db_session.commit()

    service = MemoryService(repository=MemoryRepository(), profile_refresh_scheduler=scheduler)
    result = service.remove_from_graph(db_session, memory.id)

    assert result.graph_status == 'not_added'
    assert result.graph_episode_uuid is None
    assert scheduler.reasons == ['memory_removed_from_graph']
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_memory_service_graph_lifecycle.py -v`
Expected: FAIL because `MemoryService` lacks scheduler injection and `remove_from_graph`.

- [ ] **Step 3: Implement minimal lifecycle logic**

```python
from app.services.agent_knowledge_profile_refresh import agent_knowledge_profile_refresh_scheduler


class MemoryService:
    def __init__(
        self,
        repository: MemoryRepository | None = None,
        *,
        profile_refresh_scheduler=None,
    ) -> None:
        self.repository = repository or MemoryRepository()
        self.profile_refresh_scheduler = profile_refresh_scheduler or agent_knowledge_profile_refresh_scheduler

    def update_memory(self, db: Session, memory_id: str, payload: MemoryUpdate):
        ...
        if has_graph_relevant_change:
            memory.graph_status = 'not_added'
            memory.graph_error = None
            memory.graph_episode_uuid = None
            memory.graph_added_at = None
            self.profile_refresh_scheduler.request_refresh(reason='memory_edited_current_truth_changed')
        return self.repository.update(db, memory, payload)

    def remove_from_graph(self, db: Session, memory_id: str):
        memory = self.get_memory(db, memory_id)
        memory.graph_status = 'not_added'
        memory.graph_error = None
        memory.graph_episode_uuid = None
        memory.graph_added_at = None
        db.commit()
        db.refresh(memory)
        self.profile_refresh_scheduler.request_refresh(reason='memory_removed_from_graph')
        return memory

    def delete_memory(self, db: Session, memory_id: str) -> None:
        memory = self.get_memory(db, memory_id)
        self.repository.delete(db, memory)
        self.profile_refresh_scheduler.request_refresh(reason='memory_deleted')
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_memory_service_graph_lifecycle.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/memory_service.py backend/tests/services/test_memory_service_graph_lifecycle.py
git commit -m "feat: add memory graph lifecycle refresh hooks"
```

### Task 8: Expose remove-from-graph API endpoint

**Files:**
- Modify: `backend/app/routers/memories.py`
- Modify: `backend/app/schemas/graph.py`
- Test: `backend/tests/test_memories_graph.py`

- [ ] **Step 1: Write the failing API test**

```python
def test_remove_memory_from_graph(client_with_worker):
    client = client_with_worker
    create_response = client.post(
        '/api/memories',
        json={
            'title': 'Graph Memory',
            'content': 'Body',
            'group_id': 'default',
            'title_status': 'ready',
        },
    )
    memory_id = create_response.json()['id']
    client.post(f'/api/memories/{memory_id}/add-to-graph')

    response = client.post(f'/api/memories/{memory_id}/remove-from-graph')

    assert response.status_code == 200
    assert response.json()['graph_status'] == 'not_added'
    assert response.json()['memory_id'] == memory_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_memories_graph.py::test_remove_memory_from_graph -v`
Expected: FAIL with 404 because endpoint does not exist.

- [ ] **Step 3: Implement minimal endpoint and schema**

```python
class RemoveFromGraphResponse(BaseModel):
    message: str
    memory_id: str
    graph_status: str


@router.post('/{memory_id}/remove-from-graph', response_model=RemoveFromGraphResponse)
def remove_memory_from_graph(memory_id: str, db: Session = Depends(get_db)) -> RemoveFromGraphResponse:
    memory = service.remove_from_graph(db, memory_id)
    return RemoveFromGraphResponse(
        message='Memory removed from current graph knowledge',
        memory_id=memory.id,
        graph_status=memory.graph_status,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/test_memories_graph.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/memories.py backend/app/schemas/graph.py backend/tests/test_memories_graph.py
git commit -m "feat: add remove-from-graph api"
```

### Task 9: Tighten agent prompt composition tests around blank overlay

**Files:**
- Modify: `backend/tests/services/test_agent_knowledge_profile_service.py`

- [ ] **Step 1: Write the failing regression test**

```python
def test_compose_system_prompt_ignores_blank_overlay_snapshot():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        repo = AgentKnowledgeProfileRepository()
        profile = repo.create_building_profile(db)
        repo.mark_profile_ready(
            db,
            profile,
            major_topics=[],
            high_frequency_entities=[],
            high_frequency_relations=[],
            recent_focuses=[],
            rendered_overlay='   ',
        )
    finally:
        db.close()

    service = AgentKnowledgeProfileService(repository=AgentKnowledgeProfileRepository(), session_factory=TestingSessionLocal)
    assert service.compose_system_prompt('base prompt') == 'base prompt'
```

- [ ] **Step 2: Run test to verify it fails if whitespace is not normalized correctly**

Run: `pytest backend/tests/services/test_agent_knowledge_profile_service.py::test_compose_system_prompt_ignores_blank_overlay_snapshot -v`
Expected: PASS or FAIL. If it already passes, keep the test as a guard and proceed without production code change.

- [ ] **Step 3: Apply the smallest needed code change**

```python
def get_latest_ready_overlay(self) -> str:
    snapshot = self.get_latest_ready_snapshot()
    if snapshot is None:
        return ''
    return snapshot.rendered_overlay.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_agent_knowledge_profile_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/services/test_agent_knowledge_profile_service.py backend/app/services/agent_knowledge_profile_service.py
git commit -m "test: guard blank overlay prompt composition"
```

### Task 10: Add end-to-end-ish history tool tests and targeted workflow coverage

**Files:**
- Modify: `backend/tests/services/test_graph_history_tool.py`
- Modify: `backend/tests/workflow/test_agent_node_history_tool.py`

- [ ] **Step 1: Write the failing integration-shaped tests**

```python
def test_graph_history_tool_returns_not_found_for_deleted_memory():
    service = GraphHistoryService(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
        db_factory=lambda: db_session,
    )
    tool = GraphHistoryTool(history_service=service)

    result = tool.run(target_type='memory', target_value='missing-memory', mode='timeline', question='它怎么变化？')

    assert result.status == 'not_found'


@pytest.mark.asyncio
async def test_agent_node_tool_registry_contains_history_tool_when_running():
    ...
    assert 'graph_history_tool' in registered_names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_graph_history_tool.py backend/tests/workflow/test_agent_node_history_tool.py -v`
Expected: FAIL if wiring gaps remain.

- [ ] **Step 3: Fill the smallest missing gaps**

```python
# Ensure canvas_factory passes graph_history_tool into AgentNode
agent_node = AgentNode(
    ...,
    graph_history_tool=graph_history_tool,
)

# Ensure agent node tool registry includes both tool instances
tool_registry = {
    graph_tool.name: graph_tool,
    history_tool.name: history_tool,
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_graph_history_tool.py backend/tests/workflow/test_agent_node_history_tool.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/services/test_graph_history_tool.py backend/tests/workflow/test_agent_node_history_tool.py backend/app/workflow/canvas_factory.py backend/app/workflow/nodes/agent_node.py
git commit -m "test: cover graph history tool workflow integration"
```

### Task 11: Run focused verification suite

**Files:**
- Test only; no code changes required unless failures are found.

- [ ] **Step 1: Run repository and service tests**

Run: `pytest backend/tests/repositories/test_memory_graph_episode_repository.py backend/tests/services/test_graph_history_service.py backend/tests/services/test_graph_history_tool.py backend/tests/services/test_memory_service_graph_lifecycle.py backend/tests/services/test_agent_knowledge_profile_refresh.py backend/tests/services/test_agent_knowledge_profile_service.py -v`
Expected: PASS

- [ ] **Step 2: Run API and workflow tests**

Run: `pytest backend/tests/test_memories_graph.py backend/tests/workflow/test_agent_node_history_tool.py -v`
Expected: PASS

- [ ] **Step 3: Run a final narrow regression around existing retrieval**

Run: `pytest backend/tests/services/test_graph_retrieval_tool.py -v`
Expected: PASS

- [ ] **Step 4: If anything fails, fix with smallest change and rerun only the failing tests first**

```bash
pytest <failing-test-node> -v
```

- [ ] **Step 5: Commit verification-stable state**

```bash
git add backend
git commit -m "test: verify graph history v1 and overlay lifecycle"
```

### Task 12: Update docs after code lands

**Files:**
- Modify: `docs/superpowers/specs/2026-04-06-graph-history-tool-and-overlay-lifecycle-design.md`
- Optionally modify: `backend/README_GRAPHITI.md`

- [ ] **Step 1: Add implementation status notes to the spec**

```md
## Implementation Status

- [x] V1 memory-history tool added
- [x] overlay now follows current truth only
- [x] remove-from-graph endpoint added
- [ ] entity-history remains future work
- [ ] relation/topic-history remains future work
```

- [ ] **Step 2: Document the new API/tool behavior**

```md
### V1 Runtime Behavior

- default graph retrieval continues to use latest-only current truth
- `graph_history_tool` supports `target_type=memory`
- `POST /api/memories/{memory_id}/remove-from-graph` removes a memory from current truth without deleting the memory row
```

- [ ] **Step 3: Run docs grep for consistency**

Run: `python -c "from pathlib import Path; text=Path('docs/superpowers/specs/2026-04-06-graph-history-tool-and-overlay-lifecycle-design.md').read_text(encoding='utf-8'); print('graph_history_tool' in text and 'remove-from-graph' in text)"`
Expected: `True`

- [ ] **Step 4: Review git diff for docs only**

Run: `git diff -- docs/superpowers/specs/2026-04-06-graph-history-tool-and-overlay-lifecycle-design.md backend/README_GRAPHITI.md`
Expected: shows only the intended documentation updates.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-04-06-graph-history-tool-and-overlay-lifecycle-design.md backend/README_GRAPHITI.md
git commit -m "docs: record graph history v1 rollout behavior"
```

---

## Self-Review

### 1. Spec coverage

- **Current Truth vs History Truth split** → Tasks 6, 7, 8, 9
- **`graph_history_tool` for memory history** → Tasks 1, 3, 4, 5, 10
- **Modes: timeline / compare / summarize** → Task 3
- **Overlay only summarizes current truth** → Task 6
- **Edit / remove-from-graph / delete semantics** → Task 7 and Task 8
- **Agent tool-calling strategy** → Task 5 and Task 10
- **V1 only, not V2/V3** → enforced in scope check and implementation notes

No spec gaps found for V1 scope.

### 2. Placeholder scan

- Removed generic “write tests” phrasing and replaced it with concrete test names.
- All code-changing steps include concrete code blocks.
- All run steps include explicit commands and expected outcomes.

### 3. Type consistency

- `GraphHistoryQuery`, `GraphHistoryResult`, `GraphHistoryTool`, and `GraphHistoryService` names are consistent across all tasks.
- `target_type`, `target_value`, `mode`, and `question` names match the approved spec.
- `remove_from_graph` naming is consistent across service, router, and tests.

No naming inconsistencies found.