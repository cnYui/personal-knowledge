# Graph History V2/V3 Mainline Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the missing Graph History V2 entity-history flow and V3 minimal relation/topic + planner orchestration flow from the worktree into the main workspace without breaking the existing V1 memory-history behavior.

**Architecture:** Extend the existing graph history schema and service in place, then add focused helper services for entity resolution, entity aggregation, relation/topic resolution, and history intent planning. Wire the new history tool path into the agent workflow and canvas factory, then verify with service, tool, and workflow tests.

**Tech Stack:** Python, Pydantic, SQLAlchemy, pytest

---

## File map

### Create
- `backend/app/services/graph_history_entity_resolver.py` — entity name/alias resolution for V2
- `backend/app/services/graph_history_entity_aggregator.py` — cross-memory entity event aggregation for V2
- `backend/app/services/graph_history_relation_topic_resolver.py` — minimal relation/topic target resolution for V3
- `backend/app/services/history_query_planner.py` — classify query into current-only/history-only/mixed
- `backend/tests/services/test_graph_history_entity_resolver.py`
- `backend/tests/services/test_graph_history_entity_aggregator.py`
- `backend/tests/services/test_graph_history_relation_topic_resolver.py`
- `backend/tests/services/test_history_query_planner.py`
- `backend/tests/workflow/test_agent_history_orchestration.py`

### Modify
- `backend/app/schemas/agent.py` — extend graph history models and statuses
- `backend/app/repositories/memory_repository.py` — add entity lookup helpers
- `backend/app/repositories/memory_graph_episode_repository.py` — add multi-memory version helpers
- `backend/app/services/graph_history_service.py` — add entity and relation/topic branches
- `backend/app/services/agent_tools/graph_history_tool.py` — update description/contract wording only as needed
- `backend/app/workflow/nodes/agent_node.py` — expose graph history tool and minimal planner-aware orchestration
- `backend/app/workflow/canvas_factory.py` — inject graph history tool into agent nodes
- `backend/tests/services/test_graph_history_service.py` — extend for V2/V3 coverage
- `backend/tests/services/test_graph_history_tool.py` — extend for entity/relation passthrough coverage

---

### Task 1: Extend graph history schema for V2/V3 result contracts

**Files:**
- Modify: `backend/app/schemas/agent.py`
- Test: `backend/tests/services/test_graph_history_tool.py`

- [ ] **Step 1: Write the failing test for new status and target coverage**

```python
from app.schemas.agent import GraphHistoryQuery, GraphHistoryResolvedTarget, GraphHistoryResult


def test_graph_history_schema_supports_entity_and_relation_topic_fields():
    query = GraphHistoryQuery(
        target_type='relation_topic',
        target_value='合作关系',
        mode='summarize',
        constraints={'source_entity': 'OpenAI'},
    )
    resolved = GraphHistoryResolvedTarget(
        canonical_name='OpenAI',
        matched_alias='openai',
        candidate_count=1,
        entity_id='entity-openai',
    )
    result = GraphHistoryResult(
        target_type='entity',
        target_value='OpenAI',
        mode='timeline',
        status='ambiguous_target',
        resolved_target=resolved,
        warnings=['need disambiguation'],
    )

    assert query.target_type == 'relation_topic'
    assert result.status == 'ambiguous_target'
    assert result.resolved_target.entity_id == 'entity-openai'
```

- [ ] **Step 2: Run test to verify it fails if schema is incomplete**

Run: `python -m pytest backend/tests/services/test_graph_history_tool.py -k schema_supports_entity_and_relation_topic_fields -v`
Expected: FAIL with validation or missing field error before schema updates.

- [ ] **Step 3: Update the schema with the minimal new fields and statuses**

```python
class GraphHistoryResolvedTarget(BaseModel):
    memory_id: str | None = None
    memory_title: str | None = None
    latest_version: int | None = None
    version_count: int = 0
    entity_id: str | None = None
    canonical_name: str | None = None
    matched_alias: str | None = None
    candidate_count: int = 0


class GraphHistoryResult(BaseModel):
    target_type: Literal['memory', 'entity', 'relation_topic']
    target_value: str
    resolved_target: GraphHistoryResolvedTarget | None = None
    mode: Literal['timeline', 'compare', 'summarize']
    status: Literal[
        'ok',
        'not_found',
        'insufficient_history',
        'unsupported_target_type',
        'insufficient_evidence',
        'ambiguous_target',
        'error',
    ]
```

- [ ] **Step 4: Run the schema coverage test again**

