from __future__ import annotations

from app.workflow.nodes.base import WorkflowNode


class MessageNode(WorkflowNode):
    node_type = 'message'

    async def execute(self, context, canvas):
        source_ref = self.config.get('source_ref')
        if not source_ref:
            source_ref = f'node:{canvas.execution_path[-1]}' if canvas.execution_path else 'sys.query'
        source = self.resolve_reference(source_ref, context) if isinstance(source_ref, str) else source_ref

        if hasattr(source, 'model_dump'):
            source = source.model_dump()

        if isinstance(source, dict):
            answer = source.get('answer') or source.get('content') or ''
            references = source.get('references') or []
        else:
            answer = str(source)
            references = []

        payload = {
            'content': answer,
            'references': references,
        }
        context.set_global(self.config.get('output_key', 'workflow.message'), payload)
        return payload
