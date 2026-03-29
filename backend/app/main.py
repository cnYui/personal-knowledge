import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.database import Base, engine
from app.models import ChatMessage, Memory, MemoryImage
from app.routers.chat import router as chat_router
from app.routers.memories import router as memories_router
from app.routers.uploads import router as uploads_router
from app.workers import GraphitiIngestWorker
from app import dependencies

logger = logging.getLogger(__name__)


app = FastAPI(title="Personal Knowledge Base API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)
app.include_router(memories_router)
app.include_router(uploads_router)
Base.metadata.create_all(bind=engine)


@app.on_event('startup')
async def startup_event():
    """Initialize and start the GraphitiIngestWorker on application startup."""
    dependencies.graphiti_worker = GraphitiIngestWorker()
    
    # Start worker in background task
    asyncio.create_task(dependencies.graphiti_worker.start())
    
    logger.info('Application startup complete, GraphitiIngestWorker started')


@app.on_event('shutdown')
async def shutdown_event():
    """Stop the GraphitiIngestWorker gracefully on application shutdown."""
    if dependencies.graphiti_worker:
        await dependencies.graphiti_worker.stop()
        
        # Wait for queue to drain (with timeout)
        try:
            await asyncio.wait_for(dependencies.graphiti_worker.queue.join(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning('Queue did not drain within timeout, forcing shutdown')
    
    logger.info('Application shutdown complete')


def _migrate_sqlite_memories_table() -> None:
    if engine.dialect.name != 'sqlite':
        return

    with engine.begin() as connection:
        columns = [
            row[1]
            for row in connection.execute(text('PRAGMA table_info(memories)'))
        ]

        target_columns = {
            'id',
            'title',
            'title_status',
            'content',
            'group_id',
            'created_at',
            'updated_at',
        }

        if set(columns) == target_columns:
            return

        connection.execute(text('PRAGMA foreign_keys=OFF'))
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS memories_new (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '标题生成中',
                    title_status TEXT NOT NULL DEFAULT 'pending',
                    content TEXT NOT NULL,
                    group_id TEXT NOT NULL DEFAULT 'default',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

        connection.execute(
            text(
                """
                INSERT INTO memories_new (id, title, title_status, content, group_id, created_at, updated_at)
                SELECT
                    id,
                    COALESCE(NULLIF(TRIM(title), ''), '标题生成中') AS title,
                    CASE
                        WHEN title IS NULL OR TRIM(title) = '' OR title = '标题生成中' THEN 'pending'
                        ELSE 'ready'
                    END AS title_status,
                    content,
                    'default' AS group_id,
                    created_at,
                    updated_at
                FROM memories
                """
            )
        )

        connection.execute(text('DROP TABLE memories'))
        connection.execute(text('ALTER TABLE memories_new RENAME TO memories'))
        connection.execute(text('CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at DESC)'))
        connection.execute(
            text('CREATE INDEX IF NOT EXISTS idx_memories_group_updated ON memories(group_id, updated_at DESC)')
        )
        connection.execute(text('PRAGMA foreign_keys=ON'))


_migrate_sqlite_memories_table()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