Run: `python -m pytest backend/tests/services/test_graph_history_tool.py -k schema_supports_entity_and_relation_topic_fields -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/agent.py backend/tests/services/test_graph_history_tool.py
git commit -m "feat: extend graph history schema for v2 v3"
```

### Task 2: Add repository helpers needed by entity history

**Files:**
- Modify: `backend/app/repositories/memory_repository.py`
- Modify: `backend/app/repositories/memory_graph_episode_repository.py`
- Test: `backend/tests/services/test_graph_history_entity_aggregator.py`

- [ ] **Step 1: Write the failing aggregator-oriented repository test**

```python
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository


def test_count_versions_for_memories_returns_zero_for_empty_input(session):
    repo = MemoryGraphEpisodeRepository()
    assert repo.count_versions_for_memories(session, []) == 0
```

- [ ] **Step 2: Run the repository test to verify it fails**

Run: `python -m pytest backend/tests/services/test_graph_history_entity_aggregator.py -k count_versions_for_memories_returns_zero_for_empty_input -v`
Expected: FAIL with attribute error before helper methods exist.

- [ ] **Step 3: Add the repository helpers from the worktree implementation**

```python
def list_entity_memory_ids(self, db: Session, keyword: str) -> list[str]:
    pattern = f'%{keyword}%'
    query = (
        select(Memory.id)
        .where(or_(Memory.title.ilike(pattern), Memory.content.ilike(pattern)))
        .order_by(Memory.updated_at.desc(), Memory.created_at.desc(), Memory.id.asc())
    )
    return list(db.scalars(query))


def list_versions_for_memories(self, db: Session, memory_ids: list[str]) -> list[dict]:
    if not memory_ids:
        return []
```

- [ ] **Step 4: Run the repository helper test again**

Run: `python -m pytest backend/tests/services/test_graph_history_entity_aggregator.py -k count_versions_for_memories_returns_zero_for_empty_input -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/memory_repository.py backend/app/repositories/memory_graph_episode_repository.py backend/tests/services/test_graph_history_entity_aggregator.py
git commit -m "feat: add repository helpers for entity history"
```

### Task 3: Add entity resolver service

**Files:**
- Create: `backend/app/services/graph_history_entity_resolver.py`
- Test: `backend/tests/services/test_graph_history_entity_resolver.py`

- [ ] **Step 1: Write the failing entity resolver tests**

```python
from app.services.graph_history_entity_resolver import GraphHistoryEntityResolver


def test_entity_resolver_returns_exact_match():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['openai', 'Open AI']})
    result = resolver.resolve('OpenAI')

    assert result.status == 'ok'
    assert result.canonical_name == 'OpenAI'


def test_entity_resolver_returns_ambiguous_target_when_multiple_matches():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['ai'], 'Anthropic': ['ai']})
    result = resolver.resolve('ai')

    assert result.status == 'ambiguous_target'
    assert sorted(result.disambiguation_candidates) == ['Anthropic', 'OpenAI']
```

- [ ] **Step 2: Run the resolver tests to verify they fail**

Run: `python -m pytest backend/tests/services/test_graph_history_entity_resolver.py -v`
Expected: FAIL because the service file does not exist yet.

- [ ] **Step 3: Implement the minimal resolver**

```python
from dataclasses import dataclass, field


@dataclass
class EntityResolution:
    status: str
    canonical_name: str | None = None
    matched_alias: str | None = None
    disambiguation_candidates: list[str] = field(default_factory=list)


class GraphHistoryEntityResolver:
    def __init__(self, alias_map: dict[str, list[str]] | None = None) -> None:
        self.alias_map = alias_map or {}

    def resolve(self, raw_target: str) -> EntityResolution:
        normalized = raw_target.strip().lower()
        matches: dict[str, str] = {}
        for canonical_name, aliases in self.alias_map.items():
            if canonical_name.strip().lower() == normalized:
                matches.setdefault(canonical_name, canonical_name)
            for alias in aliases:
                if alias.strip().lower() == normalized:
                    matches.setdefault(canonical_name, alias)
        if not matches:
            return EntityResolution(status='not_found')
        if len(matches) > 1:
            return EntityResolution(status='ambiguous_target', disambiguation_candidates=list(matches))
        canonical_name, alias = next(iter(matches.items()))
        return EntityResolution(status='ok', canonical_name=canonical_name, matched_alias=alias)
```

- [ ] **Step 4: Run the resolver tests again**

