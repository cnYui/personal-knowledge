from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage


class ChatRepository:
    def create(self, db: Session, role: str, content: str) -> ChatMessage:
        message = ChatMessage(role=role, content=content)
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    def list(self, db: Session) -> list[ChatMessage]:
        return list(db.scalars(select(ChatMessage).order_by(ChatMessage.created_at.asc())))

    def clear(self, db: Session) -> None:
        for message in self.list(db):
            db.delete(message)
        db.commit()
