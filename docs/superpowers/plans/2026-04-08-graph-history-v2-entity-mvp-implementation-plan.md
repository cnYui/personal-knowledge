# Graph History V2 Entity-History MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build explicit, testable `graph_history_tool(target_type='entity')` support for `timeline / compare / summarize` without changing the default current-truth-only Q&A path.

**Architecture:** Extend the existing V1 graph-history path instead of replacing it. `GraphHistoryService` remains the single entry point and adds an entity branch that resolves a user-provided entity target, aggregates matching memory/version events through repository helpers, and returns the existing result structure with a small set of V2-only schema/status extensions.

**Tech Stack:** Python, FastAPI service layer, SQLAlchemy ORM, Pydantic, pytest, existing agent tool/workflow stack.

---

## Scope Check

This plan covers only the approved V2 entity-history MVP from `docs/superpowers/specs/2026-04-08-graph-history-v2-entity-mvp-design.md`.

It intentionally does **not** include:

- `relation_topic` implementation
- planner / composer / multi-hop orchestration
- automatic history-tool routing in default Q&A
- always-on history injection into prompts or overlays
- V3-only output fields such as `turning_points`, `confidence`, or `evidence_groups`

That separation is correct for this spec. V3 should get its own follow-up plan.

## File Structure

### Files to create

- `backend/app/services/graph_history_entity_resolver.py`
  - Resolve `target_value` to a canonical entity target using exact / alias matching with safe ambiguity handling.
- `backend/app/services/graph_history_entity_aggregator.py`
  - Aggregate entity-scoped history events across matching memories and their graph episodes.
- `backend/tests/services/test_graph_history_entity_resolver.py`
  - Unit tests for exact match, alias match, ambiguity, normalization, and not-found cases.
- `backend/tests/services/test_graph_history_entity_aggregator.py`
  - Unit tests for cross-memory aggregation, ordering, truncation, counting, stable ordering ties, and empty results.

### Files to modify

- `backend/app/schemas/agent.py`
  - Extend `GraphHistoryResolvedTarget` and `GraphHistoryResult.status` for V2 entity-history semantics only.
- `backend/app/repositories/memory_repository.py`
  - Add minimal entity-oriented lookup helpers for matching memories by keyword/alias.
- `backend/app/repositories/memory_graph_episode_repository.py`
  - Add aggregation helpers for listing/counting version rows across multiple memories.
- `backend/app/services/graph_history_service.py`
  - Preserve V1 `memory` behavior and add an `entity` query path while leaving `relation_topic` unsupported.
- `backend/app/services/agent_tools/graph_history_tool.py`
  - Keep the tool thin, but update descriptive text to mention entity-history support.
- `backend/tests/services/test_graph_history_service.py`
  - Add V2 entity-history coverage while preserving existing V1 regression tests.
- `backend/tests/services/test_graph_history_tool.py`
  - Add schema/contract checks for V2 fields/statuses and entity constraint passthrough.
- `backend/app/workflow/nodes/agent_node.py`
  - Add descriptive tool-schema support for `graph_history_tool` and include `entity` in the documented enum without adding orchestration logic.

### Files to inspect while implementing

- `docs/superpowers/specs/2026-04-08-graph-history-v2-entity-mvp-design.md`
- `backend/app/services/graph_history_service.py`
- `backend/tests/services/test_graph_history_service.py`
- `backend/tests/services/test_graph_history_tool.py`
- `backend/app/workflow/nodes/agent_node.py`

## Implementation Notes Before Starting

- Keep V1 memory-history tests green after every task.
- Fail safely for ambiguous entities by default.
- Keep repository helpers small and reusable; do not push SQL into workflow code.
- Keep `GraphHistoryTool` thin; business logic belongs in service / resolver / aggregator layers.
- Do not introduce V3 data structures or behavior “for later convenience.”

---

### Task 1: Extend graph-history schemas for V2 entity semantics

**Files:**
- Modify: `backend/app/schemas/agent.py`
- Test: `backend/tests/services/test_graph_history_tool.py`

- [ ] **Step 1: Write the failing schema tests**

