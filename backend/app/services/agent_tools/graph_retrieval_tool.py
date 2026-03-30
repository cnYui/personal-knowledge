from app.schemas.agent import GraphRetrievalResult
from app.services.knowledge_graph_service import KnowledgeGraphService


class GraphRetrievalTool:
    name = 'graph_retrieval_tool'
    description = 'Search the Graphiti temporal knowledge graph and return evidence for answering the user question.'

    def __init__(self, knowledge_graph_service: KnowledgeGraphService | None = None) -> None:
        self.knowledge_graph_service = knowledge_graph_service or KnowledgeGraphService()

    async def run(self, query: str, group_id: str = 'default') -> GraphRetrievalResult:
        return await self.knowledge_graph_service.retrieve_graph_context(query, group_id=group_id)