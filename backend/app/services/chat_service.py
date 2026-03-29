from sqlalchemy.orm import Session

from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatResponse
from app.services.knowledge_graph_service import KnowledgeGraphService


class ChatService:
    def __init__(
        self,
        repository: ChatRepository | None = None,
        knowledge_graph_service: KnowledgeGraphService | None = None,
    ) -> None:
        self.repository = repository or ChatRepository()
        self.knowledge_graph_service = knowledge_graph_service or KnowledgeGraphService()

    def send_message(self, db: Session, message: str) -> ChatResponse:
        self.repository.create(db, "user", message)
        result = self.knowledge_graph_service.ask(message)
        self.repository.create(db, "assistant", str(result["answer"]))
        return ChatResponse(answer=str(result["answer"]), references=list(result["references"]))

    def list_messages(self, db: Session):
        return self.repository.list(db)

    def clear_messages(self, db: Session) -> None:
        self.repository.clear(db)
