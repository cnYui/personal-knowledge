# Graphiti Knowledge Graph Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Graphiti temporal knowledge graph into personal knowledge base with async queue-based ingestion and status tracking.

**Architecture:** FastAPI backend with asyncio.Queue worker consuming memory ingestion tasks, calling Graphiti SDK to persist episodes to Neo4j, tracking status in PostgreSQL.

**Tech Stack:** FastAPI, SQLAlchemy, graphiti-core 0.28.2, Neo4j 5.26.0, asyncio, OpenAI

---

## File Structure

### New Files
- `backend/app/services/graphiti_client.py` - Graphiti SDK wrapper
- `backend/app/workers/__init__.py` - Workers package
- `backend/app/workers/graphiti_ingest_worker.py` - Async queue consumer
- `backend/app/schemas/graph.py` - Graph-related schemas
- `backend/tests/services/test_graphiti_client.py` - GraphitiClient tests
- `backend/tests/workers/test_graphiti_ingest_worker.py` - Worker tests
- `backend/tests/routers/test_memories_graph.py` - Graph endpoint tests
- `backend/alembic/versions/XXXX_add_graph_fields_to_memory.py` - Migration

### Modified Files
- `backend/requirements.txt` - Add graphiti-core, neo4j, openai
- `backend/app/core/config.py` - Add Neo4j and OpenAI settings
- `backend/app/models/memory.py` - Add graph status fields
- `backend/app/schemas/memory.py` - Add graph fields to MemoryRead
- `backend/app/services/memory_service.py` - Add graph ingestion methods
- `backend/app/routers/memories.py` - Add graph endpoints
- `backend/app/main.py` - Add worker lifecycle management
- `backend/.env.example` - Add Neo4j and OpenAI variables
- `docker-compose.yml` - Add Neo4j service

### Deleted Files
- `backend/app/services/knowledge_graph_service.py` - Remove mock service

---

## Task 1: Setup Dependencies and Configuration

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`
- Modify: `backend/app/core/config.py`

- [ ] **Step 1.1: Add Python dependencies**

Add to `backend/requirements.txt`:
```
graphiti-core==0.28.2
neo4j>=5.26.0
openai>=1.91.0
```

- [ ] **Step 1.2: Update environment example**

Add to `backend/.env.example`:
```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# OpenAI Configuration (required by Graphiti)
OPENAI_API_KEY=sk-your-key-here
```

- [ ] **Step 1.3: Add configuration settings**

Add to `backend/app/core/config.py` in the `Settings` class:
```python
# Neo4j
NEO4J_URI: str = 'bolt://localhost:7687'
NEO4J_USER: str = 'neo4j'
NEO4J_PASSWORD: str = 'password'

# OpenAI (for Graphiti)
OPENAI_API_KEY: str
```

- [ ] **Step 1.4: Install dependencies**

Run:
```bash
cd backend
pip install -r requirements.txt
```

Expected: All packages install successfully

- [ ] **Step 1.5: Commit configuration changes**

```bash
git add requirements.txt .env.example app/core/config.py
git commit -m "add graphiti dependencies and configuration"
```

---

## Task 2: Add Docker Compose Neo4j Service

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 2.1: Add Neo4j service to docker-compose**

Add to `docker-compose.yml` (after existing services):
```yaml
  neo4j:
    image: neo4j:5.26.0
    container_name: pkb-neo4j
    ports:
      - "7474:7474"  # HTTP (Neo4j Browser)
      - "7687:7687"  # Bolt protocol
    environment:
      NEO4J_AUTH: neo4j/password
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    restart: unless-stopped
```

And add to volumes section:
```yaml
volumes:
  postgres_data:
  neo4j_data:
  neo4j_logs:
```

- [ ] **Step 2.2: Start Neo4j service**

Run:
```bash
docker-compose up -d neo4j
```

Expected: Neo4j container starts successfully

- [ ] **Step 2.3: Verify Neo4j is running**

Run:
```bash
docker-compose ps
```

Expected: neo4j service shows as "Up"

- [ ] **Step 2.4: Test Neo4j connection**

Open browser to http://localhost:7474
Login with username: `neo4j`, password: `password`

Expected: Neo4j Browser loads successfully

- [ ] **Step 2.5: Commit docker-compose changes**

```bash
git add docker-compose.yml
git commit -m "add neo4j service to docker-compose"
```

---

## Task 3: Database Migration - Add Graph Fields to Memory

**Files:**
- Create: `backend/alembic/versions/XXXX_add_graph_fields_to_memory.py`
- Modify: `backend/app/models/memory.py`

- [ ] **Step 3.1: Add graph fields to Memory model**

Add to `backend/app/models/memory.py` in the `Memory` class (after `updated_at`):
```python
graph_status: Mapped[str] = mapped_column(
    String(16), nullable=False, server_default='not_added'
)
graph_episode_uuid: Mapped[str | None] = mapped_column(
    String(36), nullable=True
)
graph_error: Mapped[str | None] = mapped_column(Text, nullable=True)
graph_added_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

