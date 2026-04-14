# Graph History V2 / V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build V2 entity-history and V3 relation/topic-history + current/history multi-hop orchestration without breaking the default current-truth-only Q&A path.

**Architecture:** Extend the existing V1 `graph_history_tool` contract instead of replacing it. V2 adds entity resolution plus entity-scoped history aggregation inside the history service path; V3 adds relation/topic target resolution and a planner/composer layer that coordinates `graph_retrieval_tool` and `graph_history_tool` while keeping current truth and history truth separate.

**Tech Stack:** FastAPI, SQLAlchemy ORM, Pydantic, pytest, existing agent tools/workflow stack, existing graph retrieval service.

---

## Scope Check

The approved design covers two staged expansions that should be planned together but implemented in order:

1. **V2 entity-history**: resolve an entity target, aggregate history evidence across related memories/versions, and expose structured `timeline / compare / summarize` results through `graph_history_tool(target_type='entity')`.
2. **V3 relation/topic-history + orchestration**: resolve relation/topic targets, plan whether to use current retrieval, history retrieval, or both, and compose grouped evidence with turning points.

These remain in one plan because V3 reuses V2 schema/service boundaries. Execution should still land as small, testable commits: finish V2 first, then layer V3 on top.

## File Structure

### Files to create

- `backend/app/services/graph_history_entity_resolver.py`
  - Resolve `target_value` into a canonical entity target with ambiguity handling.
- `backend/app/services/graph_history_entity_aggregator.py`
  - Aggregate entity-related memories and versions into history events consumable by the service.
- `backend/app/services/graph_history_relation_topic_resolver.py`
  - Parse `relation_topic` requests into a stable intermediate target representation.
- `backend/app/services/history_query_planner.py`
  - Decide whether a user request needs current retrieval only, history retrieval only, or dual-tool orchestration.
- `backend/app/services/history_evidence_composer.py`
  - Compose current/history outputs into grouped evidence plus turning points.
- `backend/tests/services/test_graph_history_entity_resolver.py`
  - Unit tests for exact/alias/ambiguous entity resolution.
- `backend/tests/services/test_graph_history_entity_aggregator.py`
  - Unit tests for entity event aggregation.
- `backend/tests/services/test_history_query_planner.py`
  - Unit tests for planner routing decisions.
- `backend/tests/services/test_history_evidence_composer.py`
  - Unit tests for grouped evidence and turning point composition.
- `backend/tests/workflow/test_agent_history_orchestration.py`
  - Focused orchestration tests covering current-only, history-only, and dual-tool flows.

### Files to modify

- `backend/app/schemas/agent.py`
  - Extend graph history request/result schemas for entity and relation/topic targets.
- `backend/app/repositories/memory_repository.py`
  - Add entity-oriented lookup helpers if no equivalent exists.
- `backend/app/repositories/memory_graph_episode_repository.py`
  - Add entity-scoped and relation/topic-scoped history query helpers.
- `backend/app/services/graph_history_service.py`
  - Route `memory`, `entity`, and later `relation_topic` requests to the correct resolver/aggregator path.
- `backend/app/services/agent_tools/graph_history_tool.py`
  - Keep tool thin while permitting expanded constraints and statuses.
- `backend/app/services/agent_tools/graph_retrieval_tool.py`
  - No behavior change expected, but inspect for compatibility with V3 orchestration result shape.
- `backend/app/workflow/nodes/agent_node.py`
  - Extend tool schema descriptions and optionally call planner/composer for dual-tool answers.
- `backend/app/workflow/canvas_factory.py`
  - Construct planner/composer dependencies alongside retrieval/history tools.
- `backend/tests/services/test_graph_history_service.py`
  - Add entity and relation/topic service coverage without regressing V1 memory behavior.
- `backend/tests/services/test_graph_history_tool.py`
  - Add schema/contract assertions for new statuses and fields.

### Files to inspect while implementing

- `docs/superpowers/specs/2026-04-07-graph-history-v2-v3-design.md`
- `backend/app/services/graph_history_service.py`
- `backend/app/services/agent_tools/graph_history_tool.py`
- `backend/app/services/agent_tools/graph_retrieval_tool.py`
- `backend/app/workflow/nodes/agent_node.py`
- `backend/app/workflow/canvas_factory.py`
- `backend/app/repositories/memory_repository.py`
- `backend/app/repositories/memory_graph_episode_repository.py`

## Implementation Notes Before Starting

- Keep V1 memory-history behavior green throughout; do not refactor away existing V1 tests.
- Preserve the core boundary from the spec:
  - default Q&A = current truth only
  - explicit history = `graph_history_tool`
  - orchestration may combine outputs, but history data must not become always-on prompt state
- Prefer repository/service additions over embedding raw SQL in workflow code.
- For V2, fail safely on ambiguity instead of guessing.
- For V3, plan and compose in dedicated classes; do not turn `GraphHistoryTool` into a god object.

---

### Task 1: Extend graph history schemas for V2/V3 targets

