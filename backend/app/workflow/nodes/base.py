from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.workflow.dsl import WorkflowNodeSpec


class WorkflowNode(ABC):
    node_type = 'base'

    def __init__(self, spec: WorkflowNodeSpec) -> None:
        self.spec = spec
        self.node_id = spec.id
        self.config = spec.config

    def validate(self) -> None:
        return

    def to_event_payload(self) -> dict[str, Any]:
        return {'config': self.config}

    def resolve_reference(self, ref: str, context) -> Any:
        if ref.startswith('sys.') or ref.startswith('env.') or ref.startswith('workflow.'):
            return context.get_global(ref)
        if ref.startswith('node:'):
            return context.get_node_output(ref.split(':', 1)[1])
        return context.get_global(ref)

    @abstractmethod
    async def execute(self, context, canvas) -> Any:
        raise NotImplementedError