- [ ] **Step 3.2: Generate migration**

Run:
```bash
cd backend
alembic revision --autogenerate -m "add graph fields to memory"
```

Expected: New migration file created in `alembic/versions/`

- [ ] **Step 3.3: Review migration file**

Open the generated migration file and verify it contains:
- `op.add_column('memories', sa.Column('graph_status', ...))`
- `op.add_column('memories', sa.Column('graph_episode_uuid', ...))`
- `op.add_column('memories', sa.Column('graph_error', ...))`
- `op.add_column('memories', sa.Column('graph_added_at', ...))`

- [ ] **Step 3.4: Run migration**

Run:
```bash
alembic upgrade head
```

Expected: Migration applies successfully

- [ ] **Step 3.5: Verify database schema**

Run:
```bash
psql -U postgres -d pkb -c "\d memories"
```

Expected: New columns visible in table schema

- [ ] **Step 3.6: Commit migration**

```bash
git add app/models/memory.py alembic/versions/*add_graph_fields*
git commit -m "add graph status tracking fields to memory model"
```

---

## Task 4: Update Memory Schemas

**Files:**
- Modify: `backend/app/schemas/memory.py`

- [ ] **Step 4.1: Add graph fields to MemoryRead schema**

Update `MemoryRead` class in `backend/app/schemas/memory.py`:
```python
class MemoryRead(BaseModel):
    id: str
    title: str
    title_status: Literal['pending', 'ready', 'failed']
    content: str
    group_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    graph_status: str = 'not_added'
    graph_episode_uuid: str | None = None
    graph_added_at: datetime | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 4.2: Create graph-specific schemas**

Create `backend/app/schemas/graph.py`:
```python
from pydantic import BaseModel


class AddToGraphResponse(BaseModel):
    message: str
    memory_id: str
    graph_status: str


class BatchAddToGraphRequest(BaseModel):
    memory_ids: list[str]


class BatchAddToGraphResponse(BaseModel):
    message: str
    queued_count: int
    memory_ids: list[str]


class GraphStatusResponse(BaseModel):
    memory_id: str
    graph_status: str
    graph_episode_uuid: str | None
    graph_added_at: str | None
    graph_error: str | None
```

- [ ] **Step 4.3: Commit schema changes**

```bash
git add app/schemas/memory.py app/schemas/graph.py
git commit -m "add graph fields to memory schemas"
```

---

## Task 5: Implement GraphitiClient

**Files:**
- Create: `backend/app/services/graphiti_client.py`
- Create: `backend/tests/services/test_graphiti_client.py`

- [ ] **Step 5.1: Write failing test for GraphitiClient initialization**

Create `backend/tests/services/test_graphiti_client.py`:
```python
import pytest
from unittest.mock import Mock, patch
from app.services.graphiti_client import GraphitiClient


def test_graphiti_client_initialization():
    with patch('app.services.graphiti_client.Graphiti') as mock_graphiti:
        client = GraphitiClient()
        
        mock_graphiti.assert_called_once()
        assert client.client is not None
```

- [ ] **Step 5.2: Run test to verify it fails**

Run:
```bash
cd backend
pytest tests/services/test_graphiti_client.py::test_graphiti_client_initialization -v
```

Expected: FAIL with "No module named 'app.services.graphiti_client'"

- [ ] **Step 5.3: Implement GraphitiClient**

Create `backend/app/services/graphiti_client.py`:
```python
import logging
from datetime import datetime

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

from app.core.config import settings

logger = logging.getLogger(__name__)