**Files:**
- Modify: `backend/app/schemas/agent.py`
- Test: `backend/tests/services/test_graph_history_tool.py`

- [ ] **Step 1: Write the failing schema tests**

```python
from app.schemas.agent import GraphHistoryQuery, GraphHistoryResult, GraphHistoryResolvedTarget


def test_graph_history_query_supports_entity_constraints():
    query = GraphHistoryQuery(
        target_type='entity',
        target_value='OpenAI',
        mode='timeline',
        constraints={
            'entity_match_mode': 'alias',
            'top_k_events': 5,
            'disambiguation_policy': 'return_candidates',
        },
    )

    assert query.target_type == 'entity'
    assert query.constraints['entity_match_mode'] == 'alias'
    assert query.constraints['top_k_events'] == 5


def test_graph_history_result_supports_ambiguous_target_and_turning_points():
    result = GraphHistoryResult(
        target_type='relation_topic',
        target_value='OpenAI 与 Sam Altman 的关系如何变化',
        mode='summarize',
        status='ambiguous_target',
        resolved_target=GraphHistoryResolvedTarget(
            canonical_name='OpenAI',
            candidate_count=2,
        ),
        turning_points=[{'label': '董事会风波', 'version': 4}],
        confidence=0.42,
        evidence_groups=[{'group_type': 'history', 'items': []}],
    )

    assert result.status == 'ambiguous_target'
    assert result.resolved_target.canonical_name == 'OpenAI'
    assert result.turning_points[0]['label'] == '董事会风波'
    assert result.confidence == 0.42
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_graph_history_tool.py -v`
Expected: FAIL because the new schema fields/status literals are not yet defined.