```python
from app.schemas.agent import GraphHistoryQuery, GraphHistoryResolvedTarget, GraphHistoryResult


def test_graph_history_query_supports_entity_constraints():
    query = GraphHistoryQuery(
        target_type='entity',
        target_value='OpenAI',
        mode='timeline',
        constraints={
            'entity_match_mode': 'alias',
            'top_k_events': 5,
            'include_related_memories': True,
            'disambiguation_policy': 'fail',
            'time_range': {'start': '2024-01-01', 'end': '2024-12-31'},
        },
    )

    assert query.target_type == 'entity'
    assert query.constraints['entity_match_mode'] == 'alias'
    assert query.constraints['top_k_events'] == 5
    assert query.constraints['include_related_memories'] is True


def test_graph_history_result_supports_entity_resolved_target_and_new_statuses():
    result = GraphHistoryResult(
        target_type='entity',
        target_value='Apple',
        mode='timeline',
        status='ambiguous_target',
        resolved_target=GraphHistoryResolvedTarget(
            entity_id='entity-apple',
            canonical_name=None,
            matched_alias=None,
            candidate_count=2,
        ),
    )

    assert result.status == 'ambiguous_target'
    assert result.resolved_target is not None
    assert result.resolved_target.entity_id == 'entity-apple'
    assert result.resolved_target.candidate_count == 2


def test_graph_history_result_supports_insufficient_evidence_status():
    result = GraphHistoryResult(
        target_type='entity',
        target_value='OpenAI',
        mode='summarize',
        status='insufficient_evidence',
    )

    assert result.status == 'insufficient_evidence'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_graph_history_tool.py -v`
Expected: FAIL because `GraphHistoryResolvedTarget` does not yet contain entity fields and `GraphHistoryResult.status` does not yet include `ambiguous_target` or `insufficient_evidence`.

- [ ] **Step 3: Write minimal implementation**

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
        'ambiguous_target',
        'insufficient_evidence',
        'error',
    ]
    timeline: list[GraphHistoryTimelineItem] = Field(default_factory=list)
    comparisons: list[GraphHistoryComparisonItem] = Field(default_factory=list)
    summary: str = ''
    evidence: list[GraphHistoryEvidenceItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/services/test_graph_history_tool.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/agent.py backend/tests/services/test_graph_history_tool.py
git commit -m "feat: extend graph history schemas for entity history"
```

### Task 2: Add repository helpers for entity memory lookup and multi-memory episode aggregation

**Files:**
- Modify: `backend/app/repositories/memory_repository.py`
- Modify: `backend/app/repositories/memory_graph_episode_repository.py`
- Test: `backend/tests/services/test_graph_history_entity_aggregator.py`

- [ ] **Step 1: Write the failing repository/aggregator tests**

```python
from datetime import datetime, timezone

from app.models.memory import Memory, MemoryGraphEpisode
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository
from app.repositories.memory_repository import MemoryRepository
from app.services.graph_history_entity_aggregator import GraphHistoryEntityAggregator


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


def test_collect_entity_events_uses_stable_memory_id_tiebreaker_for_tied_rows(db_session):
    tied_time = datetime(2026, 4, 7, 0, 0, tzinfo=timezone.utc)
    memory_a = Memory(id='aaa-memory', title='OpenAI Alpha', title_status='ready', content='OpenAI alpha event', group_id='default')
    memory_b = Memory(id='zzz-memory', title='OpenAI Zeta', title_status='ready', content='OpenAI zeta event', group_id='default')
    db_session.add_all([memory_a, memory_b])
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory_a.id, episode_uuid='alpha-v1', version=1, chunk_index=0, is_latest=True, created_at=tied_time),
            MemoryGraphEpisode(memory_id=memory_b.id, episode_uuid='zeta-v1', version=1, chunk_index=0, is_latest=True, created_at=tied_time),
        ]
    )
    db_session.commit()

    aggregator = GraphHistoryEntityAggregator(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
    )

    events = aggregator.collect_entity_events(db_session, canonical_name='OpenAI', top_k_events=10)

    assert [event['memory_id'] for event in events] == ['aaa-memory', 'zzz-memory']
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_graph_history_entity_aggregator.py -v`
Expected: FAIL because repository helpers and the aggregator do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class MemoryRepository:
    def list_entity_memory_refs(self, db: Session, keyword: str, limit: int | None = 20) -> list[dict[str, str]]:
        query = select(Memory.id, Memory.title).where(
            or_(Memory.title.ilike(f'%{keyword}%'), Memory.content.ilike(f'%{keyword}%'))
        )
        query = query.order_by(Memory.updated_at.desc(), Memory.created_at.desc(), Memory.id.asc())
        if limit is not None:
            query = query.limit(limit)
        return [
            {'id': row.id, 'title': row.title}
            for row in db.execute(query)
        ]

    def list_entity_memory_ids(self, db: Session, keyword: str) -> list[str]:
        return [item['id'] for item in self.list_entity_memory_refs(db, keyword, limit=None)]


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
            .order_by(
                func.max(MemoryGraphEpisode.reference_time).desc().nullslast(),
                func.max(MemoryGraphEpisode.created_at).desc().nullslast(),
                MemoryGraphEpisode.version.desc(),
                MemoryGraphEpisode.memory_id.asc(),
            )
        )
        return [dict(row._mapping) for row in rows]

    def count_versions_for_memories(self, db: Session, memory_ids: list[str]) -> int:
        if not memory_ids:
            return 0
        return int(
            db.scalar(
                select(func.count())
                .select_from(
                    select(MemoryGraphEpisode.memory_id, MemoryGraphEpisode.version)
                    .where(MemoryGraphEpisode.memory_id.in_(memory_ids))
                    .group_by(MemoryGraphEpisode.memory_id, MemoryGraphEpisode.version)
                    .subquery()
                )
            )
            or 0
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/services/test_graph_history_entity_aggregator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/memory_repository.py backend/app/repositories/memory_graph_episode_repository.py backend/tests/services/test_graph_history_entity_aggregator.py
git commit -m "feat: add repository helpers for entity history aggregation"
```