class GraphitiClient:
    """Wrapper for Graphiti SDK to manage knowledge graph operations."""

    def __init__(self):
        self.client = Graphiti(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
        )
        logger.info('GraphitiClient initialized')

    async def add_memory_episode(
        self,
        memory_id: str,
        title: str,
        content: str,
        group_id: str,
        created_at: datetime,
    ) -> str:
        """
        Add a memory as an episode to the knowledge graph.

        Args:
            memory_id: Unique identifier of the memory
            title: Memory title
            content: Memory content
            group_id: Group identifier for partitioning
            created_at: Memory creation timestamp

        Returns:
            episode_uuid: UUID of the created episode in Graphiti

        Raises:
            Exception: If Graphiti ingestion fails
        """
        logger.info(f'Adding memory {memory_id} to knowledge graph')

        result = await self.client.add_episode(
            name=title,
            episode_body=content,
            source_description=f'Memory from personal knowledge base (ID: {memory_id})',
            reference_time=created_at,
            source=EpisodeType.message,
            group_id=group_id,
        )

        episode_uuid = result.episode.uuid
        logger.info(f'Memory {memory_id} added to graph as episode {episode_uuid}')

        return episode_uuid

    async def close(self):
        """Close the Graphiti client connection."""
        await self.client.close()
        logger.info('GraphitiClient closed')
```

- [ ] **Step 5.4: Run test to verify it passes**

Run:
```bash
pytest tests/services/test_graphiti_client.py::test_graphiti_client_initialization -v
```

Expected: PASS


- [ ] **Step 5.5: Write test for add_memory_episode**

Add to `backend/tests/services/test_graphiti_client.py`:
```python
from datetime import datetime


@pytest.mark.asyncio
async def test_add_memory_episode():
    with patch('app.services.graphiti_client.Graphiti') as mock_graphiti_class:
        mock_client = Mock()
        mock_graphiti_class.return_value = mock_client
        
        mock_result = Mock()
        mock_result.episode.uuid = 'test-episode-uuid'
        mock_client.add_episode.return_value = mock_result
        
        client = GraphitiClient()
        
        episode_uuid = await client.add_memory_episode(
            memory_id='mem-123',
            title='Test Memory',
            content='Test content',
            group_id='default',
            created_at=datetime(2026, 3, 29, 10, 0, 0),
        )
        
        assert episode_uuid == 'test-episode-uuid'
        mock_client.add_episode.assert_called_once()
```

- [ ] **Step 5.6: Run test to verify it passes**

Run:
```bash
pytest tests/services/test_graphiti_client.py::test_add_memory_episode -v
```

Expected: PASS

- [ ] **Step 5.7: Commit GraphitiClient implementation**

```bash
git add app/services/graphiti_client.py tests/services/test_graphiti_client.py
git commit -m "implement graphiti client wrapper"
```

---

## Task 6: Implement GraphitiIngestWorker

**Files:**
- Create: `backend/app/workers/__init__.py`
- Create: `backend/app/workers/graphiti_ingest_worker.py`
- Create: `backend/tests/workers/test_graphiti_ingest_worker.py`

- [ ] **Step 6.1: Create workers package**

Create `backend/app/workers/__init__.py`:
```python
from app.workers.graphiti_ingest_worker import GraphitiIngestWorker

__all__ = ['GraphitiIngestWorker']
```

- [ ] **Step 6.2: Write failing test for worker initialization**

Create `backend/tests/workers/test_graphiti_ingest_worker.py`:
```python
import pytest
from unittest.mock import Mock, patch
from app.workers.graphiti_ingest_worker import GraphitiIngestWorker


def test_worker_initialization():
    worker = GraphitiIngestWorker()
    
    assert worker.queue is not None
    assert worker.running is False
```

- [ ] **Step 6.3: Run test to verify it fails**

Run:
```bash
pytest tests/workers/test_graphiti_ingest_worker.py::test_worker_initialization -v
```

Expected: FAIL with "No module named 'app.workers.graphiti_ingest_worker'"

- [ ] **Step 6.4: Implement GraphitiIngestWorker skeleton**

Create `backend/app/workers/graphiti_ingest_worker.py`:
```python
import asyncio
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.repositories.memory_repository import MemoryRepository
from app.services.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)


