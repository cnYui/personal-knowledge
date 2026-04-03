from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.agent_tools.graph_retrieval_tool import GraphRetrievalTool
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.workflow.canvas import Canvas
from app.workflow.dsl import WorkflowDSL
from app.workflow.nodes import AgentNode, BeginNode, MessageNode, RetrievalNode
from app.workflow.runtime_context import RuntimeContext

TEMPLATE_DIR = Path(__file__).resolve().parent / 'templates'


class CanvasFactory:
    def __init__(
        self,
        *,
        knowledge_graph_service: KnowledgeGraphService | None = None,
        graph_retrieval_tool: GraphRetrievalTool | None = None,
    ) -> None:
        shared_knowledge_graph_service = knowledge_graph_service or getattr(
            graph_retrieval_tool, 'knowledge_graph_service', None
        )
        self.knowledge_graph_service = shared_knowledge_graph_service
        self.graph_retrieval_tool = graph_retrieval_tool

    def _get_knowledge_graph_service(self) -> KnowledgeGraphService:
        if self.knowledge_graph_service is None:
            self.knowledge_graph_service = KnowledgeGraphService()
        return self.knowledge_graph_service

    def _get_graph_retrieval_tool(self) -> GraphRetrievalTool:
        if self.graph_retrieval_tool is None:
            self.graph_retrieval_tool = GraphRetrievalTool(
                knowledge_graph_service=self._get_knowledge_graph_service()
            )
        return self.graph_retrieval_tool

    def _load_template(self, template_name: str) -> WorkflowDSL:
        template_path = TEMPLATE_DIR / template_name
        with template_path.open('r', encoding='utf-8') as file:
            return WorkflowDSL.from_dict(json.load(file))

    def create_chat_canvas(
        self,
        *,
        query: str,
        history: list[dict[str, Any]] | None = None,
        files: list[Any] | None = None,
        user_id: str | None = None,
        group_id: str = 'default',
    ) -> Canvas:
        dsl = self._load_template('chat_agentic_rag.json')
        for node in dsl.nodes:
            if node.id == 'agent':
                node.config = {**node.config, 'group_id': group_id}
        context = RuntimeContext(
            query=query,
            history=history or [],
            files=files or [],
            user_id=user_id,
        )
        canvas = Canvas(dsl, context=context)
        knowledge_graph_service = self._get_knowledge_graph_service()
        graph_retrieval_tool = self._get_graph_retrieval_tool()
        canvas.register_node_type('begin', lambda spec: BeginNode(spec))
        canvas.register_node_type(
            'retrieval',
            lambda spec: RetrievalNode(spec, knowledge_graph_service=knowledge_graph_service),
        )
        canvas.register_node_type(
            'agent',
            lambda spec: AgentNode(
                spec,
                knowledge_graph_service=knowledge_graph_service,
                graph_retrieval_tool=graph_retrieval_tool,
            ),
        )
        canvas.register_node_type('message', lambda spec: MessageNode(spec))
        return canvas
