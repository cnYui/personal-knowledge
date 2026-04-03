from __future__ import annotations

from app.workflow.nodes.base import WorkflowNode


class BeginNode(WorkflowNode):
    node_type = 'begin'

    async def execute(self, context, canvas):
        payload = {
            'query': context.query,
            'history': list(context.history),
            'files': list(context.files),
            'user_id': context.user_id,
        }
        output_key = self.config.get('output_key', 'workflow.begin')
        context.set_global(output_key, payload)
        return payload