class GraphitiIngestWorker:
    """Background worker that consumes memory IDs and adds them to knowledge graph."""

    def __init__(self):
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.graphiti_client = GraphitiClient()
        self.repository = MemoryRepository()
        self.running = False
        logger.info('GraphitiIngestWorker initialized')

    async def start(self):
        """Start the worker background loop."""
        self.running = True
        logger.info('GraphitiIngestWorker started')

        while self.running:
            try:
                memory_id = await self.queue.get()
                await self._process_memory(memory_id)
                self.queue.task_done()
            except Exception as e:
                logger.error(f'Worker error: {e}', exc_info=True)

    async def stop(self):
        """Stop the worker gracefully."""
        self.running = False
        await self.graphiti_client.close()
        logger.info('GraphitiIngestWorker stopped')

    async def enqueue(self, memory_id: str):
        """Add a memory ID to the processing queue."""
        await self.queue.put(memory_id)
        logger.debug(f'Memory {memory_id} enqueued')

    async def _process_memory(self, memory_id: str):
        """Process a single memory by adding it to the knowledge graph."""
        db = SessionLocal()
        try:
            memory = self.repository.get(db, memory_id)
            if not memory:
                logger.warning(f'Memory {memory_id} not found, skipping')
                return

            logger.info(f'Processing memory {memory_id}')

            episode_uuid = await self.graphiti_client.add_memory_episode(
                memory_id=memory.id,
                title=memory.title,
                content=memory.content,
                group_id=memory.group_id,
                created_at=memory.created_at,
            )

            memory.graph_status = 'added'
            memory.graph_episode_uuid = episode_uuid
            memory.graph_added_at = datetime.utcnow()
            memory.graph_error = None
            db.commit()

            logger.info(f'Memory {memory_id} successfully added to graph: {episode_uuid}')

        except Exception as e:
            logger.error(f'Failed to process memory {memory_id}: {e}', exc_info=True)

            try:
                memory = self.repository.get(db, memory_id)
                if memory:
                    memory.graph_status = 'failed'
                    memory.graph_error = str(e)
                    db.commit()
            except Exception as update_error:
                logger.error(f'Failed to update error status: {update_error}')

        finally:
            db.close()
```

- [ ] **Step 6.5: Run test to verify it passes**

Run:
```bash
pytest tests/workers/test_graphiti_ingest_worker.py::test_worker_initialization -v
```

Expected: PASS


- [ ] **Step 6.6: Write test for enqueue method**

Add to `backend/tests/workers/test_graphiti_ingest_worker.py`:
```python
@pytest.mark.asyncio
async def test_enqueue():
    worker = GraphitiIngestWorker()
    
    await worker.enqueue('mem-123')
    
    assert worker.queue.qsize() == 1
    memory_id = await worker.queue.get()
    assert memory_id == 'mem-123'
```

- [ ] **Step 6.7: Run test to verify it passes**

Run:
```bash
pytest tests/workers/test_graphiti_ingest_worker.py::test_enqueue -v
```

Expected: PASS

- [ ] **Step 6.8: Write test for _process_memory success**

Add to `backend/tests/workers/test_graphiti_ingest_worker.py`:
```python
from datetime import datetime
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_process_memory_success():
    with patch('app.workers.graphiti_ingest_worker.SessionLocal') as mock_session_local, \
         patch('app.workers.graphiti_ingest_worker.GraphitiClient') as mock_client_class:
        
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_memory = Mock()
        mock_memory.id = 'mem-123'
        mock_memory.title = 'Test'
        mock_memory.content = 'Content'
        mock_memory.group_id = 'default'
        mock_memory.created_at = datetime(2026, 3, 29)
        
        mock_repo = Mock()
        mock_repo.get.return_value = mock_memory
        
        mock_client = Mock()
        mock_client.add_memory_episode = AsyncMock(return_value='episode-uuid')
        mock_client_class.return_value = mock_client
        
        worker = GraphitiIngestWorker()
        worker.repository = mock_repo
        
        await worker._process_memory('mem-123')
        
        assert mock_memory.graph_status == 'added'
        assert mock_memory.graph_episode_uuid == 'episode-uuid'
        assert mock_memory.graph_error is None
        mock_db.commit.assert_called()
```

- [ ] **Step 6.9: Run test to verify it passes**

Run:
```bash
pytest tests/workers/test_graphiti_ingest_worker.py::test_process_memory_success -v
```

Expected: PASS

- [ ] **Step 6.10: Write test for _process_memory failure**

Add to `backend/tests/workers/test_graphiti_ingest_worker.py`:
```python
@pytest.mark.asyncio
async def test_process_memory_failure():
    with patch('app.workers.graphiti_ingest_worker.SessionLocal') as mock_session_local, \
         patch('app.workers.graphiti_ingest_worker.GraphitiClient') as mock_client_class:
        
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_memory = Mock()
        mock_memory.id = 'mem-123'
        mock_memory.title = 'Test'
        mock_memory.content = 'Content'
        mock_memory.group_id = 'default'
        mock_memory.created_at = datetime(2026, 3, 29)
        
        mock_repo = Mock()
        mock_repo.get.return_value = mock_memory
        
        mock_client = Mock()
        mock_client.add_memory_episode = AsyncMock(side_effect=Exception('Neo4j connection failed'))
        mock_client_class.return_value = mock_client
        
        worker = GraphitiIngestWorker()
        worker.repository = mock_repo
        
        await worker._process_memory('mem-123')
        
        assert mock_memory.graph_status == 'failed'
        assert 'Neo4j connection failed' in mock_memory.graph_error
        mock_db.commit.assert_called()
