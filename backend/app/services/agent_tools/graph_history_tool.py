from typing import Any

from app.schemas.agent import GraphHistoryQuery, GraphHistoryResult
from app.services.graph_history_service import GraphHistoryService


class GraphHistoryTool:
    name = 'graph_history_tool'
    description = 'Retrieve structured history evidence for a memory or entity from versioned graph knowledge.'

    def __init__(self, history_service: GraphHistoryService | None = None) -> None:
        self.history_service = history_service or GraphHistoryService()

    def run(
        self,
        target_type: str,
        target_value: str,
        mode: str,
        question: str = '',
        constraints: dict[str, Any] | None = None,
    ) -> GraphHistoryResult:
        return self.history_service.query(
            GraphHistoryQuery(
                target_type=target_type,
                target_value=target_value,
                mode=mode,
                question=question,
                constraints=constraints or {},
            )
        )