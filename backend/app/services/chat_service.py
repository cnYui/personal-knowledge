import asyncio
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.model_errors import ModelAPIError
from app.repositories.chat_repository import ChatRepository
from app.schemas.agent import AgentTrace
from app.schemas.chat import ChatReference, ChatResponse
from app.workflow.canvas_factory import CanvasFactory
from app.workflow.engine.citation_postprocessor import CitationPostProcessor, CitationResult

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        repository: ChatRepository | None = None,
        canvas_factory: CanvasFactory | None = None,
        citation_postprocessor: CitationPostProcessor | None = None,
    ) -> None:
        self.repository = repository or ChatRepository()
        self.canvas_factory = canvas_factory or CanvasFactory()
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
            else:
                normalized_fallback.append(item)
        return normalized_fallback

    def _build_citation_section(self, citation_result: CitationResult) -> list[str]:
        return [str(citation.get('label') or '').strip() for citation in citation_result.citations if str(citation.get('label') or '').strip()]

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
        tool_loop_payload = workflow_debug or {
            'forced_retrieval': False,
            'tool_rounds_exceeded': False,
            'tool_steps': [],
        }
        if trace is None:
            trace = AgentTrace(
                mode='graph_rag',
                retrieval_rounds=len(tool_loop_payload.get('tool_steps') or []),
                final_action='timeline_only',
            )
        trace_payload = trace.model_dump() if hasattr(trace, 'model_dump') else dict(trace)
        trace_payload['canvas'] = {
            'execution_path': execution_path,
            'events': canvas_events,
        }
        trace_payload['tool_loop'] = tool_loop_payload
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

    def _timeline_chunk(
        self,
        *,
        event_id: str,
        kind: str,
        title: str,
        detail: str,
        status: str,
        order: int,
        preview_items: list[str] | None = None,
        preview_total: int | None = None,
    ) -> str:
        payload = {
            'type': 'timeline',
            'content': {
                'id': event_id,
                'kind': kind,
                'title': title,
                'detail': detail,
                'status': status,
                'order': order,
                'preview_items': preview_items or [],
                'preview_total': preview_total,
            },
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _timeline_chunks_from_canvas_event(self, event: Any, order: int) -> list[str]:
        chunks: list[str] = []

        if event.event == 'node_started' and event.node_id == 'agent':
            chunks.append(
                self._timeline_chunk(
                    event_id='understand-question',
                    kind='understand',
                    title='理解问题',
                    detail='正在理解你的问题。',
                    status='started',
                    order=order,
                )
            )

        return chunks

    def _timeline_chunk_from_runtime_event(self, event: dict[str, Any], order: int) -> str | None:
        if event.get('type') != 'timeline':
            return None
        return self._timeline_chunk(
            event_id=str(event.get('id') or f'runtime-{order}'),
            kind=str(event.get('kind') or 'canvas'),
            title=str(event.get('title') or '执行步骤'),
            detail=str(event.get('detail') or ''),
            status=str(event.get('status') or 'started'),
            order=order,
            preview_items=event.get('preview_items') if isinstance(event.get('preview_items'), list) else None,
            preview_total=event.get('preview_total') if isinstance(event.get('preview_total'), int) else None,
        )

    async def _run_chat_canvas(self, message: str, *, group_id: str = 'default') -> dict[str, Any]:
        if self.canvas_factory is None:
            raise RuntimeError('CanvasFactory is not configured')

        canvas = self.canvas_factory.create_chat_canvas(query=message, group_id=group_id)
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

        citation_result = await self.citation_postprocessor.process(
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
            'citation_section': self._build_citation_section(citation_result),
            'sentence_citations': list(citation_result.sentence_citations),
            'agent_trace': agent_trace,
        }

    async def send_message(self, db: Session, message: str) -> ChatResponse:
        """Send message and save to database"""
        self.repository.create(db, "user", message)
        result = await self._run_chat_canvas(message)
        self.repository.create(db, "assistant", str(result["answer"]))
        return ChatResponse(
            answer=str(result["answer"]),
            references=list(result["references"]),
            citation_section=list(result.get("citation_section") or []),
            sentence_citations=list(result.get("sentence_citations") or []),
            agent_trace=result.get("agent_trace"),
        )

    async def rag_query(self, message: str) -> ChatResponse:
        """RAG query without saving to database (for localStorage-based chat)"""
        result = await self._run_chat_canvas(message)
        return ChatResponse(
            answer=str(result["answer"]),
            references=list(result["references"]),
            citation_section=list(result.get("citation_section") or []),
            sentence_citations=list(result.get("sentence_citations") or []),
            agent_trace=result.get("agent_trace"),
        )

    async def rag_stream(self, message: str):
        """Streaming RAG query for real-time chat experience"""
        try:
            canvas = self.canvas_factory.create_chat_canvas(query=message, group_id='default')
            agent_output: dict[str, Any] | None = None
            message_output: dict[str, Any] | None = None
            canvas_events: list[dict[str, Any]] = []
            timeline_order = 1
            timeline_emitted = False
            queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

            def runtime_event_sink(event: dict[str, Any]) -> None:
                queue.put_nowait(('runtime', event))

            canvas.set_runtime_event_sink(runtime_event_sink)

            async def produce_canvas_events() -> None:
                async for event in canvas.run():
                    await queue.put(('canvas', event))
                await queue.put(('done', None))

            producer_task = asyncio.create_task(produce_canvas_events())

            while True:
                source, payload = await queue.get()
                if source == 'done':
                    break

                if source == 'runtime':
                    chunk = self._timeline_chunk_from_runtime_event(payload, timeline_order)
                    if chunk:
                        yield chunk
                        timeline_order += 1
                        timeline_emitted = True
                    continue

                event = payload
                if event.node_id:
                    canvas_events.append(
                        {
                            'event': event.event,
                            'node_id': event.node_id,
                            'node_type': getattr(event, 'node_type', None),
                        }
                    )

                for chunk in self._timeline_chunks_from_canvas_event(event, timeline_order):
                    yield chunk
                    timeline_order += 1
                    timeline_emitted = True

                if event.event != 'node_finished':
                    continue
                if event.node_id == 'agent':
                    agent_output = event.payload.get('output') or {}
                elif event.node_id == 'message':
                    message_output = event.payload.get('output') or {}

            await producer_task

            if message_output is None:
                raise RuntimeError('Canvas workflow did not produce a message output')

            if not timeline_emitted:
                yield self._timeline_chunk(
                    event_id='understand-question',
                    kind='understand',
                    title='理解问题',
                    detail='正在理解你的问题。',
                    status='done',
                    order=timeline_order,
                )
                timeline_order += 1

            yield self._timeline_chunk(
                event_id='citation',
                kind='citation',
                title='整理引用与轨迹',
                detail='正在整理引用与可解释轨迹。',
                status='started',
                order=timeline_order,
            )
            timeline_emitted = True
            timeline_order += 1

            citation_result = await self.citation_postprocessor.process(
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
            yield self._timeline_chunk(
                event_id='citation',
                kind='citation',
                title='整理引用与轨迹',
                detail='引用与可解释轨迹已整理完成。',
                status='done',
                order=timeline_order,
            )
            timeline_order += 1
            yield self._timeline_chunk(
                event_id='final-answer',
                kind='answer',
                title='最终回答完成',
                detail='最终回答已生成完成。',
                status='done',
                order=timeline_order,
            )
            result = {
                'answer': citation_result.answer,
                'references': references,
                'citation_section': self._build_citation_section(citation_result),
                'sentence_citations': list(citation_result.sentence_citations),
                'agent_trace': agent_trace,
            }
            for chunk in (
                {'type': 'trace', 'content': result.get('agent_trace')},
                {
                    'type': 'references',
                    'content': [
                        reference.model_dump() if hasattr(reference, 'model_dump') else reference
                        for reference in result['references']
                    ],
                },
                {
                    'type': 'citation_section',
                    'content': list(result.get('citation_section') or []),
                },
                {
                    'type': 'sentence_citations',
                    'content': list(result.get('sentence_citations') or []),
                },
                {'type': 'content', 'content': str(result['answer'])},
                {'type': 'done', 'content': ''},
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Error in streaming RAG: {e}", exc_info=True)
            if isinstance(e, ModelAPIError):
                error_chunk = {
                    "type": "error",
                    "content": e.message,
                    **e.to_dict(),
                }
            else:
                error_chunk = {
                    "type": "error",
                    "content": str(e),
                    "error_code": "UNKNOWN_ERROR",
                    "message": str(e),
                    "details": "",
                    "provider": "",
                    "retryable": False,
                }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

    def list_messages(self, db: Session):
        return self.repository.list(db)

    def clear_messages(self, db: Session) -> None:
        self.repository.clear(db)