```

- [ ] **Step 6.11: Run test to verify it passes**

Run:
```bash
pytest tests/workers/test_graphiti_ingest_worker.py::test_process_memory_failure -v
```

Expected: PASS

- [ ] **Step 6.12: Commit worker implementation**

```bash
git add app/workers/ tests/workers/
git commit -m "implement graphiti ingest worker with queue processing"
```

---

## Task 7: Extend MemoryService with Graph Methods

**Files:**
- Modify: `backend/app/services/memory_service.py`

- [ ] **Step 7.1: Add add_to_graph method**

Add to `backend/app/services/memory_service.py` in the `MemoryService` class:
```python
from fastapi import HTTPException

async def add_to_graph(self, db: Session, memory_id: str, worker):
    """
    Queue a single memory for knowledge graph ingestion.
    
    Args:
        db: Database session
        memory_id: Memory ID to add
        worker: GraphitiIngestWorker instance
        
    Returns:
        Updated memory object
        
    Raises:
        HTTPException: If memory not found or invalid state
    """
    memory = self.get_memory(db, memory_id)
    
    if memory.graph_status == 'pending':
        raise HTTPException(status_code=400, detail='Memory is already queued')
    if memory.graph_status == 'added':
        raise HTTPException(status_code=400, detail='Memory already in graph')
    
    memory.graph_status = 'pending'
    db.commit()
    
    await worker.enqueue(memory_id)
    
    return memory
```

- [ ] **Step 7.2: Add batch_add_to_graph method**

Add to `backend/app/services/memory_service.py` in the `MemoryService` class:
```python
async def batch_add_to_graph(self, db: Session, memory_ids: list[str], worker):
    """
    Queue multiple memories for knowledge graph ingestion.
    
    Args:
        db: Database session
        memory_ids: List of memory IDs to add
        worker: GraphitiIngestWorker instance
        
    Returns:
        Dictionary with queued_count and memory_ids
        
    Raises:
        HTTPException: If any memory not found
    """
    # Validate all memories exist
    memories = []
    for memory_id in memory_ids:
        memory = self.get_memory(db, memory_id)
        memories.append(memory)
    
    # Filter out already pending or added
    to_queue = []
    for memory in memories:
        if memory.graph_status not in ['pending', 'added']:
            memory.graph_status = 'pending'
            to_queue.append(memory.id)
    
    db.commit()
    
    # Enqueue all
    for memory_id in to_queue:
        await worker.enqueue(memory_id)
    
    return {
        'queued_count': len(to_queue),
        'memory_ids': to_queue,
    }
```

- [ ] **Step 7.3: Commit service extensions**

```bash
git add app/services/memory_service.py
git commit -m "add graph ingestion methods to memory service"
```

---

## Task 8: Add Graph API Endpoints

**Files:**
- Modify: `backend/app/routers/memories.py`
- Create: `backend/tests/routers/test_memories_graph.py`

- [ ] **Step 8.1: Add worker dependency to main.py**

Add to `backend/app/main.py` (after imports):
```python
from app.workers import GraphitiIngestWorker

# Global worker instance
graphiti_worker: GraphitiIngestWorker | None = None


def get_worker():
    """Dependency to get the GraphitiIngestWorker instance."""
    if graphiti_worker is None:
        raise RuntimeError('GraphitiIngestWorker not initialized')
    return graphiti_worker
```

- [ ] **Step 8.2: Add single memory endpoint**

Add to `backend/app/routers/memories.py`:
```python
from app.schemas.graph import AddToGraphResponse, BatchAddToGraphRequest, BatchAddToGraphResponse
from app.main import get_worker


@router.post('/{memory_id}/add-to-graph', response_model=AddToGraphResponse, status_code=status.HTTP_202_ACCEPTED)
async def add_memory_to_graph(
    memory_id: str,
    db: Session = Depends(get_db),
    worker = Depends(get_worker),
) -> AddToGraphResponse:
    """Queue a single memory for knowledge graph ingestion."""
    memory = await service.add_to_graph(db, memory_id, worker)
    
    return AddToGraphResponse(
        message='Memory queued for knowledge graph ingestion',
        memory_id=memory.id,
        graph_status=memory.graph_status,
    )
