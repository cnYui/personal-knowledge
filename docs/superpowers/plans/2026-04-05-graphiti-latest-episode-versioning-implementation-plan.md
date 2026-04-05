# Graphiti Latest Episode Versioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build versioned Graphiti episode tracking so one memory can own multiple episode chunks across multiple graph-ingest versions, while retrieval only uses the latest version by default.

**Architecture:** Keep Graphiti as the source of raw temporal knowledge, and add an application-side `memory_graph_episodes` table to define which episode records are currently valid. Ingestion writes a new version worth of episode rows, then atomically flips latest markers only after the full new version succeeds; retrieval filters Graphiti search results through this table before building answer context.

**Tech Stack:** FastAPI, SQLAlchemy ORM, Alembic, pytest, Graphiti SDK mocks, Pydantic

---

## File Map

### Create

- `backend/alembic/versions/<new_revision>_add_memory_graph_episodes_table.py` — creates `memory_graph_episodes`, indexes, and backfills minimal compatibility rows from `memories.graph_episode_uuid`
- `backend/app/repositories/memory_graph_episode_repository.py` — encapsulates version lookup, row creation, latest switching, and episode lookup helpers
- `backend/tests/repositories/test_memory_graph_episode_repository.py` — repository-level tests for versioning and latest switching

### Modify

- `backend/app/models/memory.py` — add `MemoryGraphEpisode` ORM model and relationships from `Memory`
- `backend/app/services/knowledge_graph_service.py` — add latest-episode filtering to retrieval flow
- `backend/app/workers/graphiti_ingest_worker.py` — record episode versions, use `updated_at or created_at`, and perform two-phase latest switching
- `backend/tests/test_models.py` — verify new ORM model and relationships exist
- `backend/tests/workers/test_graphiti_ingest_worker.py` — add worker tests for version creation, latest flip, failure safety, and updated reference time
- `backend/tests/services/test_graph_retrieval_tool.py` — add retrieval filtering tests

### Maybe Modify After Inspecting During Execution

- `backend/app/schemas/agent.py` — only if `GraphRetrievalResult` needs extra debugging metadata; avoid if not required
- `backend/tests/integration/test_graphiti_integration.py` — add a narrow integration assertion if repository-backed filtering is easy to verify without making tests brittle

---

### Task 1: Add ORM model for versioned memory episodes

**Files:**
- Modify: `backend/app/models/memory.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing model test**

```python
from app.models.memory import Memory, MemoryGraphEpisode


def test_memory_graph_episode_model_has_expected_fields_and_relationships():
    memory = Memory(title="Test", title_status="ready", content="Body", group_id="default")
    episode = MemoryGraphEpisode(
        memory=memory,
        episode_uuid="episode-1",
        version=1,
        chunk_index=0,
        is_latest=True,
    )

    assert episode.memory is memory
    assert episode.episode_uuid == "episode-1"
    assert episode.version == 1
    assert episode.chunk_index == 0
    assert episode.is_latest is True
    assert hasattr(episode, "reference_time")
    assert hasattr(episode, "created_at")
    assert hasattr(memory, "graph_episodes")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_models.py::test_memory_graph_episode_model_has_expected_fields_and_relationships -v`
Expected: FAIL with import error or missing `MemoryGraphEpisode` / `graph_episodes`

- [ ] **Step 3: Write minimal ORM implementation**

Add this model and relationship shape to `backend/app/models/memory.py`:

```python
class Memory(Base):
    __tablename__ = "memories"

    # existing fields...
    graph_episodes: Mapped[list["MemoryGraphEpisode"]] = relationship(
        back_populates="memory",
        cascade="all, delete-orphan",
    )


class MemoryGraphEpisode(Base):
    __tablename__ = "memory_graph_episodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False)
    episode_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    is_latest: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=sa.false())
    reference_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    memory: Mapped[Memory] = relationship(back_populates="graph_episodes")
