# Graphiti Knowledge Graph Integration Design

**Date:** 2026-03-29  
**Status:** Approved  
**Project:** Personal Knowledge Base

## Overview

This design integrates Graphiti temporal knowledge graph capabilities into the personal knowledge base backend. Users can manually or batch-add memories to a Neo4j-backed knowledge graph using an asynchronous queue pattern with status tracking.

## Goals

1. Remove all mock data from the knowledge graph service
2. Integrate Graphiti SDK for real knowledge graph persistence
3. Implement async queue-based ingestion (single and batch)
4. Track ingestion status per memory (not_added, pending, added, failed)
5. Deploy Neo4j via Docker Compose for local development

## Non-Goals

- Automatic ingestion on memory creation (manual trigger only for MVP)
- Advanced retry mechanisms (simple re-click to retry)
- Knowledge graph querying/search (future work)
- Multi-worker distributed processing (single instance for MVP)

## Architecture

### High-Level Flow

```
Frontend → FastAPI Backend → asyncio.Queue → GraphitiIngestWorker → Graphiti SDK → Neo4j
                ↓
         PostgreSQL (status tracking)
```

**Process:**
1. User clicks "Add to Knowledge Graph" (single or batch)
2. Backend validates → updates status to `pending` → enqueues task → returns 202 Accepted
3. Background worker consumes queue → calls `Graphiti.add_episode()`
4. On success: updates status to `added` + stores `episode_uuid`
5. On failure: updates status to `failed` + records error message

### Technology Stack

- **Queue:** Python `asyncio.Queue` (in-memory, single instance)
- **Graph Database:** Neo4j 5.26.0 (Docker)
- **Graph Library:** graphiti-core 0.28.2
- **LLM/Embedder:** OpenAI (required by Graphiti)

## Data Model Changes

### Memory Table Schema Updates

Add four new fields to the `memories` table:

```python
graph_status: Mapped[str] = mapped_column(
    String(16), 
    nullable=False, 
    server_default='not_added'
)  # Values: 'not_added' | 'pending' | 'added' | 'failed'

graph_episode_uuid: Mapped[str | None] = mapped_column(
    String(36), 
    nullable=True
)  # Graphiti episode UUID (returned after successful ingestion)

graph_error: Mapped[str | None] = mapped_column(
    Text, 
    nullable=True
)  # Error message if ingestion fails

graph_added_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), 
    nullable=True
)  # Timestamp when successfully added to graph
```

**Migration:** Create Alembic migration to add these columns with appropriate defaults.

## API Design

### New Endpoints

#### 1. Add Single Memory to Graph

```
POST /api/memories/{memory_id}/add-to-graph
```

**Response:** 202 Accepted
```json
{
    "message": "Memory queued for knowledge graph ingestion",
    "memory_id": "uuid",
    "graph_status": "pending"
}
```

**Validation:**
- Memory must exist
- Cannot queue if already `pending`
- Cannot queue if already `added` (must be idempotent for retries on `failed`)

#### 2. Batch Add Memories to Graph

```
POST /api/memories/batch-add-to-graph
```

