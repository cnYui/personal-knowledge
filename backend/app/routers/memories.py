import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_worker
from app.schemas.graph import AddToGraphResponse, BatchAddToGraphRequest, BatchAddToGraphResponse, GraphStatusResponse
from app.schemas.memory import MemoryClipCreate, MemoryCreate, MemoryRead, MemoryUpdate
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/api/memories", tags=["memories"])
service = MemoryService()
logger = logging.getLogger(__name__)


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
def create_memory(payload: MemoryCreate, db: Session = Depends(get_db)) -> MemoryRead:
    return service.create_memory(db, payload)


@router.post("/clip", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
def create_memory_clip(payload: MemoryClipCreate, db: Session = Depends(get_db)) -> MemoryRead:
    logger.info(
        "Received browser clip save request: title=%s source_platform=%s source_type=%s source_url=%s content_length=%s",
        payload.title,
        payload.source_platform,
        payload.source_type,
        payload.source_url,
        len(payload.content or ""),
    )
    memory = service.create_memory_clip(db, payload)
    logger.info("Browser clip saved successfully: memory_id=%s title=%s", memory.id, memory.title)
    return memory


@router.get("", response_model=list[MemoryRead])
def list_memories(
    keyword: str | None = None,
    group_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[MemoryRead]:
    return service.list_memories(db, keyword=keyword, group_id=group_id)


@router.post('/{memory_id}/add-to-graph', response_model=AddToGraphResponse, status_code=status.HTTP_202_ACCEPTED)
async def add_memory_to_graph(
    memory_id: str,
    db: Session = Depends(get_db),
    worker = Depends(get_worker),
) -> AddToGraphResponse:
    """Queue a single memory for knowledge graph ingestion."""
    memory = await service.add_to_graph(db, memory_id, worker)
    
    return AddToGraphResponse(
        message='Memory queued for knowledge graph ingestion',
        memory_id=memory.id,
        graph_status=memory.graph_status,
    )


@router.post('/batch-add-to-graph', response_model=BatchAddToGraphResponse, status_code=status.HTTP_202_ACCEPTED)
async def batch_add_to_graph(
    payload: BatchAddToGraphRequest,
    db: Session = Depends(get_db),
    worker = Depends(get_worker),
) -> BatchAddToGraphResponse:
    """Queue multiple memories for knowledge graph ingestion."""
    result = await service.batch_add_to_graph(db, payload.memory_ids, worker)
    
    return BatchAddToGraphResponse(
        message=f"{result['queued_count']} memories queued for knowledge graph ingestion",
        queued_count=result['queued_count'],
        memory_ids=result['memory_ids'],
    )


@router.get('/{memory_id}/graph-status', response_model=GraphStatusResponse)
def get_graph_status(memory_id: str, db: Session = Depends(get_db)) -> GraphStatusResponse:
    """Get knowledge graph ingestion status for a memory."""
    memory = service.get_memory(db, memory_id)
    
    return GraphStatusResponse(
        memory_id=memory.id,
        graph_status=memory.graph_status,
        graph_episode_uuid=memory.graph_episode_uuid,
        graph_added_at=memory.graph_added_at.isoformat() if memory.graph_added_at else None,
        graph_error=memory.graph_error,
    )


@router.get("/{memory_id}", response_model=MemoryRead)
def get_memory(memory_id: str, db: Session = Depends(get_db)) -> MemoryRead:
    return service.get_memory(db, memory_id)


@router.put("/{memory_id}", response_model=MemoryRead)
def update_memory(memory_id: str, payload: MemoryUpdate, db: Session = Depends(get_db)) -> MemoryRead:
    return service.update_memory(db, memory_id, payload)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(memory_id: str, db: Session = Depends(get_db)) -> Response:
    service.delete_memory(db, memory_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