### Task 3: Implement entity resolver with exact, alias, ambiguous, and not-found outcomes

**Files:**
- Create: `backend/app/services/graph_history_entity_resolver.py`
- Test: `backend/tests/services/test_graph_history_entity_resolver.py`

- [ ] **Step 1: Write the failing resolver tests**

```python
from app.services.graph_history_entity_resolver import GraphHistoryEntityResolver


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


def test_entity_resolver_returns_not_found():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['Open AI']})

    resolved = resolver.resolve('Anthropic')

    assert resolved.status == 'not_found'
    assert resolved.canonical_name is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_graph_history_entity_resolver.py -v`
Expected: FAIL because `GraphHistoryEntityResolver` does not exist.

- [ ] **Step 3: Write minimal implementation**

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
            return EntityResolution(
                status='ambiguous_target',
                disambiguation_candidates=list(matches),
            )

        canonical_name, alias = next(iter(matches.items()))
        return EntityResolution(status='ok', canonical_name=canonical_name, matched_alias=alias)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/services/test_graph_history_entity_resolver.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_entity_resolver.py backend/tests/services/test_graph_history_entity_resolver.py
git commit -m "feat: add graph history entity resolver"
```

### Task 4: Implement entity aggregator on top of repository helpers

**Files:**
- Create: `backend/app/services/graph_history_entity_aggregator.py`
- Test: `backend/tests/services/test_graph_history_entity_aggregator.py`

- [ ] **Step 1: Write the failing aggregator tests**

```python
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository
from app.repositories.memory_repository import MemoryRepository
from app.services.graph_history_entity_aggregator import GraphHistoryEntityAggregator


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


def test_count_entity_events_counts_all_versions_across_more_than_ten_matching_memories(db_session):
    aggregator = GraphHistoryEntityAggregator(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
    )

    assert aggregator.count_entity_events(db_session, canonical_name='OpenAI') == 11
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_graph_history_entity_aggregator.py -v`
Expected: FAIL because `GraphHistoryEntityAggregator` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
from sqlalchemy.orm import Session

from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository
from app.repositories.memory_repository import MemoryRepository


class GraphHistoryEntityAggregator:
    def __init__(
        self,
        *,
        memory_repository: MemoryRepository,
        episode_repository: MemoryGraphEpisodeRepository,
    ) -> None:
        self.memory_repository = memory_repository
        self.episode_repository = episode_repository

    def count_entity_events(self, db: Session, canonical_name: str) -> int:
        memory_ids = self.memory_repository.list_entity_memory_ids(db, canonical_name)
        if not memory_ids:
            return 0
        return self.episode_repository.count_versions_for_memories(db, memory_ids)

    def collect_entity_events(self, db: Session, canonical_name: str, top_k_events: int | None = 10) -> list[dict]:
        memory_limit = None if top_k_events is None else max(top_k_events, 10)
        memory_refs = self.memory_repository.list_entity_memory_refs(db, canonical_name, limit=memory_limit)
        if not memory_refs:
            return []

        memory_map = {item['id']: item['title'] for item in memory_refs}
        version_rows = self.episode_repository.list_versions_for_memories(db, list(memory_map.keys()))
        events = [
            {
                'memory_id': row['memory_id'],
                'memory_title': memory_map[row['memory_id']],
                'version': row['version'],
                'reference_time': row['reference_time'],
                'created_at': row['created_at'],
            }
            for row in version_rows
        ]

        if top_k_events is None:
            return events
        return events[:top_k_events]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/services/test_graph_history_entity_aggregator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_entity_aggregator.py backend/tests/services/test_graph_history_entity_aggregator.py
git commit -m "feat: add graph history entity aggregator"
```

