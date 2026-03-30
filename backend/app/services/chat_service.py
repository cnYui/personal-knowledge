import json
import logging

from sqlalchemy.orm import Session

from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatResponse
from app.services.agent_service import AgentService

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        repository: ChatRepository | None = None,
        agent_service: AgentService | None = None,
    ) -> None:
        self.repository = repository or ChatRepository()
        self.agent_service = agent_service or AgentService()

    async def send_message(self, db: Session, message: str) -> ChatResponse:
        """Send message and save to database"""
        self.repository.create(db, "user", message)
        result = await self.agent_service.ask(message)
        self.repository.create(db, "assistant", str(result["answer"]))
        return ChatResponse(
            answer=str(result["answer"]),
            references=list(result["references"]),
            agent_trace=result.get("agent_trace"),
        )

    async def rag_query(self, message: str) -> ChatResponse:
        """RAG query without saving to database (for localStorage-based chat)"""
        result = await self.agent_service.ask(message)
        return ChatResponse(
            answer=str(result["answer"]),
            references=list(result["references"]),
            agent_trace=result.get("agent_trace"),
        )

    async def rag_stream(self, message: str):
        """Streaming RAG query for real-time chat experience"""
        try:
            # Stream the response directly from ask_stream (it's already an async generator)
            async for chunk in self.agent_service.ask_stream(message):
                # Send as SSE format
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Error in streaming RAG: {e}", exc_info=True)
            error_chunk = {"type": "error", "content": str(e)}
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

    def list_messages(self, db: Session):
        return self.repository.list(db)

    def clear_messages(self, db: Session) -> None:
        self.repository.clear(db)
