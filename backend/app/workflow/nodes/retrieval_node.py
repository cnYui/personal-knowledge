from __future__ import annotations

from app.services.knowledge_graph_service import KnowledgeGraphService
from app.workflow.nodes.base import WorkflowNode


class RetrievalNode(WorkflowNode):
    node_type = 'retrieval'

    def __init__(
        self,
        spec,
        *,
        knowledge_graph_service: KnowledgeGraphService | None = None,
    ) -> None:
        super().__init__(spec)
        self.knowledge_graph_service = knowledge_graph_service or KnowledgeGraphService()

    async def execute(self, context, canvas):
        query_ref = self.config.get('query_ref', 'sys.query')
        group_id = self.config.get('group_id', 'default')
        output_key = self.config.get('output_key', f'{self.node_id}.result')

        query = self.resolve_reference(query_ref, context) if isinstance(query_ref, str) else query_ref
        retrieval_result = await self.knowledge_graph_service.retrieve_graph_context(
            str(query or ''),
            group_id=group_id,
        )

        canvas.reference_store.merge(
            chunks=[
                {'id': f'{self.node_id}-chunk-{index}', 'content': ref.fact or ref.summary or ref.name or ref.type}
                for index, ref in enumerate(retrieval_result.references)
            ],
            graph_evidence=[
                ref.model_dump()
                for ref in retrieval_result.references
            ],
        )
        context.set_global(output_key, retrieval_result)
        return retrieval_result