### Task 5: Add `entity` query routing to `GraphHistoryService`

**Files:**
- Modify: `backend/app/services/graph_history_service.py`
- Modify: `backend/tests/services/test_graph_history_service.py`

- [ ] **Step 1: Write the failing service tests**

```python
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository
from app.repositories.memory_repository import MemoryRepository
from app.schemas.agent import GraphHistoryQuery
from app.services.graph_history_entity_aggregator import GraphHistoryEntityAggregator
from app.services.graph_history_entity_resolver import GraphHistoryEntityResolver
from app.services.graph_history_service import GraphHistoryService


def test_query_entity_timeline_returns_aggregated_events(db_session):
    service = GraphHistoryService(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
        db_factory=lambda: db_session,
        entity_resolver=GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI', 'Open AI']}),
        entity_aggregator=GraphHistoryEntityAggregator(
            memory_repository=MemoryRepository(),
            episode_repository=MemoryGraphEpisodeRepository(),
        ),
    )

    result = service.query(
        GraphHistoryQuery(
            target_type='entity',
            target_value='Open AI',
            mode='timeline',
            question='这个实体如何演化？',
            constraints={'top_k_events': 10},
        )
    )

    assert result.status == 'ok'
    assert result.resolved_target is not None
    assert result.resolved_target.canonical_name == 'OpenAI'
    assert result.resolved_target.matched_alias == 'Open AI'
    assert len(result.timeline) == 2


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
    assert result.resolved_target is not None
    assert result.resolved_target.candidate_count == 2


def test_query_entity_returns_insufficient_evidence_when_no_events_are_found(db_session):
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
        GraphHistoryQuery(target_type='entity', target_value='OpenAI', mode='timeline', question='实体历史？')
    )

    assert result.status == 'insufficient_evidence'
    assert result.resolved_target is not None
    assert result.resolved_target.canonical_name == 'OpenAI'


def test_query_entity_compare_requires_at_least_two_events(db_session):
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
        GraphHistoryQuery(target_type='entity', target_value='OpenAI', mode='compare', question='比较历史')
    )

    assert result.status == 'insufficient_history'
    assert result.comparisons == []


def test_query_returns_unsupported_target_type_for_relation_topic_request(db_session):
    service = GraphHistoryService(
        memory_repository=MemoryRepository(),
        episode_repository=MemoryGraphEpisodeRepository(),
        db_factory=lambda: db_session,
    )

    result = service.query(
        GraphHistoryQuery(target_type='relation_topic', target_value='OpenAI/Microsoft', mode='timeline', question='关系历史？')
    )

    assert result.status == 'unsupported_target_type'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_graph_history_service.py -v`
Expected: FAIL because `GraphHistoryService` only supports `target_type='memory'`.