- [ ] **Step 3: Write minimal schema implementation**

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
    relation_type: str | None = None
    source_entity: str | None = None
    target_entity: str | None = None
    topic_scope: str | None = None


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
    timeline: list[GraphHistoryTimelineItem] = Field(default_factory=list)
    comparisons: list[GraphHistoryComparisonItem] = Field(default_factory=list)
    summary: str = ''
    evidence: list[GraphHistoryEvidenceItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    turning_points: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float | None = None
    evidence_groups: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_graph_history_tool.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/agent.py backend/tests/services/test_graph_history_tool.py
git commit -m "feat: extend graph history schemas for entity and relation topic"
```

### Task 2: Add repository helpers for entity-history aggregation

**Files:**
- Modify: `backend/app/repositories/memory_repository.py`
- Modify: `backend/app/repositories/memory_graph_episode_repository.py`
- Test: `backend/tests/services/test_graph_history_entity_aggregator.py`

- [ ] **Step 1: Write the failing repository-oriented aggregator tests**

```python
def test_entity_aggregator_collects_versions_across_multiple_memories(db_session):
    memory_a = Memory(title='OpenAI Funding', title_status='ready', content='OpenAI completed funding', group_id='default')
    memory_b = Memory(title='OpenAI Board', title_status='ready', content='OpenAI board changed', group_id='default')
    db_session.add_all([memory_a, memory_b])
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory_a.id, episode_uuid='a-v1', version=1, chunk_index=0, is_latest=True),
            MemoryGraphEpisode(memory_id=memory_b.id, episode_uuid='b-v2', version=2, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    aggregator = GraphHistoryEntityAggregator(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
    )

    events = aggregator.collect_entity_events(db_session, canonical_name='OpenAI')

    assert len(events) == 2
    assert {event['memory_title'] for event in events} == {'OpenAI Funding', 'OpenAI Board'}


def test_entity_aggregator_respects_top_k_constraint(db_session):
    aggregator = GraphHistoryEntityAggregator(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
    )

    events = aggregator.collect_entity_events(db_session, canonical_name='OpenAI', top_k_events=1)

    assert len(events) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_graph_history_entity_aggregator.py -v`
Expected: FAIL because the aggregator and repository helpers do not exist yet.

- [ ] **Step 3: Write minimal repository-compatible implementation**

```python
class MemoryRepository:
    def list_by_entity_keyword(self, db: Session, keyword: str, limit: int = 20) -> list[Memory]:
        pattern = f'%{keyword}%'
        return list(
            db.scalars(
                select(Memory)
                .where((Memory.title.ilike(pattern)) | (Memory.content.ilike(pattern)))
                .order_by(Memory.updated_at.desc())
                .limit(limit)
            )
        )


class MemoryGraphEpisodeRepository:
    def list_versions_for_memories(self, db: Session, memory_ids: list[str]) -> list[dict]:
        if not memory_ids:
            return []
        rows = db.execute(
            select(
                MemoryGraphEpisode.memory_id,
                MemoryGraphEpisode.version,
                func.max(MemoryGraphEpisode.reference_time).label('reference_time'),
                func.max(MemoryGraphEpisode.created_at).label('created_at'),
            )
            .where(MemoryGraphEpisode.memory_id.in_(memory_ids))
            .group_by(MemoryGraphEpisode.memory_id, MemoryGraphEpisode.version)
            .order_by(func.max(MemoryGraphEpisode.created_at).desc())
        )
        return [dict(item._mapping) for item in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_graph_history_entity_aggregator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/memory_repository.py backend/app/repositories/memory_graph_episode_repository.py backend/tests/services/test_graph_history_entity_aggregator.py
git commit -m "feat: add repository helpers for entity history aggregation"
```

### Task 3: Implement entity resolver with exact/alias/ambiguous outcomes

**Files:**
- Create: `backend/app/services/graph_history_entity_resolver.py`
- Test: `backend/tests/services/test_graph_history_entity_resolver.py`

- [ ] **Step 1: Write the failing resolver tests**

```python
def test_entity_resolver_returns_exact_match():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI', 'Open AI']})

    resolved = resolver.resolve('OpenAI')

    assert resolved.status == 'ok'
    assert resolved.canonical_name == 'OpenAI'
    assert resolved.matched_alias == 'OpenAI'


def test_entity_resolver_returns_alias_match():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI', 'Open AI']})

    resolved = resolver.resolve('Open AI')

    assert resolved.status == 'ok'
    assert resolved.canonical_name == 'OpenAI'
    assert resolved.matched_alias == 'Open AI'


def test_entity_resolver_returns_ambiguous_target():
    resolver = GraphHistoryEntityResolver(alias_map={'Apple Inc.': ['Apple'], 'Apple Fruit': ['Apple']})

    resolved = resolver.resolve('Apple')

    assert resolved.status == 'ambiguous_target'
    assert len(resolved.disambiguation_candidates) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_graph_history_entity_resolver.py -v`
Expected: FAIL because `GraphHistoryEntityResolver` does not exist.

- [ ] **Step 3: Write minimal resolver implementation**

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
        matches: list[tuple[str, str]] = []
        for canonical_name, aliases in self.alias_map.items():
            for alias in aliases:
                if alias.strip().lower() == normalized:
                    matches.append((canonical_name, alias))

        if not matches:
            return EntityResolution(status='not_found')
        if len(matches) > 1:
            return EntityResolution(
                status='ambiguous_target',
                disambiguation_candidates=[item[0] for item in matches],
            )
        canonical_name, alias = matches[0]
        return EntityResolution(status='ok', canonical_name=canonical_name, matched_alias=alias)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_graph_history_entity_resolver.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_entity_resolver.py backend/tests/services/test_graph_history_entity_resolver.py
git commit -m "feat: add entity history resolver"
```

### Task 4: Implement entity-history aggregator

**Files:**
- Create: `backend/app/services/graph_history_entity_aggregator.py`
- Test: `backend/tests/services/test_graph_history_entity_aggregator.py`

- [ ] **Step 1: Write the failing aggregator service tests**

```python
def test_collect_entity_events_returns_latest_first(db_session):
    aggregator = GraphHistoryEntityAggregator(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
    )

    events = aggregator.collect_entity_events(db_session, canonical_name='OpenAI', top_k_events=10)

    assert events[0]['version'] >= events[-1]['version']


def test_collect_entity_events_returns_empty_for_no_matches(db_session):
    aggregator = GraphHistoryEntityAggregator(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
    )

    events = aggregator.collect_entity_events(db_session, canonical_name='Missing')

    assert events == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_graph_history_entity_aggregator.py -v`
Expected: FAIL because the aggregator class does not exist.

- [ ] **Step 3: Write minimal aggregator implementation**

```python
class GraphHistoryEntityAggregator:
    def __init__(
        self,
        *,
        memory_repository: MemoryRepository,
        episode_repository: MemoryGraphEpisodeRepository,
    ) -> None:
        self.memory_repository = memory_repository
        self.episode_repository = episode_repository

    def collect_entity_events(self, db: Session, canonical_name: str, top_k_events: int = 10) -> list[dict]:
        memories = self.memory_repository.list_by_entity_keyword(db, canonical_name, limit=max(top_k_events, 10))
        if not memories:
            return []
        memory_map = {memory.id: memory for memory in memories}
        version_rows = self.episode_repository.list_versions_for_memories(db, list(memory_map.keys()))
        events = [
            {
                'memory_id': row['memory_id'],
                'memory_title': memory_map[row['memory_id']].title,
                'version': row['version'],
                'reference_time': row['reference_time'],
                'created_at': row['created_at'],
            }
            for row in version_rows
        ]
        return events[:top_k_events]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_graph_history_entity_aggregator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_entity_aggregator.py backend/tests/services/test_graph_history_entity_aggregator.py
git commit -m "feat: add entity history aggregator"
```

### Task 5: Extend `GraphHistoryService` for `target_type='entity'`

**Files:**
- Modify: `backend/app/services/graph_history_service.py`
- Modify: `backend/tests/services/test_graph_history_service.py`

- [ ] **Step 1: Write the failing entity-history service tests**

```python
def test_query_entity_timeline_returns_aggregated_events(db_session):
    service = GraphHistoryService(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
        db_factory=lambda: db_session,
        entity_resolver=GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI']}),
        entity_aggregator=GraphHistoryEntityAggregator(
            memory_repository=MemoryRepository(),
            episode_repository=MemoryGraphEpisodeRepository(),
        ),
    )

    result = service.query(
        GraphHistoryQuery(target_type='entity', target_value='OpenAI', mode='timeline', question='这个实体如何演化？')
    )

    assert result.status == 'ok'
    assert result.resolved_target.canonical_name == 'OpenAI'
    assert result.timeline != []


def test_query_entity_returns_ambiguous_target_when_resolver_cannot_disambiguate(db_session):
    service = GraphHistoryService(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
        db_factory=lambda: db_session,
        entity_resolver=GraphHistoryEntityResolver(alias_map={'Apple Inc.': ['Apple'], 'Apple Fruit': ['Apple']}),
        entity_aggregator=GraphHistoryEntityAggregator(
            memory_repository=MemoryRepository(),
            episode_repository=MemoryGraphEpisodeRepository(),
        ),
    )

    result = service.query(
        GraphHistoryQuery(target_type='entity', target_value='Apple', mode='timeline', question='Apple 如何变化？')
    )

    assert result.status == 'ambiguous_target'
    assert result.resolved_target.candidate_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_graph_history_service.py -v`
Expected: FAIL because `GraphHistoryService` only handles `target_type='memory'`.

- [ ] **Step 3: Write minimal entity-history implementation**

```python
class GraphHistoryService:
    def __init__(
        self,
        *,
        memory_repository: MemoryRepository | None = None,
        episode_repository: MemoryGraphEpisodeRepository | None = None,
        db_factory=None,
        entity_resolver: GraphHistoryEntityResolver | None = None,
        entity_aggregator: GraphHistoryEntityAggregator | None = None,
    ) -> None:
        self.memory_repository = memory_repository or MemoryRepository()
        self.episode_repository = episode_repository or MemoryGraphEpisodeRepository()
        self.db_factory = db_factory or SessionLocal
        self.entity_resolver = entity_resolver or GraphHistoryEntityResolver()
        self.entity_aggregator = entity_aggregator or GraphHistoryEntityAggregator(
            memory_repository=self.memory_repository,
            episode_repository=self.episode_repository,
        )

    def _query_entity(self, db: Session, payload: GraphHistoryQuery) -> GraphHistoryResult:
        resolved = self.entity_resolver.resolve(payload.target_value)
        if resolved.status == 'not_found':
            return GraphHistoryResult(
                target_type='entity',
                target_value=payload.target_value,
                mode=payload.mode,
                status='not_found',
            )
        if resolved.status == 'ambiguous_target':
            return GraphHistoryResult(
                target_type='entity',
                target_value=payload.target_value,
                mode=payload.mode,
                status='ambiguous_target',
                resolved_target=GraphHistoryResolvedTarget(
                    canonical_name=payload.target_value,
                    candidate_count=len(resolved.disambiguation_candidates),
                ),
                warnings=['目标存在多个高置信候选，请先澄清实体。'],
            )

        events = self.entity_aggregator.collect_entity_events(
            db,
            canonical_name=resolved.canonical_name,
            top_k_events=payload.constraints.get('top_k_events', 10),
        )
        if not events:
            return GraphHistoryResult(
                target_type='entity',
                target_value=payload.target_value,
                mode=payload.mode,
                status='insufficient_evidence',
                resolved_target=GraphHistoryResolvedTarget(
                    canonical_name=resolved.canonical_name,
                    matched_alias=resolved.matched_alias,
                ),
            )
        timeline = [
            GraphHistoryTimelineItem(
                version=event['version'],
                is_latest=index == 0,
                reference_time=event['reference_time'].isoformat() if event['reference_time'] else None,
                created_at=event['created_at'].isoformat() if event['created_at'] else None,
                episode_count=1,
                summary_excerpt=f"{event['memory_title']} v{event['version']}",
            )
            for index, event in enumerate(events)
        ]
        return GraphHistoryResult(
            target_type='entity',
            target_value=payload.target_value,
            mode=payload.mode,
            status='ok',
            resolved_target=GraphHistoryResolvedTarget(
                canonical_name=resolved.canonical_name,
                matched_alias=resolved.matched_alias,
                version_count=len(events),
            ),
            timeline=timeline,
            summary=f'{resolved.canonical_name} 共关联 {len(events)} 条历史事件。' if payload.mode == 'summarize' else '',
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_graph_history_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_service.py backend/tests/services/test_graph_history_service.py
git commit -m "feat: add entity history support to graph history service"
```

### Task 6: Extend tool and workflow contract for entity-history routing

**Files:**
- Modify: `backend/app/services/agent_tools/graph_history_tool.py`
- Modify: `backend/app/workflow/nodes/agent_node.py`
- Modify: `backend/app/workflow/canvas_factory.py`
- Test: `backend/tests/workflow/test_agent_history_orchestration.py`

- [ ] **Step 1: Write the failing workflow contract tests**

```python
def test_agent_node_graph_history_tool_schema_includes_entity_target_type():
    node = build_agent_node_for_test()

    schemas = node._tool_schemas()
    history_schema = next(item for item in schemas if item['function']['name'] == 'graph_history_tool')

    assert history_schema['function']['parameters']['properties']['target_type']['enum'] == ['memory', 'entity', 'relation_topic']


def test_graph_history_tool_passes_entity_constraints_to_service():
    captured = {}

    class StubService:
        def query(self, payload):
            captured['payload'] = payload
            return GraphHistoryResult(target_type='entity', target_value='OpenAI', mode='timeline', status='ok')

    tool = GraphHistoryTool(history_service=StubService())
    tool.run(
        target_type='entity',
        target_value='OpenAI',
        mode='timeline',
        constraints={'entity_match_mode': 'alias'},
    )

    assert captured['payload'].constraints['entity_match_mode'] == 'alias'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/workflow/test_agent_history_orchestration.py -v`
Expected: FAIL because workflow/tool schema still reflects the narrower V1 contract.

- [ ] **Step 3: Implement minimal contract updates**

```python
def _graph_history_tool_schema() -> dict[str, Any]:
    return {
        'type': 'function',
        'function': {
            'name': 'graph_history_tool',
            'description': '检索 memory、entity 或 relation/topic 的结构化历史证据。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'target_type': {'type': 'string', 'enum': ['memory', 'entity', 'relation_topic']},
                    'target_value': {'type': 'string'},
                    'mode': {'type': 'string', 'enum': ['timeline', 'compare', 'summarize']},
                    'question': {'type': 'string'},
                    'constraints': {'type': 'object'},
                },
                'required': ['target_type', 'target_value', 'mode'],
            },
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/workflow/test_agent_history_orchestration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent_tools/graph_history_tool.py backend/app/workflow/nodes/agent_node.py backend/app/workflow/canvas_factory.py backend/tests/workflow/test_agent_history_orchestration.py
git commit -m "feat: expose entity history contract in workflow"
```

### Task 7: Add relation/topic resolver for V3 intermediate targets

**Files:**
- Create: `backend/app/services/graph_history_relation_topic_resolver.py`
- Test: `backend/tests/services/test_history_query_planner.py`

- [ ] **Step 1: Write the failing resolver tests**

```python
def test_relation_topic_resolver_extracts_relation_target():
    resolver = GraphHistoryRelationTopicResolver()

    result = resolver.resolve(
        target_value='OpenAI 和 Microsoft 的关系如何变化',
        constraints={'source_entity': 'OpenAI', 'target_entity': 'Microsoft', 'relation_type': 'partnership'},
    )

    assert result.target_kind == 'relation'
    assert result.source_entity == 'OpenAI'
    assert result.target_entity == 'Microsoft'
    assert result.relation_type == 'partnership'


def test_relation_topic_resolver_extracts_topic_target():
    resolver = GraphHistoryRelationTopicResolver()

    result = resolver.resolve(
        target_value='AI safety 主题如何演化',
        constraints={'topic_scope': 'AI safety'},
    )

    assert result.target_kind == 'topic'
    assert result.topic_scope == 'AI safety'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_history_query_planner.py -v`
Expected: FAIL because the relation/topic resolver does not exist.

- [ ] **Step 3: Write minimal resolver implementation**

```python
from dataclasses import dataclass


@dataclass
class RelationTopicTarget:
    target_kind: str
    source_entity: str | None = None
    target_entity: str | None = None
    relation_type: str | None = None
    topic_scope: str | None = None


class GraphHistoryRelationTopicResolver:
    def resolve(self, target_value: str, constraints: dict[str, str] | None = None) -> RelationTopicTarget:
        constraints = constraints or {}
        if constraints.get('source_entity') and constraints.get('target_entity'):
            return RelationTopicTarget(
                target_kind='relation',
                source_entity=constraints.get('source_entity'),
                target_entity=constraints.get('target_entity'),
                relation_type=constraints.get('relation_type'),
            )
        return RelationTopicTarget(
            target_kind='topic',
            topic_scope=constraints.get('topic_scope') or target_value,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_history_query_planner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_relation_topic_resolver.py backend/tests/services/test_history_query_planner.py
git commit -m "feat: add relation topic history resolver"
```

### Task 8: Add history query planner for current/history orchestration

**Files:**
- Create: `backend/app/services/history_query_planner.py`
- Test: `backend/tests/services/test_history_query_planner.py`

- [ ] **Step 1: Write the failing planner tests**

```python
def test_planner_uses_current_only_for_present_state_question():
    planner = HistoryQueryPlanner()

    plan = planner.plan('OpenAI 现在和 Microsoft 是什么关系？')

    assert plan.steps == ['current_retrieval']


def test_planner_uses_history_only_for_pure_history_question():
    planner = HistoryQueryPlanner()

    plan = planner.plan('OpenAI 和 Microsoft 以前的关系如何变化？')

    assert plan.steps == ['history_retrieval']


def test_planner_uses_dual_tool_flow_for_current_vs_history_question():
    planner = HistoryQueryPlanner()

    plan = planner.plan('OpenAI 和 Microsoft 当前关系与历史转折点有什么差异？')

    assert plan.steps == ['current_retrieval', 'history_retrieval', 'compose_answer']
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_history_query_planner.py -v`
Expected: FAIL because `HistoryQueryPlanner` does not exist.

- [ ] **Step 3: Write minimal planner implementation**

```python
from dataclasses import dataclass


@dataclass
class QueryPlan:
    steps: list[str]


class HistoryQueryPlanner:
    def plan(self, question: str) -> QueryPlan:
        normalized = question.strip()
        if '当前' in normalized and '历史' in normalized:
            return QueryPlan(steps=['current_retrieval', 'history_retrieval', 'compose_answer'])
        if '现在' in normalized and '如何变化' not in normalized and '历史' not in normalized:
            return QueryPlan(steps=['current_retrieval'])
        return QueryPlan(steps=['history_retrieval'])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_history_query_planner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/history_query_planner.py backend/tests/services/test_history_query_planner.py
git commit -m "feat: add history query planner"
```

### Task 9: Add evidence composer for turning points and grouped evidence

**Files:**
- Create: `backend/app/services/history_evidence_composer.py`
- Test: `backend/tests/services/test_history_evidence_composer.py`

- [ ] **Step 1: Write the failing composer tests**

```python
def test_evidence_composer_groups_current_and_history_outputs():
    composer = HistoryEvidenceComposer()

    result = composer.compose(
        current_result={'context': '当前结论：合作仍在继续', 'references': []},
        history_result=GraphHistoryResult(
            target_type='relation_topic',
            target_value='OpenAI/Microsoft',
            mode='summarize',
            status='ok',
            summary='历史上经历多次合作扩张。',
            evidence_groups=[],
        ),
    )

    assert [group['group_type'] for group in result['evidence_groups']] == ['current', 'history']


def test_evidence_composer_extracts_turning_points_from_comparisons():
    composer = HistoryEvidenceComposer()

    result = composer.compose(
        current_result={'context': '当前结论：合作稳定', 'references': []},
        history_result=GraphHistoryResult(
            target_type='relation_topic',
            target_value='OpenAI/Microsoft',
            mode='compare',
            status='ok',
            comparisons=[
                GraphHistoryComparisonItem(
                    from_version=2,
                    to_version=3,
                    change_summary='从研发合作转为战略合作',
                )
            ],
        ),
    )

    assert result['turning_points'][0]['label'] == '从研发合作转为战略合作'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_history_evidence_composer.py -v`
Expected: FAIL because `HistoryEvidenceComposer` does not exist.

- [ ] **Step 3: Write minimal composer implementation**

```python
class HistoryEvidenceComposer:
    def compose(self, current_result: dict, history_result: GraphHistoryResult) -> dict[str, Any]:
        evidence_groups = [
            {
                'group_type': 'current',
                'items': [current_result],
            },
            {
                'group_type': 'history',
                'items': [history_result.model_dump()],
            },
        ]
        turning_points = [
            {
                'label': item.change_summary,
                'from_version': item.from_version,
                'to_version': item.to_version,
            }
            for item in history_result.comparisons
        ]
        return {
            'evidence_groups': evidence_groups,
            'turning_points': turning_points,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_history_evidence_composer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/history_evidence_composer.py backend/tests/services/test_history_evidence_composer.py
git commit -m "feat: add history evidence composer"
```

### Task 10: Extend `GraphHistoryService` for `target_type='relation_topic'`

**Files:**
- Modify: `backend/app/services/graph_history_service.py`
- Modify: `backend/tests/services/test_graph_history_service.py`

- [ ] **Step 1: Write the failing relation/topic service tests**

```python
def test_query_relation_topic_summarize_returns_turning_points(db_session):
    service = build_relation_topic_history_service(db_session)

    result = service.query(
        GraphHistoryQuery(
            target_type='relation_topic',
            target_value='OpenAI 和 Microsoft 的关系如何变化',
            mode='summarize',
            constraints={
                'source_entity': 'OpenAI',
                'target_entity': 'Microsoft',
                'relation_type': 'partnership',
            },
        )
    )

    assert result.status == 'ok'
    assert result.resolved_target.source_entity == 'OpenAI'
    assert result.turning_points != []


def test_query_relation_topic_returns_insufficient_evidence_when_no_events(db_session):
    service = build_relation_topic_history_service(db_session)

    result = service.query(
        GraphHistoryQuery(target_type='relation_topic', target_value='unknown topic', mode='timeline')
    )

    assert result.status == 'insufficient_evidence'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_graph_history_service.py -v`
Expected: FAIL because `relation_topic` is not yet implemented.

- [ ] **Step 3: Write minimal relation/topic implementation**

```python
class GraphHistoryService:
    def __init__(..., relation_topic_resolver: GraphHistoryRelationTopicResolver | None = None) -> None:
        ...
        self.relation_topic_resolver = relation_topic_resolver or GraphHistoryRelationTopicResolver()

    def _query_relation_topic(self, db: Session, payload: GraphHistoryQuery) -> GraphHistoryResult:
        resolved = self.relation_topic_resolver.resolve(payload.target_value, payload.constraints)
        if resolved.target_kind == 'relation':
            label = f"{resolved.source_entity} -> {resolved.target_entity} ({resolved.relation_type or 'related'})"
        else:
            label = resolved.topic_scope or payload.target_value

        events = self.entity_aggregator.collect_entity_events(
            db,
            canonical_name=resolved.source_entity or resolved.topic_scope or payload.target_value,
            top_k_events=payload.constraints.get('top_k_events', 10),
        )
        if not events:
            return GraphHistoryResult(
                target_type='relation_topic',
                target_value=payload.target_value,
                mode=payload.mode,
                status='insufficient_evidence',
                resolved_target=GraphHistoryResolvedTarget(
                    relation_type=resolved.relation_type,
                    source_entity=resolved.source_entity,
                    target_entity=resolved.target_entity,
                    topic_scope=resolved.topic_scope,
                ),
            )

        comparisons = [
            GraphHistoryComparisonItem(
                from_version=max(event['version'] - 1, 0),
                to_version=event['version'],
                change_summary=f'{label} 在 v{event["version"]} 发生关键变化',
            )
            for event in events[:1]
        ]
        return GraphHistoryResult(
            target_type='relation_topic',
            target_value=payload.target_value,
            mode=payload.mode,
            status='ok',
            resolved_target=GraphHistoryResolvedTarget(
                relation_type=resolved.relation_type,
                source_entity=resolved.source_entity,
                target_entity=resolved.target_entity,
                topic_scope=resolved.topic_scope,
            ),
            summary=f'{label} 共整理出 {len(events)} 条历史证据。' if payload.mode == 'summarize' else '',
            comparisons=comparisons,
            turning_points=[{'label': item.change_summary, 'to_version': item.to_version} for item in comparisons],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_graph_history_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_service.py backend/tests/services/test_graph_history_service.py
git commit -m "feat: add relation topic history support"
```

### Task 11: Wire planner + composer into agent orchestration

**Files:**
- Modify: `backend/app/workflow/nodes/agent_node.py`
- Modify: `backend/app/workflow/canvas_factory.py`
- Modify: `backend/tests/workflow/test_agent_history_orchestration.py`

- [ ] **Step 1: Write the failing orchestration tests**

```python
@pytest.mark.asyncio
async def test_agent_orchestration_uses_current_then_history_then_composer_for_dual_mode_question():
    node = build_agent_node_with_history_planner(
        planner=StubPlanner(steps=['current_retrieval', 'history_retrieval', 'compose_answer']),
        retrieval_tool=StubGraphRetrievalTool(context='当前事实'),
        history_tool=StubGraphHistoryTool(summary='历史事实'),
        composer=StubComposer(result={'evidence_groups': [{'group_type': 'current'}, {'group_type': 'history'}], 'turning_points': []}),
    )

    response = await node.answer_question('当前关系和历史转折点有什么差异？')

    assert response.trace.final_action == 'compose_answer'
    assert response.answer != ''


@pytest.mark.asyncio
async def test_agent_orchestration_keeps_current_only_question_off_history_path():
    node = build_agent_node_with_history_planner(
        planner=StubPlanner(steps=['current_retrieval']),
        retrieval_tool=StubGraphRetrievalTool(context='当前事实'),
        history_tool=ExplodingHistoryTool(),
        composer=StubComposer(result={'evidence_groups': [], 'turning_points': []}),
    )

    response = await node.answer_question('现在是什么情况？')

    assert response.trace.final_action == 'current_retrieval'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/workflow/test_agent_history_orchestration.py -v`
Expected: FAIL because agent orchestration has no planner/composer integration.

- [ ] **Step 3: Implement minimal orchestration path**

```python
class AgentNode:
    def __init__(..., history_query_planner: HistoryQueryPlanner | None = None, history_evidence_composer: HistoryEvidenceComposer | None = None, ...):
        ...
        self.history_query_planner = history_query_planner or HistoryQueryPlanner()
        self.history_evidence_composer = history_evidence_composer or HistoryEvidenceComposer()

    async def answer_question(self, question: str, group_id: str = 'default'):
        plan = self.history_query_planner.plan(question)
        current_result = None
        history_result = None

        if 'current_retrieval' in plan.steps:
            current_result = await self._get_graph_retrieval_tool().run(question, group_id=group_id)
        if 'history_retrieval' in plan.steps:
            history_result = self._get_graph_history_tool().run(
                target_type='relation_topic' if ('关系' in question or '主题' in question) else 'entity',
                target_value=question,
                mode='summarize',
                question=question,
            )
        if 'compose_answer' in plan.steps and current_result and history_result:
            composed = self.history_evidence_composer.compose(
                current_result=current_result.model_dump() if hasattr(current_result, 'model_dump') else current_result,
                history_result=history_result,
            )
            return self._build_dual_mode_answer(question, current_result, history_result, composed)
        return self._build_single_mode_answer(question, current_result=current_result, history_result=history_result)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/workflow/test_agent_history_orchestration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/workflow/nodes/agent_node.py backend/app/workflow/canvas_factory.py backend/tests/workflow/test_agent_history_orchestration.py
git commit -m "feat: add current history orchestration path"
```

### Task 12: Run focused regression verification for V1 + V2/V3 additions

**Files:**
- Test: `backend/tests/services/test_graph_history_service.py`
- Test: `backend/tests/services/test_graph_history_tool.py`
- Test: `backend/tests/services/test_graph_history_entity_resolver.py`
- Test: `backend/tests/services/test_graph_history_entity_aggregator.py`
- Test: `backend/tests/services/test_history_query_planner.py`
- Test: `backend/tests/services/test_history_evidence_composer.py`
- Test: `backend/tests/workflow/test_agent_history_orchestration.py`

- [ ] **Step 1: Run V1 + V2 service/tool coverage**

```bash
python -m pytest \
  backend/tests/services/test_graph_history_service.py \
  backend/tests/services/test_graph_history_tool.py \
  backend/tests/services/test_graph_history_entity_resolver.py \
  backend/tests/services/test_graph_history_entity_aggregator.py \
  -q
```

Expected: PASS with all V1 memory-history tests still green and new V2 tests green.

- [ ] **Step 2: Run V3 planner/composer/workflow coverage**

```bash
python -m pytest \
  backend/tests/services/test_history_query_planner.py \
  backend/tests/services/test_history_evidence_composer.py \
  backend/tests/workflow/test_agent_history_orchestration.py \
  -q
```

Expected: PASS with planner, composer, and orchestration tests green.

- [ ] **Step 3: Run one combined focused suite**

```bash
python -m pytest \
  backend/tests/services/test_graph_history_service.py \
  backend/tests/services/test_graph_history_tool.py \
  backend/tests/services/test_graph_history_entity_resolver.py \
  backend/tests/services/test_graph_history_entity_aggregator.py \
  backend/tests/services/test_history_query_planner.py \
  backend/tests/services/test_history_evidence_composer.py \
  backend/tests/workflow/test_agent_history_orchestration.py \
  -q
```

Expected: PASS

- [ ] **Step 4: Commit final integrated V2/V3 slice**

```bash
git add backend/app/schemas/agent.py \
  backend/app/repositories/memory_repository.py \
  backend/app/repositories/memory_graph_episode_repository.py \
  backend/app/services/graph_history_service.py \
  backend/app/services/graph_history_entity_resolver.py \
  backend/app/services/graph_history_entity_aggregator.py \
  backend/app/services/graph_history_relation_topic_resolver.py \
  backend/app/services/history_query_planner.py \
  backend/app/services/history_evidence_composer.py \
  backend/app/workflow/nodes/agent_node.py \
  backend/app/workflow/canvas_factory.py \
  backend/tests/services/test_graph_history_service.py \
  backend/tests/services/test_graph_history_tool.py \
  backend/tests/services/test_graph_history_entity_resolver.py \
  backend/tests/services/test_graph_history_entity_aggregator.py \
  backend/tests/services/test_history_query_planner.py \
  backend/tests/services/test_history_evidence_composer.py \
  backend/tests/workflow/test_agent_history_orchestration.py
git commit -m "feat: implement graph history v2 and v3 planning architecture"
```

---

## Self-Review

### Spec coverage check

- **V2 entity-history** → covered by Tasks 1-6
  - entity resolver: Task 3
  - entity history aggregator: Tasks 2 and 4
  - `target_type='entity'` service path: Task 5
  - agent/tool routing and contract: Task 6
  - ambiguity + insufficient evidence semantics: Tasks 1, 3, 5
- **V3 relation/topic-history + stronger Agentic RAG** → covered by Tasks 7-11
  - relation/topic resolver: Task 7
  - history query planner: Task 8
  - multi-hop evidence composer: Task 9
  - `target_type='relation_topic'` service path: Task 10
  - current + history orchestration: Task 11
- **Current-truth / history-truth boundary** → reinforced in notes plus Tasks 6, 8, 11
- **Regression protection for V1** → Task 12 explicitly keeps V1 focused tests in the final verification suite

### Placeholder scan

- Replaced generic “add tests” wording with concrete file paths, test code, commands, and expected results.
- No `TODO`, `TBD`, or “similar to previous task” placeholders remain.

### Type consistency check

- `GraphHistoryResolvedTarget`, `GraphHistoryResult`, `GraphHistoryEntityResolver`, `GraphHistoryEntityAggregator`, `GraphHistoryRelationTopicResolver`, `HistoryQueryPlanner`, and `HistoryEvidenceComposer` use consistent names across tasks.
- Status values match the spec-driven expansion: `ok`, `not_found`, `insufficient_history`, `unsupported_target_type`, `insufficient_evidence`, `ambiguous_target`, `error`.