Run: `python -m pytest backend/tests/services/test_graph_history_entity_resolver.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_entity_resolver.py backend/tests/services/test_graph_history_entity_resolver.py
git commit -m "feat: add graph history entity resolver"
```

### Task 4: Add entity aggregator service

**Files:**
- Create: `backend/app/services/graph_history_entity_aggregator.py`
- Test: `backend/tests/services/test_graph_history_entity_aggregator.py`

- [ ] **Step 1: Write the failing entity aggregator tests**

```python
from app.services.graph_history_entity_aggregator import GraphHistoryEntityAggregator


class StubMemoryRepository:
    def list_entity_memory_ids(self, db, keyword):
        return ['m1', 'm2']

    def list_entity_memory_refs(self, db, keyword, limit=20):
        return [{'id': 'm1', 'title': 'OpenAI 1'}, {'id': 'm2', 'title': 'OpenAI 2'}]


class StubEpisodeRepository:
    def list_versions_for_memories(self, db, memory_ids):
        return [
            {'memory_id': 'm1', 'version': 2, 'reference_time': None, 'created_at': None},
            {'memory_id': 'm2', 'version': 1, 'reference_time': None, 'created_at': None},
        ]

    def count_versions_for_memories(self, db, memory_ids):
        return 2


def test_collect_entity_events_returns_ranked_events():
    aggregator = GraphHistoryEntityAggregator(
        memory_repository=StubMemoryRepository(),
        episode_repository=StubEpisodeRepository(),
    )

    events = aggregator.collect_entity_events(db=None, canonical_name='OpenAI', top_k_events=10)
    assert [item['memory_id'] for item in events] == ['m1', 'm2']
```

- [ ] **Step 2: Run the aggregator tests to verify they fail**

Run: `python -m pytest backend/tests/services/test_graph_history_entity_aggregator.py -v`
Expected: FAIL because the service file does not exist yet.

- [ ] **Step 3: Implement the minimal aggregator**

```python
class GraphHistoryEntityAggregator:
    def __init__(self, *, memory_repository, episode_repository) -> None:
        self.memory_repository = memory_repository
        self.episode_repository = episode_repository

    def count_entity_events(self, db, canonical_name: str) -> int:
        memory_ids = self.memory_repository.list_entity_memory_ids(db, canonical_name)
        return self.episode_repository.count_versions_for_memories(db, memory_ids)

    def collect_entity_events(self, db, *, canonical_name: str, top_k_events: int = 10) -> list[dict]:
        memory_refs = {
            item['id']: item['title']
            for item in self.memory_repository.list_entity_memory_refs(db, canonical_name, limit=max(top_k_events, 20))
        }
        rows = self.episode_repository.list_versions_for_memories(db, list(memory_refs))
        events = [
            {
                'memory_id': row['memory_id'],
                'memory_title': memory_refs.get(row['memory_id'], row['memory_id']),
                'version': row['version'],
                'reference_time': row['reference_time'],
                'created_at': row['created_at'],
            }
            for row in rows
        ]
        return events[:top_k_events]
```

- [ ] **Step 4: Run the aggregator tests again**

Run: `python -m pytest backend/tests/services/test_graph_history_entity_aggregator.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_entity_aggregator.py backend/tests/services/test_graph_history_entity_aggregator.py
git commit -m "feat: add graph history entity aggregator"
```

### Task 5: Extend GraphHistoryService for entity history

**Files:**
- Modify: `backend/app/services/graph_history_service.py`
- Test: `backend/tests/services/test_graph_history_service.py`

- [ ] **Step 1: Write the failing entity service tests**

```python
from app.schemas.agent import GraphHistoryQuery
from app.services.graph_history_service import GraphHistoryService


def test_graph_history_service_returns_entity_timeline_from_aggregated_events():
    service = GraphHistoryService(
        db_factory=lambda: object(),
        entity_resolver=type('Resolver', (), {'resolve': lambda self, raw: type('R', (), {'status': 'ok', 'canonical_name': 'OpenAI', 'matched_alias': 'openai'})()})(),
        entity_aggregator=type('Agg', (), {
            'count_entity_events': lambda self, db, canonical_name: 2,
            'collect_entity_events': lambda self, db, canonical_name, top_k_events=10: [
                {'memory_id': 'm1', 'memory_title': 'OpenAI note', 'version': 2, 'reference_time': None, 'created_at': None},
                {'memory_id': 'm2', 'memory_title': 'OpenAI update', 'version': 1, 'reference_time': None, 'created_at': None},
            ],
        })(),
    )
    result = service.query(GraphHistoryQuery(target_type='entity', target_value='OpenAI', mode='timeline'))

    assert result.status == 'ok'
    assert result.resolved_target.canonical_name == 'OpenAI'
    assert len(result.timeline) == 2
```