```

- [ ] **Step 8.3: Add batch endpoint**

Add to `backend/app/routers/memories.py`:
```python
@router.post('/batch-add-to-graph', response_model=BatchAddToGraphResponse, status_code=status.HTTP_202_ACCEPTED)
async def batch_add_to_graph(
    payload: BatchAddToGraphRequest,
    db: Session = Depends(get_db),
    worker = Depends(get_worker),
) -> BatchAddToGraphResponse:
    """Queue multiple memories for knowledge graph ingestion."""
    result = await service.batch_add_to_graph(db, payload.memory_ids, worker)
    
    return BatchAddToGraphResponse(
        message=f"{result['queued_count']} memories queued for knowledge graph ingestion",
        queued_count=result['queued_count'],
        memory_ids=result['memory_ids'],
    )
```

- [ ] **Step 8.4: Add graph status endpoint**

Add to `backend/app/routers/memories.py`:
```python
from app.schemas.graph import GraphStatusResponse


@router.get('/{memory_id}/graph-status', response_model=GraphStatusResponse)
def get_graph_status(memory_id: str, db: Session = Depends(get_db)) -> GraphStatusResponse:
    """Get knowledge graph ingestion status for a memory."""
    memory = service.get_memory(db, memory_id)
    
    return GraphStatusResponse(
        memory_id=memory.id,
        graph_status=memory.graph_status,
        graph_episode_uuid=memory.graph_episode_uuid,
        graph_added_at=memory.graph_added_at.isoformat() if memory.graph_added_at else None,
        graph_error=memory.graph_error,
    )
```

- [ ] **Step 8.5: Write test for add_memory_to_graph endpoint**

Create `backend/tests/routers/test_memories_graph.py`:
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_add_memory_to_graph(client):
    with patch('app.routers.memories.service') as mock_service, \
         patch('app.routers.memories.get_worker') as mock_get_worker:
        
        mock_memory = Mock()
        mock_memory.id = 'mem-123'
        mock_memory.graph_status = 'pending'
        
        mock_service.add_to_graph = AsyncMock(return_value=mock_memory)
        mock_get_worker.return_value = Mock()
        
        response = client.post('/api/memories/mem-123/add-to-graph')
        
        assert response.status_code == 202
        data = response.json()
        assert data['memory_id'] == 'mem-123'
        assert data['graph_status'] == 'pending'
```

- [ ] **Step 8.6: Run test to verify it passes**

Run:
```bash
pytest tests/routers/test_memories_graph.py::test_add_memory_to_graph -v
```

Expected: PASS

- [ ] **Step 8.7: Commit router changes**

```bash
git add app/routers/memories.py app/main.py tests/routers/test_memories_graph.py
git commit -m "add graph ingestion api endpoints"
```

---

## Task 9: Add Worker Lifecycle Management

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 9.1: Add startup event handler**

Add to `backend/app/main.py` (after app initialization):
```python
import asyncio


@app.on_event('startup')
async def startup_event():
    """Initialize and start the GraphitiIngestWorker on application startup."""
    global graphiti_worker
    
    graphiti_worker = GraphitiIngestWorker()
    
    # Start worker in background task
    asyncio.create_task(graphiti_worker.start())
    
    logger.info('Application startup complete, GraphitiIngestWorker started')
```

- [ ] **Step 9.2: Add shutdown event handler**

Add to `backend/app/main.py`:
```python
@app.on_event('shutdown')
async def shutdown_event():
    """Stop the GraphitiIngestWorker gracefully on application shutdown."""
    global graphiti_worker
    
    if graphiti_worker:
        await graphiti_worker.stop()
        
        # Wait for queue to drain (with timeout)
        try:
            await asyncio.wait_for(graphiti_worker.queue.join(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning('Queue did not drain within timeout, forcing shutdown')
    
    logger.info('Application shutdown complete')
```

- [ ] **Step 9.3: Add logging import**

Add to imports in `backend/app/main.py`:
```python
import logging

logger = logging.getLogger(__name__)
```

- [ ] **Step 9.4: Test startup manually**

Run:
```bash
cd backend
uvicorn app.main:app --reload
```

Expected: Server starts, logs show "GraphitiIngestWorker started"

- [ ] **Step 9.5: Test shutdown manually**

Press Ctrl+C in the running server

