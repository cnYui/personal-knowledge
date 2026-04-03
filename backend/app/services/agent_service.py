import logging
from collections.abc import AsyncGenerator
from typing import Any

from app.core.model_errors import ModelAPIError
from app.schemas.chat import ChatReference
from app.services.agent_tools.graph_retrieval_tool import GraphRetrievalTool
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.workflow.canvas_factory import CanvasFactory
from app.workflow.engine.citation_postprocessor import CitationPostProcessor, CitationResult

logger = logging.getLogger(__name__)


class AgentService:
    """Legacy compatibility wrapper around the Canvas-based agentic chat workflow."""

    def __init__(
        self,
        graph_retrieval_tool: GraphRetrievalTool | None = None,
        knowledge_graph_service: KnowledgeGraphService | None = None,
        canvas_factory: CanvasFactory | None = None,
        citation_postprocessor: CitationPostProcessor | None = None,
    ) -> None:
        shared_knowledge_graph_service = knowledge_graph_service or getattr(
            graph_retrieval_tool, 'knowledge_graph_service', None
        )
        self.canvas_factory = canvas_factory or CanvasFactory(
            knowledge_graph_service=shared_knowledge_graph_service,
            graph_retrieval_tool=graph_retrieval_tool,
        )
        self.citation_postprocessor = citation_postprocessor or CitationPostProcessor()

    def _collect_references(
        self,
        canvas,
        fallback_references: list[Any] | None = None,
    ) -> list[ChatReference]:
        references: list[ChatReference] = []
        for evidence in canvas.reference_store.snapshot().get('graph_evidence', []):
            try:
                references.append(ChatReference.model_validate(evidence))
            except Exception:
                logger.debug('Skip invalid graph evidence for chat references: %s', evidence)
        if references:
            return references

        normalized_fallback: list[ChatReference] = []
        for item in fallback_references or []:
            if hasattr(item, 'model_dump'):
                normalized_fallback.append(ChatReference.model_validate(item.model_dump()))
            elif isinstance(item, dict):
                normalized_fallback.append(ChatReference.model_validate(item))
        return normalized_fallback

    def _augment_trace(
        self,
        trace: Any,
        *,
        execution_path: list[str],
        canvas_events: list[dict[str, Any]],
        citation_result: CitationResult,
        reference_store_snapshot: dict[str, Any],
        workflow_debug: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if trace is None:
            return None
        trace_payload = trace.model_dump() if hasattr(trace, 'model_dump') else dict(trace)
        trace_payload['canvas'] = {
            'execution_path': execution_path,
            'events': canvas_events,
        }
        trace_payload['tool_loop'] = workflow_debug or {
            'forced_retrieval': False,
            'tool_rounds_exceeded': False,
            'tool_steps': [],
        }
        trace_payload['citation'] = {
            'count': len(citation_result.citations),
            'used_general_fallback': citation_result.used_general_fallback,
            'items': [
                {
                    'index': citation['index'],
                    'type': citation['type'],
                    'label': citation['label'],
                }
                for citation in citation_result.citations
            ],
        }
        trace_payload['reference_store'] = {
            'chunk_count': len(reference_store_snapshot.get('chunks', [])),
            'doc_count': len(reference_store_snapshot.get('doc_aggs', [])),
            'graph_evidence_count': len(reference_store_snapshot.get('graph_evidence', [])),
        }
        return trace_payload

    async def _run_chat_canvas(self, query: str, *, group_id: str = 'default') -> dict[str, Any]:
        canvas = self.canvas_factory.create_chat_canvas(query=query, group_id=group_id)
        agent_output: dict[str, Any] | None = None
        message_output: dict[str, Any] | None = None
        canvas_events: list[dict[str, Any]] = []

        async for event in canvas.run():
            if event.node_id:
                canvas_events.append(
                    {
                        'event': event.event,
                        'node_id': event.node_id,
                        'node_type': getattr(event, 'node_type', None),
                    }
                )
            if event.event != 'node_finished':
                continue
            if event.node_id == 'agent':
                agent_output = event.payload.get('output') or {}
            elif event.node_id == 'message':
                message_output = event.payload.get('output') or {}

        if message_output is None:
            raise RuntimeError('Canvas workflow did not produce a message output')

        citation_result = self.citation_postprocessor.process(
            answer=str(message_output.get('content') or ''),
            reference_store=canvas.reference_store,
        )
        reference_store_snapshot = canvas.reference_store.snapshot()
        references = self._collect_references(
            canvas,
            fallback_references=list(message_output.get('references') or []),
        )
        agent_trace = self._augment_trace(
            (agent_output or {}).get('agent_trace'),
            execution_path=list(canvas.execution_path),
            canvas_events=canvas_events,
            citation_result=citation_result,
            reference_store_snapshot=reference_store_snapshot,
            workflow_debug=(agent_output or {}).get('workflow_debug'),
        )
        return {
            'answer': citation_result.answer,
            'references': references,
            'agent_trace': agent_trace,
        }

    async def ask(self, query: str, group_id: str = 'default') -> dict:
        try:
            return await self._run_chat_canvas(query, group_id=group_id)
        except Exception as exc:
            logger.error('Error in legacy-compatible agent ask: %s', exc, exc_info=True)
            return {
                'answer': f'抱歉，处理您的问题时出现错误：{str(exc)}',
                'references': [],
                'agent_trace': None,
            }

    async def ask_stream(self, query: str, group_id: str = 'default') -> AsyncGenerator[dict, None]:
        try:
            result = await self._run_chat_canvas(query, group_id=group_id)
            yield {'type': 'trace', 'content': result.get('agent_trace')}
            yield {
                'type': 'references',
                'content': [
                    reference.model_dump() if hasattr(reference, 'model_dump') else reference
                    for reference in result.get('references', [])
                ],
            }
            yield {'type': 'content', 'content': str(result.get('answer', ''))}
            yield {'type': 'done', 'content': ''}
        except Exception as exc:
            logger.error('Error in legacy-compatible agent stream: %s', exc, exc_info=True)
            if isinstance(exc, ModelAPIError):
                yield {'type': 'error', 'content': exc.message, **exc.to_dict()}
                return
            yield {
                'type': 'error',
                'content': str(exc),
                'error_code': 'UNKNOWN_ERROR',
                'message': str(exc),
                'details': '',
                'provider': '',
                'retryable': False,
            }
