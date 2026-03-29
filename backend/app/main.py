import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.routers.chat import router as chat_router
from app.routers.memories import router as memories_router
from app.routers.uploads import router as uploads_router
from app.workers import GraphitiIngestWorker
from app.workers.title_generation_worker import title_generation_worker
from app import dependencies

logger = logging.getLogger(__name__)

# Initialize database before creating app
init_db()

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


@app.on_event('startup')
async def startup_event():
    """Initialize and start workers on application startup."""
    # Start Graphiti ingest worker
    dependencies.graphiti_worker = GraphitiIngestWorker()
    asyncio.create_task(dependencies.graphiti_worker.start())
    
    # Start title generation worker
    await title_generation_worker.start()
    
    logger.info('Application startup complete, workers started')


@app.on_event('shutdown')
async def shutdown_event():
    """Stop workers gracefully on application shutdown."""
    # Stop Graphiti worker
    if dependencies.graphiti_worker:
        await dependencies.graphiti_worker.stop()
        
        # Wait for queue to drain (with timeout)
        try:
            await asyncio.wait_for(dependencies.graphiti_worker.queue.join(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning('Graphiti queue did not drain within timeout, forcing shutdown')
    
    # Stop title generation worker
    await title_generation_worker.stop()
    
    logger.info('Application shutdown complete')


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