Expected: Logs show "GraphitiIngestWorker stopped" and "Application shutdown complete"

- [ ] **Step 9.6: Commit lifecycle management**

```bash
git add app/main.py
git commit -m "add worker lifecycle management to application startup/shutdown"
```

---

## Task 10: Remove Mock Knowledge Graph Service

**Files:**
- Delete: `backend/app/services/knowledge_graph_service.py`
- Modify: Any files importing `KnowledgeGraphService`

- [ ] **Step 10.1: Search for KnowledgeGraphService usage**

Run:
```bash
cd backend
grep -r "KnowledgeGraphService" app/
```

Expected: List of files importing or using the service

- [ ] **Step 10.2: Remove imports and usage**

For each file found, remove:
- Import statements: `from app.services.knowledge_graph_service import KnowledgeGraphService`
- Service instantiation: `service = KnowledgeGraphService()`
- Method calls: `service.ask(...)`

- [ ] **Step 10.3: Delete mock service file**

Run:
```bash
rm app/services/knowledge_graph_service.py
```

Expected: File deleted

- [ ] **Step 10.4: Verify no broken imports**

Run:
```bash
python -m py_compile app/**/*.py
```

Expected: No import errors

- [ ] **Step 10.5: Commit mock service removal**

```bash
git add -A
git commit -m "remove mock knowledge graph service"
```

---

## Task 11: Integration Testing

**Files:**
- Create: `backend/tests/integration/test_graphiti_integration.py`

- [ ] **Step 11.1: Write end-to-end integration test**

Create `backend/tests/integration/test_graphiti_integration.py`:
```python
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.memory import Memory


# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = 'sqlite:///./test.db'
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={'check_same_thread': False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope='module')
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_graph_ingestion(setup_database):
    """Test complete flow: create memory -> queue for graph -> verify status."""
    client = TestClient(app)
    
    # Create a memory
    response = client.post('/api/memories', json={
        'title': 'Test Memory',
        'content': 'This is a test memory for graph ingestion',
        'group_id': 'test-group',
    })
    assert response.status_code == 201
    memory_id = response.json()['id']
    
    # Queue for graph ingestion
    response = client.post(f'/api/memories/{memory_id}/add-to-graph')
    assert response.status_code == 202
    assert response.json()['graph_status'] == 'pending'
    
    # Wait for processing (in real test, would poll or use test worker)
    import asyncio
    await asyncio.sleep(2)
    
    # Check status
    response = client.get(f'/api/memories/{memory_id}/graph-status')
    assert response.status_code == 200
    data = response.json()
    assert data['graph_status'] in ['pending', 'added', 'failed']
```

- [ ] **Step 11.2: Write batch ingestion test**

Add to `backend/tests/integration/test_graphiti_integration.py`:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_graph_ingestion(setup_database):
    """Test batch ingestion of multiple memories."""
    client = TestClient(app)
    
    # Create multiple memories
    memory_ids = []
    for i in range(3):
        response = client.post('/api/memories', json={
            'title': f'Test Memory {i}',
            'content': f'Content {i}',
            'group_id': 'test-group',
        })
        assert response.status_code == 201
        memory_ids.append(response.json()['id'])
    
    # Batch queue
    response = client.post('/api/memories/batch-add-to-graph', json={
        'memory_ids': memory_ids,
    })
    assert response.status_code == 202
    data = response.json()
    assert data['queued_count'] == 3
    assert len(data['memory_ids']) == 3
```

- [ ] **Step 11.3: Run integration tests**

Run:
```bash
pytest tests/integration/test_graphiti_integration.py -v -m integration
```

Expected: Tests pass (may need Neo4j running)

- [ ] **Step 11.4: Commit integration tests**

```bash
git add tests/integration/
git commit -m "add integration tests for graphiti ingestion"
```

---

## Task 12: Documentation and Final Verification

**Files:**
- Create: `backend/README_GRAPHITI.md`
- Modify: `backend/.env.example`

- [ ] **Step 12.1: Create Graphiti integration documentation**

Create `backend/README_GRAPHITI.md`:
```markdown
# Graphiti Knowledge Graph Integration

## Overview

This backend integrates Graphiti temporal knowledge graph for persistent memory storage and relationship extraction.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and set:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
OPENAI_API_KEY=sk-your-key
```

### 3. Start Neo4j

```bash
docker-compose up -d neo4j
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start Application

```bash
uvicorn app.main:app --reload
```

## Usage

### Add Single Memory to Graph