- [ ] **Step 2: Run the entity service test to verify it fails**

Run: `python -m pytest backend/tests/services/test_graph_history_service.py -k entity_timeline -v`
Expected: FAIL because entity targets are still unsupported.

- [ ] **Step 3: Port the entity branch into `GraphHistoryService`**

```python
def query(self, payload: GraphHistoryQuery) -> GraphHistoryResult:
    if payload.target_type not in {'memory', 'entity', 'relation_topic'}:
        return GraphHistoryResult(...)
    db = self.db_factory()
    try:
        if payload.target_type == 'entity':
            return self._query_entity(db, payload)
        if payload.target_type == 'relation_topic':
            return self._query_relation_topic(db, payload)
        return self._query_memory(db, payload)
    finally:
        close = getattr(db, 'close', None)
        if callable(close):
            close()
```

- [ ] **Step 4: Run all service tests for memory + entity paths**

Run: `python -m pytest backend/tests/services/test_graph_history_service.py -v`
Expected: PASS for legacy memory tests and new entity tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_service.py backend/tests/services/test_graph_history_service.py
git commit -m "feat: add entity history to graph history service"
```

### Task 6: Expose graph history tool in agent schema and canvas wiring

**Files:**
- Modify: `backend/app/workflow/nodes/agent_node.py`
- Modify: `backend/app/workflow/canvas_factory.py`
- Test: `backend/tests/workflow/test_agent_history_orchestration.py`

- [ ] **Step 1: Write the failing workflow schema test**

```python
from app.workflow.dsl import WorkflowNodeSpec
from app.workflow.nodes.agent_node import AgentNode


def test_agent_node_graph_history_tool_schema_includes_entity_and_relation_topic():
    node = AgentNode(WorkflowNodeSpec(id='agent', type='agent'))
    schemas = node._tool_schemas()
    history_schema = next(item for item in schemas if item['function']['name'] == 'graph_history_tool')

    assert history_schema['function']['parameters']['properties']['target_type']['enum'] == [
        'memory',
        'entity',
        'relation_topic',
    ]
```

- [ ] **Step 2: Run the schema test to verify it fails**

Run: `python -m pytest backend/tests/workflow/test_agent_history_orchestration.py -k schema_includes_entity_and_relation_topic -v`
Expected: FAIL because the agent node only exposes graph retrieval today.

- [ ] **Step 3: Port the graph history tool schema and canvas factory injection**

```python
def _tool_schemas(self) -> list[dict[str, Any]]:
    return [
        {... graph retrieval schema ...},
        self._graph_history_tool_schema(),
    ]
```

```python
lambda spec: AgentNode(
    spec,
    knowledge_graph_service=knowledge_graph_service,
    graph_retrieval_tool=graph_retrieval_tool,
    graph_history_tool=graph_history_tool,
)
```

- [ ] **Step 4: Run the workflow schema test again**

Run: `python -m pytest backend/tests/workflow/test_agent_history_orchestration.py -k schema_includes_entity_and_relation_topic -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/workflow/nodes/agent_node.py backend/app/workflow/canvas_factory.py backend/tests/workflow/test_agent_history_orchestration.py
git commit -m "feat: expose graph history tool in agent workflow"
```

### Task 7: Add V3 minimal planner and relation/topic resolver

**Files:**
- Create: `backend/app/services/history_query_planner.py`
- Create: `backend/app/services/graph_history_relation_topic_resolver.py`
- Test: `backend/tests/services/test_history_query_planner.py`
- Test: `backend/tests/services/test_graph_history_relation_topic_resolver.py`

- [ ] **Step 1: Write the failing V3 helper tests**

```python
from app.services.history_query_planner import HistoryQueryPlanner
from app.services.graph_history_relation_topic_resolver import GraphHistoryRelationTopicResolver


def test_history_query_planner_classifies_mixed_question():
    planner = HistoryQueryPlanner()
    plan = planner.plan('OpenAI 现在和微软关系如何，历史上怎么变化的？')
    assert plan.intent == 'current_plus_history'


def test_relation_topic_resolver_prefers_relation_when_entities_are_present():
    resolver = GraphHistoryRelationTopicResolver()
    resolved = resolver.resolve('OpenAI 和微软的关系变化', {'source_entity': 'OpenAI', 'target_entity': '微软'})
    assert resolved.target_kind == 'relation'
