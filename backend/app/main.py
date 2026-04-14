import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import SessionLocal, init_db
from app.core.model_errors import ModelAPIError
from app.routers.chat import router as chat_router
from app.routers.daily_review import router as daily_review_router
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

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )

logger = logging.getLogger(__name__)

# Initialize database before creating app
logger.info('Bootstrapping application module import: starting database initialization.')
init_db()
logger.info('Bootstrapping application module import: database initialization finished.')


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    logger.info('Application startup sequence started.')

    try:
        logger.info('Startup step 1/3: initializing GraphitiIngestWorker.')
        dependencies.graphiti_worker = GraphitiIngestWorker()
        await dependencies.graphiti_worker.start()
        logger.info('Startup step 1/3 complete: GraphitiIngestWorker started.')
    except Exception as error:
        logger.error('Startup step 1/3 failed while starting GraphitiIngestWorker: %s', error, exc_info=True)
        raise

    memory_service = MemoryService()
    db = SessionLocal()
    try:
        logger.info('Startup step 2/3: recovering pending graph ingestion tasks.')
        recovered_count = await memory_service.recover_pending_graph_tasks(db, dependencies.graphiti_worker)
        logger.info('Startup step 2/3 complete: recovered_count=%s', recovered_count)
    except Exception as error:
        logger.error('Startup step 2/3 failed during pending graph recovery: %s', error, exc_info=True)
        raise
    finally:
        db.close()

    try:
        logger.info('Startup step 3/3: starting title generation worker.')
        await title_generation_worker.start()
        logger.info('Startup step 3/3 complete: title generation worker started.')
    except Exception as error:
        logger.error('Startup step 3/3 failed while starting title generation worker: %s', error, exc_info=True)
        raise

    logger.info('Application startup complete, all startup stages succeeded.')

    try:
        yield
    finally:
        logger.info('Application shutdown sequence started.')

        if dependencies.graphiti_worker:
            try:
                logger.info('Shutdown step 1/2: stopping GraphitiIngestWorker.')
                await dependencies.graphiti_worker.stop()
                try:
                    await asyncio.wait_for(dependencies.graphiti_worker.queue.join(), timeout=30.0)
                    logger.info('Shutdown step 1/2 complete: Graphiti queue drained successfully.')
                except asyncio.TimeoutError:
                    logger.warning('Graphiti queue did not drain within timeout, forcing shutdown.')
            except Exception as error:
                logger.error('Shutdown step 1/2 failed while stopping GraphitiIngestWorker: %s', error, exc_info=True)

        try:
            logger.info('Shutdown step 2/2: stopping title generation worker.')
            await title_generation_worker.stop()
            logger.info('Shutdown step 2/2 complete: title generation worker stopped.')
        except Exception as error:
            logger.error('Shutdown step 2/2 failed while stopping title generation worker: %s', error, exc_info=True)

        logger.info('Application shutdown complete.')


app = FastAPI(title="Personal Knowledge Base API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=(
        r"(chrome-extension|moz-extension)://.*"
        r"|https://("
        r"chat\.openai\.com"
        r"|chatgpt\.com"
        r"|gemini\.google\.com"
        r"|kimi\.moonshot\.cn"
        r"|(?:www\.)?kimi\.com"
        r"|tongyi\.aliyun\.com"
        r"|qianwen\.aliyun\.com"
        r"|(?:www\.)?qianwen\.com"
        r"|(?:www\.)?doubao\.com"
        r")"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)
app.include_router(daily_review_router)
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
