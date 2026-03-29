from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatMessageRead, ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat/messages", tags=["chat"])
service = ChatService()


@router.post("", response_model=ChatResponse)
def send_message(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return service.send_message(db, payload.message)


@router.get("", response_model=list[ChatMessageRead])
def get_messages(db: Session = Depends(get_db)) -> list[ChatMessageRead]:
    return service.list_messages(db)


@router.delete("")
def clear_messages(db: Session = Depends(get_db)) -> dict[str, bool]:
    service.clear_messages(db)
    return {"success": True}