```

- [ ] **Step 2: Run the helper tests to verify they fail**

Run: `python -m pytest backend/tests/services/test_history_query_planner.py backend/tests/services/test_graph_history_relation_topic_resolver.py -v`
Expected: FAIL because both service files do not exist yet.

- [ ] **Step 3: Implement the minimal planner and resolver**

```python
@dataclass
class HistoryQueryPlan:
    intent: str


class HistoryQueryPlanner:
    def plan(self, query: str) -> HistoryQueryPlan:
        text = query.strip()
        has_history = any(token in text for token in ['历史', '演变', '变化', '过去'])
        has_current = any(token in text for token in ['现在', '目前', '当前'])
        if has_history and has_current:
            return HistoryQueryPlan(intent='current_plus_history')
        if has_history:
            return HistoryQueryPlan(intent='history_only')
        return HistoryQueryPlan(intent='current_only')
```

- [ ] **Step 4: Run the helper tests again**

Run: `python -m pytest backend/tests/services/test_history_query_planner.py backend/tests/services/test_graph_history_relation_topic_resolver.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/history_query_planner.py backend/app/services/graph_history_relation_topic_resolver.py backend/tests/services/test_history_query_planner.py backend/tests/services/test_graph_history_relation_topic_resolver.py
git commit -m "feat: add v3 minimal planner and relation topic resolver"
```

### Task 8: Extend GraphHistoryService for minimal relation/topic support

**Files:**
- Modify: `backend/app/services/graph_history_service.py`
- Test: `backend/tests/services/test_graph_history_service.py`
- Test: `backend/tests/services/test_graph_history_tool.py`

- [ ] **Step 1: Write the failing relation/topic service test**

```python
from app.schemas.agent import GraphHistoryQuery
from app.services.graph_history_service import GraphHistoryService


def test_graph_history_service_supports_relation_topic_summarize():
    service = GraphHistoryService(
        db_factory=lambda: object(),
        relation_topic_resolver=type('Resolver', (), {
            'resolve': lambda self, target_value, constraints=None: type('Resolved', (), {
                'status': 'ok',
                'target_kind': 'relation',
                'target_value': target_value,
                'warnings': ['minimal relation mode'],
            })()
        })(),
    )
    result = service.query(
        GraphHistoryQuery(
            target_type='relation_topic',
            target_value='OpenAI 和微软关系变化',
            mode='summarize',
            constraints={'source_entity': 'OpenAI', 'target_entity': '微软'},
        )
    )

    assert result.status == 'ok'
    assert result.target_type == 'relation_topic'
    assert result.warnings == ['minimal relation mode']
```

- [ ] **Step 2: Run the relation/topic service test to verify it fails**

Run: `python -m pytest backend/tests/services/test_graph_history_service.py -k relation_topic_summarize -v`
Expected: FAIL because `GraphHistoryService` lacks the relation/topic branch.

- [ ] **Step 3: Implement the minimal relation/topic branch**

```python
def _query_relation_topic(self, db, payload: GraphHistoryQuery) -> GraphHistoryResult:
    resolved = self.relation_topic_resolver.resolve(payload.target_value, payload.constraints)
    if resolved.status != 'ok':
        return GraphHistoryResult(
            target_type='relation_topic',
            target_value=payload.target_value,
            mode=payload.mode,
            status=resolved.status,
            warnings=list(getattr(resolved, 'warnings', [])),
        )
    return GraphHistoryResult(
        target_type='relation_topic',
        target_value=payload.target_value,
        mode=payload.mode,
        status='ok',
        summary=f"围绕 {resolved.target_value} 的历史查询已进入 minimal 模式。",
        warnings=list(getattr(resolved, 'warnings', [])),
    )
```

- [ ] **Step 4: Run service and tool tests for relation/topic paths**

Run: `python -m pytest backend/tests/services/test_graph_history_service.py backend/tests/services/test_graph_history_tool.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_service.py backend/tests/services/test_graph_history_service.py backend/tests/services/test_graph_history_tool.py
git commit -m "feat: add minimal relation topic graph history support"
```

### Task 9: Add minimal planner-aware agent orchestration tests and implementation

**Files:**
- Modify: `backend/app/workflow/nodes/agent_node.py`
- Test: `backend/tests/workflow/test_agent_history_orchestration.py`

- [ ] **Step 1: Write the failing orchestration tests**

```python
from app.workflow.dsl import WorkflowNodeSpec
from app.workflow.nodes.agent_node import AgentNode


