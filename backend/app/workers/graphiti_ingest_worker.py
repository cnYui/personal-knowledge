import asyncio
import logging
from datetime import datetime

from app.core.database import SessionLocal
from app.repositories.memory_repository import MemoryRepository
from app.services.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)


class GraphitiIngestWorker:
    """Background worker that processes memory ingestion into knowledge graph."""

    def __init__(self):
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.running = False
        self.graphiti_client = GraphitiClient()
        self.repository = MemoryRepository()
        self._task = None

    async def start(self):
        """Start the background worker loop."""
        if self.running:
            logger.warning('Worker already running')
            return
        
        self.running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info('GraphitiIngestWorker started')

    async def stop(self):
        """Stop the worker gracefully."""
        if not self.running:
            return
        
        self.running = False
        if self._task:
            await self._task
        await self.graphiti_client.close()
        logger.info('GraphitiIngestWorker stopped')

    async def enqueue(self, memory_id: str):
        """Add a memory ID to the processing queue."""
        await self.queue.put(memory_id)
        logger.debug(f'Enqueued memory {memory_id}')

    async def _worker_loop(self):
        """Main worker loop that processes queue items."""
        while self.running:
            try:
                memory_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._process_memory(memory_id)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f'Error in worker loop: {e}', exc_info=True)

    async def _process_memory(self, memory_id: str):
        """Process a single memory by adding it to the knowledge graph."""
        db = SessionLocal()
        try:
            memory = self.repository.get(db, memory_id)
            if not memory:
                logger.error(f'Memory {memory_id} not found')
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
            memory.graph_added_at = datetime.now()
            memory.graph_error = None
            db.commit()

            logger.info(f'Memory {memory_id} successfully added to graph')

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