- [ ] **Step 3: Write minimal implementation**

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

    def query(self, payload: GraphHistoryQuery) -> GraphHistoryResult:
        if payload.target_type == 'memory':
            return self._query_memory(payload)
        if payload.target_type == 'entity':
            return self._query_entity(payload)
        return GraphHistoryResult(
            target_type=payload.target_type,
            target_value=payload.target_value,
            mode=payload.mode,
            status='unsupported_target_type',
        )

    def _query_entity(self, payload: GraphHistoryQuery) -> GraphHistoryResult:
        db = self.db_factory()
        try:
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
                        entity_id=f"entity-{payload.target_value.lower()}",
                        canonical_name=None,
                        matched_alias=None,
                        candidate_count=len(resolved.disambiguation_candidates),
                    ),
                    warnings=['目标存在多个高置信候选，请先澄清实体。'],
                )

            total_event_count = self.entity_aggregator.count_entity_events(db, resolved.canonical_name)
            events = self.entity_aggregator.collect_entity_events(
                db,
                canonical_name=resolved.canonical_name,
                top_k_events=payload.constraints.get('top_k_events', 10),
            )
            resolved_target = GraphHistoryResolvedTarget(
                entity_id=f"entity-{resolved.canonical_name.lower()}",
                canonical_name=resolved.canonical_name,
                matched_alias=resolved.matched_alias,
                version_count=total_event_count,
                candidate_count=1,
            )
            if not events:
                return GraphHistoryResult(
                    target_type='entity',
                    target_value=payload.target_value,
                    mode=payload.mode,
                    status='insufficient_evidence',
                    resolved_target=resolved_target,
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

            if payload.mode == 'timeline':
                return GraphHistoryResult(
                    target_type='entity',
                    target_value=payload.target_value,
                    mode='timeline',
                    status='ok',
                    resolved_target=resolved_target,
                    timeline=timeline,
                )

            if len(events) < 2:
                return GraphHistoryResult(
                    target_type='entity',
                    target_value=payload.target_value,
                    mode=payload.mode,
                    status='insufficient_history',
                    resolved_target=resolved_target,
                    timeline=timeline,
                    warnings=['该实体缺少足够历史事件，无法进行比较。'],
                )

            comparison = GraphHistoryComparisonItem(
                from_version=events[1]['version'],
                to_version=events[0]['version'],
                change_summary=f"从 v{events[1]['version']} 演进到 v{events[0]['version']}",
                added_points=[f"最新事件：{events[0]['memory_title']}"],
                removed_points=[],
                updated_points=[],
            )
            if payload.mode == 'compare':
                return GraphHistoryResult(
                    target_type='entity',
                    target_value=payload.target_value,
                    mode='compare',
                    status='ok',
                    resolved_target=resolved_target,
                    timeline=timeline,
                    comparisons=[comparison],
                )

            return GraphHistoryResult(
                target_type='entity',
                target_value=payload.target_value,
                mode='summarize',
                status='ok',
                resolved_target=resolved_target,
                timeline=timeline,
                comparisons=[comparison],
                summary=f'{resolved.canonical_name} 共关联 {total_event_count} 条历史事件。',
            )
        finally:
            close = getattr(db, 'close', None)
            if callable(close):
                close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/services/test_graph_history_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_history_service.py backend/tests/services/test_graph_history_service.py
git commit -m "feat: add entity history support to graph history service"
```

### Task 6: Update tool contract and agent description without adding orchestration

**Files:**
- Modify: `backend/app/services/agent_tools/graph_history_tool.py`
- Modify: `backend/app/workflow/nodes/agent_node.py`
- Test: `backend/tests/services/test_graph_history_tool.py`

- [ ] **Step 1: Write the failing contract tests**

```python
from app.schemas.agent import GraphHistoryResult
from app.services.agent_tools import GraphHistoryTool
from app.workflow.nodes.agent_node import AgentNode


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
        constraints={'entity_match_mode': 'alias', 'top_k_events': 5},
    )

    assert captured['payload'].constraints['entity_match_mode'] == 'alias'
    assert captured['payload'].constraints['top_k_events'] == 5


def test_graph_history_tool_description_mentions_entity_history():
    assert 'entity' in GraphHistoryTool.description


def test_agent_node_graph_history_tool_schema_includes_entity_target_type():
    node = AgentNode(spec={'id': 'agent-1', 'type': 'agent', 'config': {}})

    schema = node._graph_history_tool_schema()

    assert schema['function']['name'] == 'graph_history_tool'
    assert schema['function']['parameters']['properties']['target_type']['enum'] == ['memory', 'entity', 'relation_topic']
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_graph_history_tool.py -v`
Expected: FAIL because the tool description still mentions only memory history and `AgentNode` does not yet expose a graph-history tool schema helper.

- [ ] **Step 3: Write minimal implementation**

```python
class GraphHistoryTool:
    name = 'graph_history_tool'
    description = 'Retrieve structured history evidence for a memory or entity from versioned graph knowledge.'