```

Use the existing import style in the file; if needed add `Boolean` and `Integer` imports from SQLAlchemy instead of raw Python types in `mapped_column` definitions.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/memory.py backend/tests/test_models.py
git commit -m "feat: add memory graph episode model"
```

### Task 2: Add Alembic migration with compatibility backfill

**Files:**
- Create: `backend/alembic/versions/<new_revision>_add_memory_graph_episodes_table.py`
- Modify: `backend/app/models/memory.py` (only if migration reveals naming mismatch)
- Test: manual migration check via Alembic command

- [ ] **Step 1: Write the migration file skeleton**

Create a new Alembic file modeled after `backend/alembic/versions/11659cef325e_add_graph_fields_to_memory.py` with this shape:

```python
"""add memory graph episodes table

Revision ID: <new_revision>
Revises: 11659cef325e
Create Date: 2026-04-05 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "<new_revision>"
down_revision: Union[str, Sequence[str], None] = "11659cef325e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

- [ ] **Step 2: Implement upgrade with table, indexes, and compatibility insert**

Put this structure into `upgrade()`:

```python
op.create_table(
    "memory_graph_episodes",
    sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
    sa.Column("memory_id", sa.String(length=36), sa.ForeignKey("memories.id"), nullable=False),
    sa.Column("episode_uuid", sa.String(length=36), nullable=False),
    sa.Column("version", sa.Integer(), nullable=False),
    sa.Column("chunk_index", sa.Integer(), nullable=False),
    sa.Column("is_latest", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("reference_time", sa.DateTime(timezone=True), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
)
op.create_index(
    "ix_memory_graph_episodes_memory_version_chunk",
    "memory_graph_episodes",
    ["memory_id", "version", "chunk_index"],
    unique=True,
)
op.create_index("ix_memory_graph_episodes_episode_uuid", "memory_graph_episodes", ["episode_uuid"], unique=False)
op.create_index("ix_memory_graph_episodes_memory_latest", "memory_graph_episodes", ["memory_id", "is_latest"], unique=False)

op.execute(
    """
    INSERT INTO memory_graph_episodes (
        id, memory_id, episode_uuid, version, chunk_index, is_latest, reference_time, created_at
    )
    SELECT
        lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || '4' || substr(lower(hex(randomblob(2))), 2) || '-' ||
        substr('89ab', abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))), 2) || '-' || lower(hex(randomblob(6))),
        id,
        graph_episode_uuid,
        1,
        0,
        1,
        COALESCE(updated_at, created_at),
        CURRENT_TIMESTAMP
    FROM memories
    WHERE graph_episode_uuid IS NOT NULL
    """
)
```

If SQLite-specific UUID generation feels too brittle for this codebase, replace the SQL backfill with row-by-row Python inside the migration using `sqlalchemy.sql.table` plus `uuid.uuid4()`.

- [ ] **Step 3: Implement downgrade**

```python
op.drop_index("ix_memory_graph_episodes_memory_latest", table_name="memory_graph_episodes")
op.drop_index("ix_memory_graph_episodes_episode_uuid", table_name="memory_graph_episodes")
op.drop_index("ix_memory_graph_episodes_memory_version_chunk", table_name="memory_graph_episodes")
op.drop_table("memory_graph_episodes")
```

- [ ] **Step 4: Run migration locally**

Run: `cd /d d:\CodeWorkSpace\personal-knowledge-base\backend && alembic upgrade head`
Expected: PASS with new revision applied and no SQL errors

- [ ] **Step 5: Sanity-check downgrade path**

Run: `cd /d d:\CodeWorkSpace\personal-knowledge-base\backend && alembic downgrade -1 && alembic upgrade head`
Expected: PASS both ways

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/*.py
git commit -m "feat: add memory graph episodes migration"
```

### Task 3: Add repository for episode versioning operations

**Files:**
- Create: `backend/app/repositories/memory_graph_episode_repository.py`
- Test: `backend/tests/repositories/test_memory_graph_episode_repository.py`

- [ ] **Step 1: Write the failing repository tests**

Create `backend/tests/repositories/test_memory_graph_episode_repository.py` with these tests:

```python
from datetime import UTC, datetime

from app.models.memory import Memory, MemoryGraphEpisode
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository


def test_get_next_version_returns_one_for_memory_without_rows(db_session):
    repo = MemoryGraphEpisodeRepository()
    memory = Memory(title="Test", title_status="ready", content="Body", group_id="default")
    db_session.add(memory)
    db_session.commit()

    assert repo.get_next_version(db_session, memory.id) == 1


def test_replace_latest_version_demotes_old_rows_and_promotes_new_rows(db_session):
    repo = MemoryGraphEpisodeRepository()
    memory = Memory(title="Test", title_status="ready", content="Body", group_id="default")
    db_session.add(memory)
    db_session.commit()

    old_row = MemoryGraphEpisode(
        memory_id=memory.id,
        episode_uuid="episode-old",
        version=1,
        chunk_index=0,
        is_latest=True,
        reference_time=datetime(2026, 4, 5, tzinfo=UTC),
    )
    db_session.add(old_row)
    db_session.commit()

    repo.replace_latest_version(
        db_session,
        memory_id=memory.id,
        version=2,
        episodes=[
            {"episode_uuid": "episode-new-1", "chunk_index": 0, "reference_time": datetime(2026, 4, 6, tzinfo=UTC)},
            {"episode_uuid": "episode-new-2", "chunk_index": 1, "reference_time": datetime(2026, 4, 6, tzinfo=UTC)},
        ],
    )

    rows = db_session.query(MemoryGraphEpisode).filter(MemoryGraphEpisode.memory_id == memory.id).order_by(MemoryGraphEpisode.version, MemoryGraphEpisode.chunk_index).all()
    assert [(row.version, row.chunk_index, row.is_latest) for row in rows] == [
        (1, 0, False),
        (2, 0, True),
        (2, 1, True),
    ]


def test_list_latest_episode_uuids_returns_lookup_map(db_session):
    repo = MemoryGraphEpisodeRepository()
    memory = Memory(title="Test", title_status="ready", content="Body", group_id="default")
    db_session.add(memory)
    db_session.commit()
    db_session.add_all([
        MemoryGraphEpisode(memory_id=memory.id, episode_uuid="episode-old", version=1, chunk_index=0, is_latest=False),
        MemoryGraphEpisode(memory_id=memory.id, episode_uuid="episode-new", version=2, chunk_index=0, is_latest=True),
    ])
    db_session.commit()

    lookup = repo.get_latest_episode_uuid_set(db_session, ["episode-old", "episode-new", "episode-missing"])
    assert lookup == {"episode-new"}
```

- [ ] **Step 2: Run repository tests to verify they fail**

Run: `pytest backend/tests/repositories/test_memory_graph_episode_repository.py -v`
Expected: FAIL because repository file does not exist

- [ ] **Step 3: Implement minimal repository**

Create `backend/app/repositories/memory_graph_episode_repository.py` with this API:

```python
from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.memory import MemoryGraphEpisode


class MemoryGraphEpisodeRepository:
    def get_next_version(self, db: Session, memory_id: str) -> int:
        current = db.scalar(
            select(func.max(MemoryGraphEpisode.version)).where(MemoryGraphEpisode.memory_id == memory_id)
        )
        return 1 if current is None else current + 1

    def replace_latest_version(self, db: Session, *, memory_id: str, version: int, episodes: list[dict]) -> list[MemoryGraphEpisode]:
        db.execute(
            update(MemoryGraphEpisode)
            .where(MemoryGraphEpisode.memory_id == memory_id, MemoryGraphEpisode.is_latest.is_(True))
            .values(is_latest=False)
        )
        rows = [
            MemoryGraphEpisode(
                memory_id=memory_id,
                episode_uuid=item["episode_uuid"],
                version=version,
                chunk_index=item["chunk_index"],
                is_latest=True,
                reference_time=item.get("reference_time"),
            )
            for item in episodes
        ]
        db.add_all(rows)
        db.flush()
        return rows

    def get_latest_episode_uuid_set(self, db: Session, episode_uuids: list[str]) -> set[str]:
        if not episode_uuids:
            return set()
        rows = db.scalars(
            select(MemoryGraphEpisode.episode_uuid).where(
                MemoryGraphEpisode.episode_uuid.in_(episode_uuids),
                MemoryGraphEpisode.is_latest.is_(True),
            )
        )
        return set(rows)
```

Keep this file focused. Do not add speculative APIs beyond what Tasks 4 and 5 need.

- [ ] **Step 4: Run repository tests to verify they pass**

Run: `pytest backend/tests/repositories/test_memory_graph_episode_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/memory_graph_episode_repository.py backend/tests/repositories/test_memory_graph_episode_repository.py
git commit -m "feat: add memory graph episode repository"
```

### Task 4: Update ingestion worker to write versions and flip latest safely

**Files:**
- Modify: `backend/app/workers/graphiti_ingest_worker.py`
- Test: `backend/tests/workers/test_graphiti_ingest_worker.py`

- [ ] **Step 1: Write the failing worker tests**

Add these tests to `backend/tests/workers/test_graphiti_ingest_worker.py`:

```python
@pytest.mark.anyio
@patch("app.workers.graphiti_ingest_worker.GraphitiClient")
@patch("app.workers.graphiti_ingest_worker.SessionLocal")
async def test_process_memory_success_persists_new_latest_version(mock_session_local, mock_graphiti_client):
    mock_db = Mock()
    mock_session_local.return_value = mock_db
    mock_memory = Mock()
    mock_memory.id = "memory-1"
    mock_memory.title = "Test Memory"
    mock_memory.content = "Test content"
    mock_memory.group_id = "default"
    mock_memory.created_at = Mock()
    mock_memory.updated_at = Mock()
    mock_repository = Mock()
    mock_repository.get.return_value = mock_memory

    mock_episode_repo = Mock()
    mock_episode_repo.get_next_version.return_value = 2

    mock_client_instance = Mock()
    mock_client_instance.add_memory_in_chunks = AsyncMock(return_value=["episode-uuid-1", "episode-uuid-2"])
    mock_graphiti_client.return_value = mock_client_instance

    worker = GraphitiIngestWorker(profile_refresh_scheduler=Mock())
    worker.repository = mock_repository
    worker.memory_graph_episode_repository = mock_episode_repo

    await worker._process_memory("memory-1")

    mock_episode_repo.replace_latest_version.assert_called_once()
    kwargs = mock_episode_repo.replace_latest_version.call_args.kwargs
    assert kwargs["memory_id"] == "memory-1"
    assert kwargs["version"] == 2
    assert [item["episode_uuid"] for item in kwargs["episodes"]] == ["episode-uuid-1", "episode-uuid-2"]
    assert mock_memory.graph_episode_uuid == "episode-uuid-1"
    assert mock_memory.graph_status == "added"


@pytest.mark.anyio
@patch("app.workers.graphiti_ingest_worker.GraphitiClient")
@patch("app.workers.graphiti_ingest_worker.SessionLocal")
async def test_process_memory_failure_does_not_flip_latest(mock_session_local, mock_graphiti_client):
    mock_db = Mock()
    mock_session_local.return_value = mock_db
    mock_memory = Mock()
    mock_memory.id = "memory-2"
    mock_memory.title = "Test Memory"
    mock_memory.content = "Test content"
    mock_memory.group_id = "default"
    mock_memory.created_at = Mock()
    mock_memory.updated_at = Mock()
    mock_repository = Mock()
    mock_repository.get.return_value = mock_memory

    mock_episode_repo = Mock()
    mock_episode_repo.get_next_version.return_value = 3

    mock_client_instance = Mock()
    mock_client_instance.add_memory_in_chunks = AsyncMock(side_effect=Exception("boom"))
    mock_graphiti_client.return_value = mock_client_instance

    worker = GraphitiIngestWorker()
    worker.repository = mock_repository
    worker.memory_graph_episode_repository = mock_episode_repo

    await worker._process_memory("memory-2")

    mock_episode_repo.replace_latest_version.assert_not_called()
    assert mock_memory.graph_status == "failed"


@pytest.mark.anyio
@patch("app.workers.graphiti_ingest_worker.GraphitiClient")
async def test_add_memory_episode_with_retry_uses_updated_reference_time_when_present(mock_graphiti_client):
    mock_client_instance = Mock()
    mock_client_instance.add_memory_episode = AsyncMock(return_value="episode-uuid-456")
    mock_graphiti_client.return_value = mock_client_instance

    worker = GraphitiIngestWorker()
    memory = Mock()
    memory.id = "memory-3"
    memory.group_id = "default"
    memory.created_at = Mock(name="created_at")
    memory.updated_at = Mock(name="updated_at")
    memory.graph_error = None
    db = Mock()

    await worker._add_memory_episode_with_retry(db=db, memory=memory, title="标题", content="内容")

    assert mock_client_instance.add_memory_episode.await_args.kwargs["created_at"] is memory.updated_at
```

- [ ] **Step 2: Run worker tests to verify they fail**

Run: `pytest backend/tests/workers/test_graphiti_ingest_worker.py -v`
Expected: FAIL because repository dependency and updated reference-time behavior do not exist yet

- [ ] **Step 3: Implement minimal worker changes**

Make these changes in `backend/app/workers/graphiti_ingest_worker.py`:

```python
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository


class GraphitiIngestWorker:
    def __init__(..., profile_refresh_scheduler: AgentKnowledgeProfileRefreshScheduler | None = None):
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.running = False
        self.graphiti_client = GraphitiClient()
        self.repository = MemoryRepository()
        self.memory_graph_episode_repository = MemoryGraphEpisodeRepository()
        self.profile_refresh_scheduler = profile_refresh_scheduler or agent_knowledge_profile_refresh_scheduler
        self._task = None

    async def _process_memory(self, memory_id: str):
        db = SessionLocal()
        try:
            memory = self.repository.get(db, memory_id)
            if not memory:
                logger.error(f"Memory {memory_id} not found")
                return

            memory.graph_error = None
            db.commit()

            next_version = self.memory_graph_episode_repository.get_next_version(db, memory.id)
            reference_time = memory.updated_at or memory.created_at
            episode_uuids = await self.graphiti_client.add_memory_in_chunks(
                memory_id=memory.id,
                title=memory.title,
                content=memory.content,
                group_id=memory.group_id,
                created_at=reference_time,
                episode_adder=lambda chunk_title, chunk_content: self._add_memory_episode_with_retry(
                    db=db,
                    memory=memory,
                    title=chunk_title,
                    content=chunk_content,
                ),
            )

            self.memory_graph_episode_repository.replace_latest_version(
                db,
                memory_id=memory.id,
                version=next_version,
                episodes=[
                    {"episode_uuid": episode_uuid, "chunk_index": index, "reference_time": reference_time}
                    for index, episode_uuid in enumerate(episode_uuids)
                ],
            )

            memory.graph_status = "added"
            memory.graph_episode_uuid = episode_uuids[0] if episode_uuids else None
            memory.graph_added_at = datetime.now()
            memory.graph_error = None
            db.commit()
        except Exception as e:
            ...

    async def _attempt_single_chunk_with_retries(...):
        reference_time = memory.updated_at or memory.created_at
        return await asyncio.wait_for(
            self.graphiti_client.add_memory_episode(
                memory_id=memory.id,
                title=title,
                content=content,
                group_id=memory.group_id,
                created_at=reference_time,
            ),
            timeout=GRAPH_BUILD_TIMEOUT_SECONDS,
        )
```

Important: do not call `replace_latest_version()` before `add_memory_in_chunks()` finishes successfully.

- [ ] **Step 4: Run worker tests to verify they pass**

Run: `pytest backend/tests/workers/test_graphiti_ingest_worker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/workers/graphiti_ingest_worker.py backend/tests/workers/test_graphiti_ingest_worker.py
git commit -m "feat: version graph ingestion episodes"
```

### Task 5: Filter retrieval results to latest episodes only

**Files:**
- Modify: `backend/app/services/knowledge_graph_service.py`
- Modify: `backend/app/services/agent_tools/graph_retrieval_tool.py` (only if constructor wiring changes)
- Test: `backend/tests/services/test_graph_retrieval_tool.py`

- [ ] **Step 1: Write the failing retrieval tests**

Add these tests to `backend/tests/services/test_graph_retrieval_tool.py`:

```python
@pytest.mark.asyncio
@pytest.mark.anyio
async def test_retrieve_graph_context_filters_out_non_latest_episode_results():
    latest_edge = SimpleNamespace(
        uuid="edge-new",
        fact="Alice likes green tea",
        source_node=SimpleNamespace(name="Alice", summary="喜欢喝茶"),
        target_node=SimpleNamespace(name="Green Tea", summary="一种饮品"),
        episode_uuid="episode-new",
    )
    old_edge = SimpleNamespace(
        uuid="edge-old",
        fact="Alice likes coffee",
        source_node=SimpleNamespace(name="Alice", summary="喜欢喝茶"),
        target_node=SimpleNamespace(name="Coffee", summary="一种饮品"),
        episode_uuid="episode-old",
    )

    async def fake_search(query: str, group_id: str = "default", limit: int = 5):
        return [old_edge, latest_edge]

    class StubEpisodeRepo:
        def get_latest_episode_uuid_set(self, db, episode_uuids):
            assert set(episode_uuids) == {"episode-old", "episode-new"}
            return {"episode-new"}

    service = KnowledgeGraphService.__new__(KnowledgeGraphService)
    service.graphiti_client = SimpleNamespace(search=fake_search)
    service.memory_graph_episode_repository = StubEpisodeRepo()
    service._get_db_session = lambda: SimpleNamespace(close=lambda: None)

    result = await service.retrieve_graph_context("Alice 喜欢什么？")

    assert result.has_enough_evidence is True
    assert result.retrieved_edge_count == 1
    assert "Alice likes green tea" in result.context
    assert "Alice likes coffee" not in result.context


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_retrieve_graph_context_returns_empty_when_latest_filter_removes_all_results():
    edge = SimpleNamespace(
        fact="Alice likes coffee",
        source_node=SimpleNamespace(name="Alice", summary="喜欢喝茶"),
        target_node=SimpleNamespace(name="Coffee", summary="一种饮品"),
        episode_uuid="episode-old",
    )

    async def fake_search(query: str, group_id: str = "default", limit: int = 5):
        return [edge]

    class StubEpisodeRepo:
        def get_latest_episode_uuid_set(self, db, episode_uuids):
            return set()

    service = KnowledgeGraphService.__new__(KnowledgeGraphService)
    service.graphiti_client = SimpleNamespace(search=fake_search)
    service.memory_graph_episode_repository = StubEpisodeRepo()
    service._get_db_session = lambda: SimpleNamespace(close=lambda: None)

    result = await service.retrieve_graph_context("Alice 喜欢什么？")

    assert result.has_enough_evidence is False
    assert result.retrieved_edge_count == 0
    assert result.empty_reason == "图谱中没有足够信息"
```

- [ ] **Step 2: Run retrieval tests to verify they fail**

Run: `pytest backend/tests/services/test_graph_retrieval_tool.py -v`
Expected: FAIL because retrieval path does not yet filter by latest episode UUIDs

- [ ] **Step 3: Implement minimal retrieval filtering**

In `backend/app/services/knowledge_graph_service.py`, add a repository dependency and helper methods:

```python
from app.core.database import SessionLocal
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository


class KnowledgeGraphService:
    def __init__(..., model_config_service_instance: ModelConfigService | None = None):
        ...
        self.memory_graph_episode_repository = MemoryGraphEpisodeRepository()

    def _get_db_session(self):
        return SessionLocal()

    def _extract_episode_uuid(self, edge) -> str | None:
        if getattr(edge, "episode_uuid", None):
            return edge.episode_uuid
        episode = getattr(edge, "episode", None)
        if episode and getattr(episode, "uuid", None):
            return episode.uuid
        return None

    def _filter_latest_edges(self, db, edges):
        edge_pairs = []
        for edge in edges:
            episode_uuid = self._extract_episode_uuid(edge)
            if not episode_uuid:
                edge_pairs.append((edge, None))
            else:
                edge_pairs.append((edge, episode_uuid))
        latest_uuids = self.memory_graph_episode_repository.get_latest_episode_uuid_set(
            db,
            [episode_uuid for _, episode_uuid in edge_pairs if episode_uuid],
        )
        filtered = []
        for edge, episode_uuid in edge_pairs:
            if episode_uuid is None or episode_uuid in latest_uuids:
                filtered.append(edge)
        return filtered

    async def retrieve_graph_context(self, query: str, group_id: str = "default") -> GraphRetrievalResult:
        edges = await self.graphiti_client.search(query, group_id=group_id, limit=5)
        db = self._get_db_session()
        try:
            edges = self._filter_latest_edges(db, edges)
        finally:
            db.close()
        ...
        return GraphRetrievalResult(..., retrieved_edge_count=len(edges), ...)
```

Keep the fallback behavior from the spec: if latest filtering removes everything, return the existing empty result shape instead of reintroducing historical edges.

- [ ] **Step 4: Run retrieval tests to verify they pass**

Run: `pytest backend/tests/services/test_graph_retrieval_tool.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/knowledge_graph_service.py backend/tests/services/test_graph_retrieval_tool.py
git commit -m "feat: filter graph retrieval to latest episodes"
```

### Task 6: Add end-to-end verification for model + repository + worker + retrieval slice

**Files:**
- Modify: `backend/tests/workers/test_graphiti_ingest_worker.py`
- Modify: `backend/tests/services/test_graph_retrieval_tool.py`
- Maybe Modify: `backend/tests/integration/test_graphiti_integration.py`

- [ ] **Step 1: Run the focused test suite and capture failures**

Run: `pytest backend/tests/test_models.py backend/tests/repositories/test_memory_graph_episode_repository.py backend/tests/workers/test_graphiti_ingest_worker.py backend/tests/services/test_graph_retrieval_tool.py -v`
Expected: PASS after Tasks 1-5, or expose any remaining consistency gaps

- [ ] **Step 2: Add one worker regression test for chunk index ordering if missing**

If not already covered, add:

```python
assert [(item["chunk_index"], item["episode_uuid"]) for item in kwargs["episodes"]] == [
    (0, "episode-uuid-1"),
    (1, "episode-uuid-2"),
]
```

in `test_process_memory_success_persists_new_latest_version`.

- [ ] **Step 3: Add one retrieval regression test for edges without episode UUIDs**

Add this test if it does not already exist:

```python
@pytest.mark.asyncio
@pytest.mark.anyio
async def test_retrieve_graph_context_keeps_edges_without_episode_uuid_for_compatibility():
    edge = SimpleNamespace(
        fact="Alice likes green tea",
        source_node=SimpleNamespace(name="Alice", summary="喜欢喝茶"),
        target_node=SimpleNamespace(name="Green Tea", summary="一种饮品"),
    )

    async def fake_search(query: str, group_id: str = "default", limit: int = 5):
        return [edge]

    class StubEpisodeRepo:
        def get_latest_episode_uuid_set(self, db, episode_uuids):
            assert episode_uuids == []
            return set()

    service = KnowledgeGraphService.__new__(KnowledgeGraphService)
    service.graphiti_client = SimpleNamespace(search=fake_search)
    service.memory_graph_episode_repository = StubEpisodeRepo()
    service._get_db_session = lambda: SimpleNamespace(close=lambda: None)

    result = await service.retrieve_graph_context("Alice 喜欢什么？")

    assert result.has_enough_evidence is True
    assert result.retrieved_edge_count == 1
```

- [ ] **Step 4: Re-run focused tests**

Run: `pytest backend/tests/test_models.py backend/tests/repositories/test_memory_graph_episode_repository.py backend/tests/workers/test_graphiti_ingest_worker.py backend/tests/services/test_graph_retrieval_tool.py -v`
Expected: PASS

- [ ] **Step 5: Run broader graph-related regression suite**

Run: `pytest backend/tests/test_memories_graph.py backend/tests/workflow/nodes/test_retrieval_node.py backend/tests/workflow/nodes/test_agent_node.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/tests/workers/test_graphiti_ingest_worker.py backend/tests/services/test_graph_retrieval_tool.py backend/tests/test_models.py backend/tests/repositories/test_memory_graph_episode_repository.py
git commit -m "test: cover latest graph episode versioning"
```

### Task 7: Final verification and documentation sync

**Files:**
- Modify: `docs/superpowers/specs/2026-04-05-graphiti-latest-episode-versioning-design.md` (only if implementation deviates)
- No code changes expected if implementation matches plan

- [ ] **Step 1: Run full backend test command for confidence**

Run: `cd /d d:\CodeWorkSpace\personal-knowledge-base\backend && pytest -q`
Expected: PASS, or only pre-existing unrelated failures that must be documented before completion

- [ ] **Step 2: Check git diff against spec intent**

Run: `git diff --stat HEAD~4..HEAD`
Expected: shows migration, model, repository, worker, and retrieval changes only

- [ ] **Step 3: If implementation required any spec deviation, patch the spec**

Use a minimal doc patch like:

```markdown
- Retrieval keeps edges without an extractable `episode_uuid` for backward compatibility until Graphiti search metadata is fully normalized.
```

Only do this if the code actually behaves that way.

- [ ] **Step 4: Create final verification commit if docs changed**

```bash
git add docs/superpowers/specs/2026-04-05-graphiti-latest-episode-versioning-design.md
git commit -m "docs: align graphiti versioning spec with implementation"
```

Skip this commit if no docs changed.

---

## Self-Review

### 1. Spec coverage

- `memory_graph_episodes` table, indexes, and compatibility backfill: covered by **Task 2**.
- ORM model + relationship support for one memory to many episode rows: covered by **Task 1**.
- Version lookup and latest replacement semantics: covered by **Task 3**.
- Ingest writes new version and flips latest only after full success: covered by **Task 4**.
- Edit re-ingest uses `updated_at or created_at`: covered by **Task 4**.
- Retrieval keeps only latest episodes by default: covered by **Task 5**.
- Empty-result fallback instead of auto-mixing history: covered by **Task 5**.
- Test coverage for success, failure, latest filtering, compatibility behavior: covered by **Task 6**.

No uncovered spec requirement remains.

### 2. Placeholder scan

- Removed vague steps like “add tests” and replaced them with concrete tests, commands, and code.
- Every code-changing step names exact files and includes implementation shape.
- No `TODO`, `TBD`, or “similar to previous task” placeholders remain.

### 3. Type consistency

- New ORM model name is consistently `MemoryGraphEpisode`.
- New repository name is consistently `MemoryGraphEpisodeRepository`.
- Versioning method names are consistently `get_next_version`, `replace_latest_version`, and `get_latest_episode_uuid_set`.
- Retrieval helper names are consistently `_extract_episode_uuid`, `_filter_latest_edges`, and `_get_db_session`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-05-graphiti-latest-episode-versioning-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**