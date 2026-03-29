from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.memory_repository import MemoryRepository
from app.schemas.memory import MemoryCreate, MemoryUpdate


class MemoryService:
    def __init__(self, repository: MemoryRepository | None = None) -> None:
        self.repository = repository or MemoryRepository()

    def create_memory(self, db: Session, payload: MemoryCreate):
        return self.repository.create(db, payload)

    def list_memories(self, db: Session, keyword: str | None = None, group_id: str | None = None):
        return self.repository.list(db, keyword=keyword, group_id=group_id)

    def get_memory(self, db: Session, memory_id: str):
        memory = self.repository.get(db, memory_id)
        if memory is None:
            raise HTTPException(status_code=404, detail="Memory not found")
        return memory

    def update_memory(self, db: Session, memory_id: str, payload: MemoryUpdate):
        memory = self.get_memory(db, memory_id)
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