def test_agent_history_tool_passes_entity_constraints_to_service():
    captured = {}

    class StubService:
        def query(self, payload):
            captured['payload'] = payload
            return type('Result', (), {'model_dump': lambda self: {'status': 'ok'}})()

    from app.services.agent_tools.graph_history_tool import GraphHistoryTool
    tool = GraphHistoryTool(history_service=StubService())
    tool.run(target_type='entity', target_value='OpenAI', mode='timeline', constraints={'entity_match_mode': 'alias'})

    assert captured['payload'].constraints['entity_match_mode'] == 'alias'
```

- [ ] **Step 2: Run the orchestration tests to verify baseline failures**

Run: `python -m pytest backend/tests/workflow/test_agent_history_orchestration.py backend/tests/services/test_graph_history_tool.py -v`
Expected: FAIL until workflow and helper tests are fully aligned.

- [ ] **Step 3: Port the minimal planner-aware pieces from the worktree into `AgentNode`**

```python
def _tool_schemas(self) -> list[dict[str, Any]]:
    return [graph_retrieval_schema, self._graph_history_tool_schema()]


def _get_graph_history_tool(self) -> GraphHistoryTool:
    if self.graph_history_tool is None:
        self.graph_history_tool = GraphHistoryTool()
    return self.graph_history_tool
```

Keep the existing retrieval-first behavior intact. Only add the minimal new branches and helper wiring needed for tests and future planner use.

- [ ] **Step 4: Run workflow and tool tests again**

Run: `python -m pytest backend/tests/workflow/test_agent_history_orchestration.py backend/tests/services/test_graph_history_tool.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/workflow/nodes/agent_node.py backend/tests/workflow/test_agent_history_orchestration.py backend/tests/services/test_graph_history_tool.py
git commit -m "feat: add minimal history-aware agent orchestration"
```

### Task 10: Run focused regression suite and fix integration issues

**Files:**
- Modify as needed: all files touched above
- Test: `backend/tests/services/test_graph_history_entity_resolver.py`
- Test: `backend/tests/services/test_graph_history_entity_aggregator.py`
- Test: `backend/tests/services/test_graph_history_relation_topic_resolver.py`
- Test: `backend/tests/services/test_history_query_planner.py`
- Test: `backend/tests/services/test_graph_history_service.py`
- Test: `backend/tests/services/test_graph_history_tool.py`
- Test: `backend/tests/workflow/test_agent_history_orchestration.py`

- [ ] **Step 1: Run the focused graph history test suite**

Run: `python -m pytest backend/tests/services/test_graph_history_entity_resolver.py backend/tests/services/test_graph_history_entity_aggregator.py backend/tests/services/test_graph_history_relation_topic_resolver.py backend/tests/services/test_history_query_planner.py backend/tests/services/test_graph_history_service.py backend/tests/services/test_graph_history_tool.py backend/tests/workflow/test_agent_history_orchestration.py -v`
Expected: all tests PASS.

- [ ] **Step 2: If a test fails, fix the minimal issue before continuing**

Common fixes to prefer:

```python
# Keep service constructors dependency-injectable.
self.relation_topic_resolver = relation_topic_resolver or GraphHistoryRelationTopicResolver()

# Close db factories safely.
close = getattr(db, 'close', None)
if callable(close):
    close()
```

- [ ] **Step 3: Re-run the focused graph history test suite**

Run: `python -m pytest backend/tests/services/test_graph_history_entity_resolver.py backend/tests/services/test_graph_history_entity_aggregator.py backend/tests/services/test_graph_history_relation_topic_resolver.py backend/tests/services/test_history_query_planner.py backend/tests/services/test_graph_history_service.py backend/tests/services/test_graph_history_tool.py backend/tests/workflow/test_agent_history_orchestration.py -v`
Expected: all tests PASS.

- [ ] **Step 4: Commit the verified integration state**

```bash
git add backend/app backend/tests
git commit -m "test: verify graph history v2 v3 mainline port"
```

---

## Self-review checklist

- Spec coverage: includes V2 schema, repository helpers, resolver, aggregator, entity service branch, agent schema exposure, V3 planner, relation/topic resolver, minimal service support, canvas wiring, and workflow tests.
- Placeholder scan: no TODO/TBD markers are left in tasks.
- Type consistency: file names, service names, and status values match the design doc and worktree naming.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-10-graph-history-v2-v3-mainline-port-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**