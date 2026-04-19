import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.memory_repository import MemoryRepository
from app.schemas.memory import MemoryClipCreate, MemoryCreate, MemoryUpdate
from app.workers.title_generation_worker import title_generation_worker

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, repository: MemoryRepository | None = None) -> None:
        self.repository = repository or MemoryRepository()

    def create_memory(self, db: Session, payload: MemoryCreate):
        return self.repository.create(db, payload)

    async def create_pending_title_memory(
        self,
        db: Session,
        *,
        content: str,
        group_id: str = 'default',
        source_platform: str | None = None,
        source_url: str | None = None,
        source_type: str | None = None,
    ):
        memory_payload = MemoryCreate(
            title='标题生成中',
            content=content,
            group_id=group_id.strip() or 'default',
            title_status='pending',
            source_platform=source_platform,
            source_url=source_url,
            source_type=source_type,
        )
        memory = self.repository.create(db, memory_payload)
        await title_generation_worker.enqueue(memory.id)
        logger.info("Created pending-title memory: memory_id=%s", memory.id)
        return memory

    async def create_memory_clip(self, db: Session, payload: MemoryClipCreate):
        logger.info(
            "Creating memory clip payload: title=%s source_platform=%s source_type=%s content_length=%s",
            payload.title,
            payload.source_platform,
            payload.source_type,
            len(payload.content or ""),
        )
        memory = await self.create_pending_title_memory(
            db,
            content=payload.content,
            source_platform=payload.source_platform,
            source_url=payload.source_url,
            source_type=payload.source_type,
        )
        logger.info("Created memory clip record: memory_id=%s title=%s", memory.id, memory.title)
        return memory

    def list_memories(self, db: Session, keyword: str | None = None, group_id: str | None = None):
        return self.repository.list(db, keyword=keyword, group_id=group_id)

    def get_memory(self, db: Session, memory_id: str):
        memory = self.repository.get(db, memory_id)
        if memory is None:
            raise HTTPException(status_code=404, detail="Memory not found")
        return memory

    def update_memory(self, db: Session, memory_id: str, payload: MemoryUpdate):
        memory = self.get_memory(db, memory_id)
        payload_data = payload.model_dump(exclude_none=True)
        edited_title = payload_data.get('title')
        edited_content = payload_data.get('content')
        has_graph_relevant_change = edited_title != memory.title or edited_content != memory.content

        if has_graph_relevant_change:
            memory.graph_status = 'not_added'
            memory.graph_error = None
            memory.graph_episode_uuid = None
            memory.graph_added_at = None
            logger.info('Memory %s edited; graph status reset to not_added', memory_id)

        return self.repository.update(db, memory, payload)

    def delete_memory(self, db: Session, memory_id: str) -> None:
        memory = self.get_memory(db, memory_id)
        self.repository.delete(db, memory)

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
            HTTPException: If memory not found
        """
        memory = self.get_memory(db, memory_id)
        
        # Pending with active retry keeps idempotent behavior; added supports re-submit.
        if memory.graph_status == 'pending':
            has_retry_meta = bool(memory.graph_error and memory.graph_error.startswith('__retry__:'))
            if has_retry_meta:
                logger.info('Memory %s is pending with active retry metadata; skip re-queue', memory_id)
                return memory

            logger.warning('Memory %s is pending but no retry metadata; treat as zombie and re-enqueue', memory_id)
            await worker.enqueue(memory_id)
            logger.info('Memory %s zombie pending task re-enqueued', memory_id)
            return memory
        if memory.graph_status == 'added':
            logger.info('Memory %s already in graph; re-submit with soft overwrite mode', memory_id)
        
        memory.graph_status = 'pending'
        memory.graph_error = None
        db.commit()
        logger.info('Memory %s status set to pending; queued for graph ingestion', memory_id)
        
        await worker.enqueue(memory_id)
        logger.info('Memory %s enqueue request submitted to GraphitiIngestWorker', memory_id)
        
        return memory

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
        
        # Filter out active pending; include added for re-submit
        to_queue = []
        for memory in memories:
            if memory.graph_status != 'pending':
                memory.graph_status = 'pending'
                memory.graph_error = None
                to_queue.append(memory.id)
        
        db.commit()
        
        # Enqueue all
        for memory_id in to_queue:
            await worker.enqueue(memory_id)
            logger.info('Batch enqueue memory %s for graph ingestion', memory_id)
        
        logger.info('Batch add-to-graph queued_count=%s memory_ids=%s', len(to_queue), to_queue)
        return {
            'queued_count': len(to_queue),
            'memory_ids': to_queue,
        }

    async def recover_pending_graph_tasks(self, db: Session, worker) -> int:
        """Recover pending graph tasks on startup by re-enqueuing them.

        Since worker queues are in-memory, backend restarts can leave DB records in
        ``pending`` without actual queue items. This routine re-queues pending records
        so ingestion can continue automatically after restart.
        """
        memories = self.repository.list(db)
        pending_memories = [memory for memory in memories if memory.graph_status == 'pending']

        if not pending_memories:
            logger.info('Startup graph recovery: no pending memories found')
            return 0

        recovered_ids: list[str] = []
        failed_recovery_ids: list[str] = []

        for memory in pending_memories:
            try:
                await worker.enqueue(memory.id)
                recovered_ids.append(memory.id)
            except Exception as error:
                memory.graph_status = 'failed'
                memory.graph_error = f'Startup recovery failed: {error}'
                failed_recovery_ids.append(memory.id)
                logger.error(
                    'Startup graph recovery failed to enqueue memory %s: %s',
                    memory.id,
                    error,
                    exc_info=True,
                )

        if failed_recovery_ids:
            db.commit()

        logger.warning(
            'Startup graph recovery complete: recovered=%s failed=%s pending_ids=%s',
            len(recovered_ids),
            len(failed_recovery_ids),
            recovered_ids,
        )

        return len(recovered_ids)
