import asyncio
import logging

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import SessionLocal, init_db
from app.core.model_errors import ModelAPIError
from app.routers.chat import router as chat_router
from app.routers.graph import router as graph_router
from app.routers.memories import router as memories_router
from app.routers.prompts import router as prompts_router
from app.routers.settings import router as settings_router
from app.services.memory_service import MemoryService
from app.routers.uploads import router as uploads_router
from app.routers.text_optimization import router as text_router
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
app.include_router(graph_router)
app.include_router(memories_router)
app.include_router(prompts_router)
app.include_router(settings_router)
app.include_router(uploads_router)
app.include_router(text_router)


@app.exception_handler(ModelAPIError)
async def handle_model_api_error(_: Request, exc: ModelAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.on_event('startup')
async def startup_event():
    """Initialize and start workers on application startup."""
    # Start Graphiti ingest worker
    dependencies.graphiti_worker = GraphitiIngestWorker()
    await dependencies.graphiti_worker.start()

    memory_service = MemoryService()
    db = SessionLocal()
    try:
        recovered_count = await memory_service.recover_pending_graph_tasks(db, dependencies.graphiti_worker)
        logger.info('Startup graph pending recovery finished: recovered_count=%s', recovered_count)
    finally:
        db.close()
    
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
