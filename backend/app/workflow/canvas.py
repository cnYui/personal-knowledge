from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator, Callable
from typing import Any

from app.workflow.dsl import WorkflowDSL, WorkflowNodeSpec
from app.workflow.events import CanvasEvent
from app.workflow.reference_store import ReferenceStore
from app.workflow.runtime_context import RuntimeContext

NodeFactory = Callable[[WorkflowNodeSpec], Any]


class Canvas:
    def __init__(
        self,
        dsl: WorkflowDSL | dict[str, Any],
        *,
        context: RuntimeContext | None = None,
        reference_store: ReferenceStore | None = None,
    ) -> None:
        self.dsl = dsl if isinstance(dsl, WorkflowDSL) else WorkflowDSL.from_dict(dsl)
        self.context = context or RuntimeContext()
        self.reference_store = reference_store or ReferenceStore()
        self._registry: dict[str, NodeFactory] = {}
        self._node_specs = self.dsl.node_map()
        self.execution_path: list[str] = []
        self._runtime_event_sink: Callable[[dict[str, Any]], None] | None = None

    def register_node_type(self, node_type: str, factory: NodeFactory) -> None:
        self._registry[node_type] = factory

    def set_runtime_event_sink(self, sink: Callable[[dict[str, Any]], None] | None) -> None:
        self._runtime_event_sink = sink

    def emit_runtime_event(self, event: dict[str, Any]) -> None:
        if self._runtime_event_sink is not None:
            self._runtime_event_sink(event)

    def get_node_spec(self, node_id: str) -> WorkflowNodeSpec:
        return self._node_specs[node_id]

    def _instantiate_node(self, node_id: str) -> Any:
        spec = self.get_node_spec(node_id)
        if spec.type not in self._registry:
            raise KeyError(f'Node type "{spec.type}" is not registered')
        return self._registry[spec.type](spec)

    async def _execute_node(self, node: Any) -> Any:
        result = node.execute(self.context, self)
        if inspect.isawaitable(result):
            return await result
        return result

    async def run(self) -> AsyncGenerator[CanvasEvent, None]:
        queue: list[str] = [self.dsl.entry_node_id]
        visited: set[str] = set()

        yield CanvasEvent(
            event='workflow_started',
            payload={
                'entry_node_id': self.dsl.entry_node_id,
                'metadata': self.dsl.metadata,
            },
        )

        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)

            node = self._instantiate_node(node_id)
            spec = self.get_node_spec(node_id)
            self.execution_path.append(node_id)

            yield CanvasEvent(
                event='node_started',
                node_id=node_id,
                node_type=spec.type,
                payload={'config': spec.config},
            )

            result = await self._execute_node(node)
            self.context.set_node_output(node_id, result)

            yield CanvasEvent(
                event='node_finished',
                node_id=node_id,
                node_type=spec.type,
                payload={'output': result},
            )

            for downstream_id in spec.downstream:
                if downstream_id not in visited:
                    queue.append(downstream_id)

        yield CanvasEvent(
            event='workflow_finished',
            payload={
                'execution_path': list(self.execution_path),
                'reference_store': self.reference_store.snapshot(),
            },
        )