```

```python
def _graph_history_tool_schema(self) -> dict[str, Any]:
    return {
        'type': 'function',
        'function': {
            'name': 'graph_history_tool',
            'description': 'Retrieve structured history evidence for memory or entity evolution queries.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'target_type': {
                        'type': 'string',
                        'enum': ['memory', 'entity', 'relation_topic'],
                    },
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

Add the helper in `AgentNode`, but do **not** wire it into the running tool loop yet. This task is descriptive contract coverage only.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/services/test_graph_history_tool.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent_tools/graph_history_tool.py backend/app/workflow/nodes/agent_node.py backend/tests/services/test_graph_history_tool.py
git commit -m "feat: document entity history tool contract"
```

### Task 7: Run focused regression suite for V1 + V2 entity-history MVP

**Files:**
- Test: `backend/tests/services/test_graph_history_entity_resolver.py`
- Test: `backend/tests/services/test_graph_history_entity_aggregator.py`
- Test: `backend/tests/services/test_graph_history_service.py`
- Test: `backend/tests/services/test_graph_history_tool.py`

- [ ] **Step 1: Run resolver tests**

Run: `pytest backend/tests/services/test_graph_history_entity_resolver.py -v`
Expected: PASS

- [ ] **Step 2: Run aggregator tests**

Run: `pytest backend/tests/services/test_graph_history_entity_aggregator.py -v`
Expected: PASS

- [ ] **Step 3: Run service tests**

Run: `pytest backend/tests/services/test_graph_history_service.py -v`
Expected: PASS with both V1 memory-history and V2 entity-history coverage green.

- [ ] **Step 4: Run tool contract tests**

Run: `pytest backend/tests/services/test_graph_history_tool.py -v`
Expected: PASS

- [ ] **Step 5: Run the combined targeted suite**

Run: `pytest backend/tests/services/test_graph_history_entity_resolver.py backend/tests/services/test_graph_history_entity_aggregator.py backend/tests/services/test_graph_history_service.py backend/tests/services/test_graph_history_tool.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/tests/services/test_graph_history_entity_resolver.py backend/tests/services/test_graph_history_entity_aggregator.py backend/tests/services/test_graph_history_service.py backend/tests/services/test_graph_history_tool.py backend/app/schemas/agent.py backend/app/repositories/memory_repository.py backend/app/repositories/memory_graph_episode_repository.py backend/app/services/graph_history_entity_resolver.py backend/app/services/graph_history_entity_aggregator.py backend/app/services/graph_history_service.py backend/app/services/agent_tools/graph_history_tool.py backend/app/workflow/nodes/agent_node.py
git commit -m "test: verify graph history entity MVP regression suite"
```

## Self-Review

### 1. Spec coverage

- Explicit `graph_history_tool(target_type='entity')` path: covered by Tasks 5 and 6.
- `timeline / compare / summarize` on entity target: covered by Task 5 tests and implementation.
- Resolver outcomes `ok / not_found / ambiguous_target`: covered by Task 3 and Task 5.
- Aggregation across memories/versions: covered by Tasks 2 and 4.
- `top_k_events`: covered by Tasks 2, 4, and 5.
- `insufficient_history`: covered by Task 5.
- `insufficient_evidence`: covered by Tasks 1 and 5.
- Keep `relation_topic` unsupported: covered by Task 5.
- Preserve V1 memory-history behavior: covered by Task 7 regression runs.
- Agent-side descriptive support only, no orchestration: covered by Task 6.

No uncovered V2 spec requirements remain.

### 2. Placeholder scan

Checked for placeholder-style failures (`TBD`, `TODO`, “implement later”, vague “add tests”, vague “handle edge cases”). None remain.

### 3. Type consistency

- `GraphHistoryResolvedTarget` entity fields are consistent across Tasks 1 and 5.
- `ambiguous_target` and `insufficient_evidence` status names are consistent across Tasks 1, 3, and 5.
- `list_entity_memory_refs`, `list_entity_memory_ids`, `list_versions_for_memories`, and `count_versions_for_memories` are named consistently across Tasks 2, 4, and 5.
- `AgentNode._graph_history_tool_schema()` is referenced consistently in Task 6.

Plan reviewed and internally consistent.