import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.routers.chat import router as chat_router
from app.routers.memories import router as memories_router
from app.routers.uploads import router as uploads_router
from app.workers import GraphitiIngestWorker
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