**Request Body:**
```json
{
    "memory_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response:** 202 Accepted
```json
{
    "message": "3 memories queued for knowledge graph ingestion",
    "queued_count": 3,
    "memory_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Behavior:**
- Validates all memory IDs exist
- Skips memories already `pending` or `added`
- Returns count of successfully queued memories

#### 3. Get Graph Status (Optional)

```
GET /api/memories/{memory_id}/graph-status
```

**Response:** 200 OK
```json
{
    "memory_id": "uuid",
    "graph_status": "added",
    "graph_episode_uuid": "episode-uuid",
    "graph_added_at": "2026-03-29T10:00:00Z",
    "graph_error": null
}
```

### Modified Endpoints

**GET /api/memories** and **GET /api/memories/{id}**

Update `MemoryRead` schema to include new fields:

```python
class MemoryRead(BaseModel):
    id: str
    title: str
    title_status: Literal['pending', 'ready', 'failed']
    content: str
    group_id: str
    created_at: datetime | None
    updated_at: datetime | None
    # New fields
    graph_status: str
    graph_episode_uuid: str | None
    graph_added_at: datetime | None
```

## Component Design

### 1. GraphitiClient (SDK Wrapper)

**File:** `app/services/graphiti_client.py`

**Responsibilities:**
- Initialize Graphiti SDK with Neo4j connection
- Wrap `add_episode()` method with memory-specific parameters
- Handle connection lifecycle

**Key Methods:**
```python
class GraphitiClient:
    def __init__(self):
        # Initialize Graphiti with Neo4j credentials from settings
        
    async def add_memory_episode(
        self,
        memory_id: str,
        title: str,
        content: str,
        group_id: str,
        created_at: datetime,
    ) -> str:
        # Call graphiti.add_episode()
        # Return episode.uuid
        
    async def close(self):
        # Close Graphiti connection
```

**Configuration:**
- Uses `settings.NEO4J_URI`, `settings.NEO4J_USER`, `settings.NEO4J_PASSWORD`
- Uses `settings.OPENAI_API_KEY` (required by Graphiti for LLM/embeddings)

### 2. GraphitiIngestWorker (Async Queue Consumer)

**File:** `app/workers/graphiti_ingest_worker.py`

**Responsibilities:**
- Maintain `asyncio.Queue` for memory IDs
- Consume queue in background loop
- Call GraphitiClient for each memory
- Update database status (success/failure)

**Key Methods:**
```python
class GraphitiIngestWorker:
    def __init__(self):
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.graphiti_client = GraphitiClient()
        self.repository = MemoryRepository()
        self.running = False
    
    async def start(self):
        # Start background loop consuming queue
        
    async def stop(self):
        # Stop loop and close Graphiti client
        
    async def enqueue(self, memory_id: str):
        # Add memory ID to queue
        
    async def _process_memory(self, memory_id: str):
        # 1. Fetch memory from DB
        # 2. Call graphiti_client.add_memory_episode()
        # 3. On success: update graph_status='added', graph_episode_uuid, graph_added_at
        # 4. On failure: update graph_status='failed', graph_error
```

**Error Handling:**
- Catch all exceptions during processing
- Log errors with memory ID
- Update `graph_error` field with exception message
- Continue processing next item in queue

### 3. MemoryService Extensions

**File:** `app/services/memory_service.py`

**New Methods:**
```python
async def add_to_graph(
    self, 
    db: Session, 
    memory_id: str, 
    worker: GraphitiIngestWorker
) -> MemoryRead:
    # 1. Validate memory exists
    # 2. Check graph_status (reject if pending/added)
    # 3. Update graph_status to 'pending'
    # 4. Commit to DB
    # 5. Enqueue to worker
    # 6. Return updated memory

async def batch_add_to_graph(
    self,
    db: Session,
    memory_ids: list[str],
    worker: GraphitiIngestWorker
) -> dict:
    # 1. Validate all memories exist
    # 2. Filter out already pending/added
    # 3. Update all to 'pending' in single transaction
    # 4. Enqueue all to worker
    # 5. Return summary (queued_count, memory_ids)
```

### 4. Router Extensions

**File:** `app/routers/memories.py`

**New Endpoints:**
```python
@router.post("/{memory_id}/add-to-graph", status_code=202)
async def add_memory_to_graph(
    memory_id: str,
    db: Session = Depends(get_db),
    worker: GraphitiIngestWorker = Depends(get_worker)
):
    # Call service.add_to_graph()
    # Return 202 with status

@router.post("/batch-add-to-graph", status_code=202)
async def batch_add_to_graph(
    payload: BatchAddToGraphRequest,
    db: Session = Depends(get_db),
    worker: GraphitiIngestWorker = Depends(get_worker)
):
    # Call service.batch_add_to_graph()
    # Return 202 with summary
```

**Dependency Injection:**
- Add `get_worker()` dependency to access singleton worker instance
- Worker instance stored in `app.state.graphiti_worker`

### 5. Application Lifecycle

**File:** `app/main.py`

**Startup:**
```python
@app.on_event("startup")
async def startup_event():
    # 1. Create GraphitiIngestWorker instance
    # 2. Store in app.state.graphiti_worker
    # 3. Start worker background task
    # 4. Log startup message
```

**Shutdown:**
```python
@app.on_event("shutdown")
async def shutdown_event():
    # 1. Stop worker (graceful shutdown)
    # 2. Wait for queue to drain (with timeout)
    # 3. Close Graphiti client
    # 4. Log shutdown message
```

## Configuration

### Environment Variables

**File:** `.env` (add new variables)

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# OpenAI Configuration (required by Graphiti)
OPENAI_API_KEY=sk-...
```

**File:** `app/core/config.py` (add new settings)

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # OpenAI (for Graphiti)
    OPENAI_API_KEY: str
```

### Dependencies

**File:** `requirements.txt` (add new dependencies)

```
graphiti-core==0.28.2
neo4j>=5.26.0
openai>=1.91.0
```

## Infrastructure

### Docker Compose

**File:** `docker-compose.yml` (add Neo4j service)

```yaml
version: '3.8'

services:
  postgres:
    # ... existing postgres service ...
  
  neo4j:
    image: neo4j:5.26.0
    container_name: pkb-neo4j
    ports:
      - "7474:7474"  # HTTP (Neo4j Browser)
      - "7687:7687"  # Bolt protocol
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_PLUGINS: '["apoc"]'  # Optional: APOC procedures
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    restart: unless-stopped

volumes:
  postgres_data:
  neo4j_data:
  neo4j_logs:
```

**Usage:**
```bash
# Start all services
docker-compose up -d

# Access Neo4j Browser
open http://localhost:7474

# Stop services
docker-compose down
```

## Mock Data Cleanup

### Tasks

1. **Delete KnowledgeGraphService mock implementation**
   - File: `app/services/knowledge_graph_service.py`
   - Remove `ask()` method mock return
   - Replace with real Graphiti search implementation (future work) or remove entirely

2. **Clean database test data**
   - Check `memories` table for any hardcoded test records
   - Remove or mark as deletable

3. **Remove hardcoded examples**
   - Search codebase for any mock memory data
   - Remove from seed scripts or fixtures

## Error Handling

### Worker Error Scenarios

| Scenario | Handling |
|----------|----------|
| Memory not found | Log warning, skip processing |
| Graphiti connection failure | Update status to `failed`, record error |
| OpenAI API error | Update status to `failed`, record error |
| Neo4j unavailable | Update status to `failed`, record error |
| Unexpected exception | Update status to `failed`, record full traceback |

### User-Facing Errors

| Endpoint | Error | Status Code | Message |
|----------|-------|-------------|---------|
| POST /add-to-graph | Memory not found | 404 | "Memory not found" |
| POST /add-to-graph | Already pending | 400 | "Memory is already queued" |
| POST /add-to-graph | Already added | 400 | "Memory already in graph" |
| POST /batch-add-to-graph | Invalid memory IDs | 400 | "Invalid memory IDs: [...]" |

### Retry Strategy

- **User-initiated retry:** User can click "Add to Graph" again on failed memories
- **No automatic retry:** Keep MVP simple, avoid retry complexity
- **Future enhancement:** Add exponential backoff retry in worker

## Testing Strategy

### Unit Tests

1. **GraphitiClient**
   - Mock Graphiti SDK
   - Test `add_memory_episode()` success/failure
   - Test connection lifecycle

2. **GraphitiIngestWorker**
   - Mock queue and database
   - Test `_process_memory()` success/failure paths
   - Test status updates

3. **MemoryService**
   - Test `add_to_graph()` validation logic
   - Test `batch_add_to_graph()` filtering

### Integration Tests

1. **End-to-end flow**
   - Start worker
   - POST to `/add-to-graph`
   - Verify status transitions (not_added → pending → added)
   - Verify episode_uuid stored

2. **Batch processing**
   - POST batch request
   - Verify all memories processed
   - Verify correct status for each

3. **Error scenarios**
   - Simulate Neo4j down
   - Verify failed status recorded
   - Verify error message stored

**Test Requirements:**
- Use `@pytest.mark.integration` for tests requiring Neo4j
- Use Docker Compose test file for CI
- Mock OpenAI API calls to avoid costs

## Deployment Checklist

### Local Development

- [ ] Add Neo4j to docker-compose.yml
- [ ] Update .env.example with new variables
- [ ] Run `docker-compose up -d`
- [ ] Install new Python dependencies
- [ ] Run database migration
- [ ] Start FastAPI server
- [ ] Verify Neo4j Browser accessible at http://localhost:7474

### Production Considerations (Future)

- Replace asyncio.Queue with Redis/Celery for persistence
- Add monitoring for queue depth
- Add alerting for failed ingestions
- Consider rate limiting for OpenAI API
- Add Graphiti index building on startup
- Implement connection pooling for Neo4j

## Future Enhancements

1. **Knowledge Graph Querying**
   - Implement search endpoint using Graphiti search API
   - Replace mock `KnowledgeGraphService.ask()` with real queries

2. **Automatic Ingestion**
   - Option to auto-add memories on creation
   - Configurable per user or group

3. **Batch Operations**
   - Bulk delete from graph
   - Bulk re-index

4. **Advanced Features**
   - Community detection
   - Entity relationship visualization
   - Temporal queries

## Success Criteria

- [ ] All mock data removed from codebase
- [ ] Memories can be added to graph (single and batch)
- [ ] Status tracking works correctly (pending → added/failed)
- [ ] Neo4j runs via Docker Compose
- [ ] Worker starts/stops gracefully with app lifecycle
- [ ] Failed ingestions show error messages
- [ ] Users can retry failed ingestions
- [ ] Integration tests pass with real Neo4j

## References

- [Graphiti Documentation](https://help.getzep.com/graphiti/graphiti/overview)
- [Graphiti GitHub](https://github.com/getzep/graphiti)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
