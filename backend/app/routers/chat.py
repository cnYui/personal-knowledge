from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatMessageRead, ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])
service = ChatService()


@router.post("/messages", response_model=ChatResponse)
async def send_message(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return await service.send_message(db, payload.message)


@router.post("/rag", response_model=ChatResponse)
async def rag_query(payload: ChatRequest) -> ChatResponse:
    """RAG query without saving to database (for localStorage-based chat)"""
    return await service.rag_query(payload.message)


@router.post("/stream")
async def rag_stream(payload: ChatRequest):
    """Streaming RAG query for real-time chat experience"""
    return StreamingResponse(
        service.rag_stream(payload.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/messages", response_model=list[ChatMessageRead])
def get_messages(db: Session = Depends(get_db)) -> list[ChatMessageRead]:
    return service.list_messages(db)


@router.delete("/messages")
def clear_messages(db: Session = Depends(get_db)) -> dict[str, bool]:
    service.clear_messages(db)
    return {"success": True}
