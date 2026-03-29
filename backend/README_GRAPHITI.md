# Graphiti Knowledge Graph Integration

## Overview

This backend integrates [Graphiti](https://github.com/getzep/graphiti), a temporal knowledge graph library, to enable semantic memory storage and retrieval. Memories created through the API can be ingested into a Neo4j-backed knowledge graph, allowing for rich relationship extraction and contextual querying.

### Key Features

- Asynchronous memory ingestion into knowledge graph
- Status tracking throughout the ingestion lifecycle
- Batch processing support for multiple memories
- Group-based memory partitioning
- Temporal episode tracking with Graphiti

### Architecture

```
┌─────────────┐
│   FastAPI   │
│   Routes    │
└──────┬──────┘
       │
       ├─────────────────┐
       │                 │
┌──────▼──────┐   ┌─────▼──────────┐
│   Memory    │   │   Graphiti     │
│   Service   │   │ Ingest Worker  │
└──────┬──────┘   └─────┬──────────┘
       │                 │
┌──────▼──────┐   ┌─────▼──────────┐
│  SQLite DB  │   │ Graphiti Client│
│  (Memories) │   └─────┬──────────┘
└─────────────┘         │
                  ┌─────▼──────────┐
                  │   Neo4j Graph  │
                  │   Database     │
                  └────────────────┘
```

**Flow:**
1. User creates a memory via POST `/api/memories`
2. Memory stored in SQLite with `graph_status='not_added'`
3. User triggers ingestion via POST `/api/memories/{id}/add-to-graph`
4. Status updates to `pending`, memory ID queued to background worker
5. Worker processes queue, calls Graphiti SDK to create episode
6. Status updates to `added` with episode UUID, or `failed` with error

## Setup Instructions

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- OpenAI API key (required by Graphiti for embeddings)

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Database
DATABASE_URL=sqlite:///./app.db

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password

# OpenAI (required by Graphiti)
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 3. Start Neo4j

From the project root:

```bash
cd ..
docker-compose up -d neo4j
```

Verify Neo4j is running:

```bash
docker-compose ps
```

You should see:
```
NAME        IMAGE           STATUS
pkb-neo4j   neo4j:5.26.0    Up
```

Access Neo4j Browser at http://localhost:7474 (credentials: neo4j/password)

### 4. Run Database Migrations

```bash
cd backend
alembic upgrade head
```

### 5. Start the Backend Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at http://localhost:8000

## API Usage Examples

### Create a Memory

```bash
curl -X POST http://localhost:8000/api/memories \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Best Practices",
    "content": "Always use type hints and follow PEP 8 style guide",
    "group_id": "programming-tips"
  }'
```

Response:
```json
{
  "id": "abc123...",
  "title": "Python Best Practices",
  "content": "Always use type hints and follow PEP 8 style guide",
  "group_id": "programming-tips",
  "graph_status": "not_added",
  "graph_episode_uuid": null,
  "created_at": "2024-03-29T10:00:00Z"
}
```

### Add Memory to Knowledge Graph

```bash
curl -X POST http://localhost:8000/api/memories/abc123.../add-to-graph
```

Response:
```json
{
  "message": "Memory queued for knowledge graph ingestion",
  "memory_id": "abc123...",
  "graph_status": "pending"
}
```

### Check Graph Ingestion Status

```bash
curl http://localhost:8000/api/memories/abc123.../graph-status
```

Response:
```json
{
  "memory_id": "abc123...",
  "graph_status": "added",
  "graph_episode_uuid": "def456...",
  "graph_added_at": "2024-03-29T10:00:05Z",
  "graph_error": null
}
```

### Batch Add Multiple Memories

```bash
curl -X POST http://localhost:8000/api/memories/batch-add-to-graph \
  -H "Content-Type: application/json" \
  -d '{
    "memory_ids": ["abc123...", "xyz789..."]
  }'
```

Response:
```json
{
  "message": "2 memories queued for knowledge graph ingestion",
  "queued_count": 2,
  "memory_ids": ["abc123...", "xyz789..."]
}
```

### List Memories

```bash
# All memories
curl http://localhost:8000/api/memories

# Filter by group
curl http://localhost:8000/api/memories?group_id=programming-tips

# Search by keyword
curl http://localhost:8000/api/memories?keyword=python
```

## Graph Status Values

| Status | Description |
|--------|-------------|
| `not_added` | Memory created but not yet queued for graph ingestion |
| `pending` | Memory queued for ingestion, waiting for worker processing |
| `added` | Successfully ingested into knowledge graph |
| `failed` | Ingestion failed (check `graph_error` field for details) |

## Troubleshooting

### Neo4j Connection Issues

**Problem:** `Failed to connect to Neo4j`

**Solutions:**
1. Verify Neo4j is running: `docker-compose ps`
2. Check Neo4j logs: `docker-compose logs neo4j`
3. Verify credentials in `.env` match docker-compose.yml
4. Test connection: `docker exec -it pkb-neo4j cypher-shell -u neo4j -p password`

### OpenAI API Errors

**Problem:** `OpenAI API key not configured` or `Invalid API key`

**Solutions:**
1. Verify `OPENAI_API_KEY` is set in `.env`
2. Check API key is valid at https://platform.openai.com/api-keys
3. Ensure you have sufficient credits/quota

### Memory Stuck in Pending Status

**Problem:** Memory remains in `pending` status indefinitely

**Solutions:**
1. Check backend logs for worker errors
2. Verify Neo4j is accessible from the backend
3. Check `graph_error` field: `GET /api/memories/{id}/graph-status`
4. Restart the backend server to restart the worker

### Worker Not Processing Queue

**Problem:** Memories queued but never processed

**Solutions:**
1. Ensure backend server is running (worker starts with server)
2. Check logs for worker initialization: "GraphitiIngestWorker started"
3. Verify no exceptions in worker loop
4. Check Neo4j and OpenAI connectivity

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Integration Tests Only

```bash
pytest tests/integration/ -v -m integration
```

### Run Specific Test

```bash
pytest tests/integration/test_graphiti_integration.py::test_end_to_end_graph_ingestion -v
```

## Development Notes

### Key Components

- **GraphitiClient** (`app/services/graphiti_client.py`): Wrapper for Graphiti SDK
- **GraphitiIngestWorker** (`app/workers/graphiti_ingest_worker.py`): Background queue processor
- **MemoryService** (`app/services/memory_service.py`): Business logic for memory operations
- **Memory Model** (`app/models/memory.py`): SQLAlchemy model with graph status tracking

### Adding New Features

When extending the integration:

1. Update the Memory model if new fields are needed
2. Create Alembic migration: `alembic revision --autogenerate -m "description"`
3. Update schemas in `app/schemas/memory.py`
4. Add service methods in `MemoryService`
5. Add routes in `app/routers/memories.py`
6. Write tests in `tests/integration/`

### Monitoring

Check worker activity in logs:

```bash
# Look for these log messages
GraphitiIngestWorker started
Enqueued memory {id}
Processing memory {id}
Memory {id} successfully added to graph
```

## Additional Resources

- [Graphiti Documentation](https://github.com/getzep/graphiti)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