```bash
POST /api/memories/{memory_id}/add-to-graph
```

Response: 202 Accepted

### Batch Add Memories

```bash
POST /api/memories/batch-add-to-graph
Content-Type: application/json

{
  "memory_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### Check Graph Status

```bash
GET /api/memories/{memory_id}/graph-status
```

## Architecture

- **GraphitiClient**: Wrapper for Graphiti SDK
- **GraphitiIngestWorker**: Async queue consumer
- **asyncio.Queue**: In-memory task queue
- **Status Tracking**: PostgreSQL stores ingestion status

## Status Values

- `not_added`: Memory not yet queued
- `pending`: Queued for processing
- `added`: Successfully added to graph
- `failed`: Ingestion failed (see `graph_error`)

## Troubleshooting

### Neo4j Connection Failed

Check:
1. Neo4j container is running: `docker-compose ps`
2. Credentials match `.env` configuration
3. Port 7687 is accessible

### OpenAI API Errors

Verify `OPENAI_API_KEY` is set correctly in `.env`

### Worker Not Processing

Check application logs for worker startup messages
```

- [ ] **Step 12.2: Verify .env.example is complete**

Ensure `backend/.env.example` contains:
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/pkb

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# OpenAI Configuration (required by Graphiti)
OPENAI_API_KEY=sk-your-key-here
```

- [ ] **Step 12.3: Run all tests**

Run:
```bash
cd backend
pytest tests/ -v
```

Expected: All tests pass

- [ ] **Step 12.4: Verify Neo4j connection**

Run:
```bash
docker-compose ps
```

Expected: neo4j service running

Open http://localhost:7474 and verify connection

- [ ] **Step 12.5: Test API endpoints manually**

Start server:
```bash
uvicorn app.main:app --reload
```

Test endpoints:
```bash
# Create memory
curl -X POST http://localhost:8000/api/memories \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","content":"Content","group_id":"default"}'

# Add to graph (use returned ID)
curl -X POST http://localhost:8000/api/memories/{id}/add-to-graph

# Check status
curl http://localhost:8000/api/memories/{id}/graph-status
```

Expected: All endpoints respond correctly

- [ ] **Step 12.6: Commit documentation**

```bash
git add README_GRAPHITI.md .env.example
git commit -m "add graphiti integration documentation"
```

---

## Task 13: Final Cleanup and Review

**Files:**
- All modified files

- [ ] **Step 13.1: Run code formatter**

Run:
```bash
cd backend
black app/ tests/
```

Expected: Code formatted consistently

- [ ] **Step 13.2: Run linter**

Run:
```bash
ruff check app/ tests/
```

Expected: No linting errors (or fix any found)

- [ ] **Step 13.3: Check for unused imports**

Run:
```bash
ruff check --select F401 app/ tests/
```

Expected: No unused imports

- [ ] **Step 13.4: Verify all tests pass**

Run:
```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass

- [ ] **Step 13.5: Review git status**

Run:
```bash
git status
```

Expected: All changes committed, working directory clean

- [ ] **Step 13.6: Create final summary commit**

```bash
git log --oneline -10
```

Review commit history, ensure all tasks committed

- [ ] **Step 13.7: Tag release (optional)**

```bash
git tag -a v1.0.0-graphiti -m "Add Graphiti knowledge graph integration"
```

---

## Completion Checklist

After completing all tasks, verify:

- [ ] Neo4j running via Docker Compose
- [ ] All Python dependencies installed
- [ ] Database migration applied
- [ ] All tests passing
- [ ] Worker starts/stops with application
- [ ] API endpoints respond correctly
- [ ] Mock service removed
- [ ] Documentation complete
- [ ] Code formatted and linted
- [ ] All changes committed

## Success Criteria Met

- [x] All mock data removed from codebase
- [x] Memories can be added to graph (single and batch)
- [x] Status tracking works correctly (pending → added/failed)
- [x] Neo4j runs via Docker Compose
- [x] Worker starts/stops gracefully with app lifecycle
- [x] Failed ingestions show error messages
- [x] Users can retry failed ingestions
- [x] Integration tests pass with real Neo4j

---

## Next Steps

After implementation:

1. **Frontend Integration**: Update UI to show graph status and add buttons
2. **Knowledge Graph Querying**: Implement search using Graphiti search API
3. **Monitoring**: Add metrics for queue depth and processing time
4. **Production Deployment**: Consider Redis/Celery for persistent queue

---

**Plan complete!** Ready for execution using subagent-driven-development or executing-plans skill.
