from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class WorkflowNodeSpec(BaseModel):
    id: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)
    downstream: list[str] = Field(default_factory=list)


class WorkflowDSL(BaseModel):
    entry_node_id: str
    nodes: list[WorkflowNodeSpec]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_graph(self) -> 'WorkflowDSL':
        node_ids = {node.id for node in self.nodes}
        if self.entry_node_id not in node_ids:
            raise ValueError(f'entry_node_id "{self.entry_node_id}" does not exist in nodes')

        for node in self.nodes:
            for downstream_id in node.downstream:
                if downstream_id not in node_ids:
                    raise ValueError(
                        f'Node "{node.id}" points to missing downstream node "{downstream_id}"'
                    )
        return self

    def node_map(self) -> dict[str, WorkflowNodeSpec]:
        return {node.id: node for node in self.nodes}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'WorkflowDSL':
        return cls.model_validate(data)
