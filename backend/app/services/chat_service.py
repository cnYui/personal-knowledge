import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.model_errors import ModelAPIError
from app.repositories.chat_repository import ChatRepository
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

    def _thinking_message_from_event(self, event: Any) -> str | None:
        if event.event == 'workflow_started':
            return '已创建工作流，正在整理问题与上下文。'
        if event.event == 'node_started' and event.node_id == 'begin':
            return '正在初始化本轮对话输入。'
        if event.event == 'node_started' and event.node_id == 'agent':
            return 'Agent 已接管本轮会话，正在决定是否调用知识检索工具。'
        if event.event == 'node_started' and event.node_id == 'message':
            return '正在组织最终回答。'
        if event.event == 'workflow_finished':
            return '工作流执行完成，准备返回结果。'
        return None

    def _thinking_messages_from_agent_output(self, agent_output: dict[str, Any] | None) -> list[str]:
        if not agent_output:
            return []

        messages: list[str] = []
        workflow_debug = agent_output.get('workflow_debug') or {}
        tool_steps = workflow_debug.get('tool_steps') or []
        if tool_steps:
            for step in tool_steps:
                round_index = int(step.get('round_index', 0)) + 1
                arguments = step.get('arguments') or {}
                query = str(arguments.get('query') or '').strip()
                result_summary = step.get('result_summary') or {}
                retrieved_edge_count = result_summary.get('retrieved_edge_count')
                has_enough_evidence = result_summary.get('has_enough_evidence')

                message = f'检索第 {round_index} 轮：'
                if query:
                    message += f' 已使用“{query}”查询知识图谱'
                else:
                    message += ' 已发起知识图谱查询'
                if retrieved_edge_count is not None:
                    message += f'，命中 {retrieved_edge_count} 条图谱证据'
                if has_enough_evidence is True:
                    message += '，当前证据已足够。'
                elif has_enough_evidence is False:
                    message += '，当前证据仍不足。'
                else:
                    message += '。'
                messages.append(message)

        trace = agent_output.get('agent_trace')
        if isinstance(trace, dict):
            final_action = str(trace.get('final_action') or '')
        else:
            final_action = getattr(trace, 'final_action', '') if trace is not None else ''
        if final_action == 'direct_general_answer':
            messages.append('本轮问题无需检索，Agent 直接生成回答。')
        elif final_action == 'kb_grounded_answer':
            messages.append('知识库证据充足，正在生成基于证据的回答。')
        elif final_action == 'kb_plus_general_answer':
            messages.append('知识库证据不足，正在补充通用模型回答。')

        return messages

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

    async def send_message(self, db: Session, message: str) -> ChatResponse:
        """Send message and save to database"""
        self.repository.create(db, "user", message)
        result = await self._run_chat_canvas(message)
        self.repository.create(db, "assistant", str(result["answer"]))
        return ChatResponse(
            answer=str(result["answer"]),
            references=list(result["references"]),
            agent_trace=result.get("agent_trace"),
        )

    async def rag_query(self, message: str) -> ChatResponse:
        """RAG query without saving to database (for localStorage-based chat)"""
        result = await self._run_chat_canvas(message)
        return ChatResponse(
            answer=str(result["answer"]),
            references=list(result["references"]),
            agent_trace=result.get("agent_trace"),
        )

    async def rag_stream(self, message: str):
        """Streaming RAG query for real-time chat experience"""
        try:
            canvas = self.canvas_factory.create_chat_canvas(query=message, group_id='default')
            agent_output: dict[str, Any] | None = None
            message_output: dict[str, Any] | None = None
            canvas_events: list[dict[str, Any]] = []
            seen_thinking_messages: set[str] = set()

            async for event in canvas.run():
                if event.node_id:
                    canvas_events.append(
                        {
                            'event': event.event,
                            'node_id': event.node_id,
                            'node_type': getattr(event, 'node_type', None),
                        }
                    )

                thinking_message = self._thinking_message_from_event(event)
                if thinking_message and thinking_message not in seen_thinking_messages:
                    seen_thinking_messages.add(thinking_message)
                    yield f"data: {json.dumps({'type': 'thinking', 'content': thinking_message}, ensure_ascii=False)}\n\n"

                if event.event != 'node_finished':
                    continue
                if event.node_id == 'agent':
                    agent_output = event.payload.get('output') or {}
                    for detail_message in self._thinking_messages_from_agent_output(agent_output):
                        if detail_message in seen_thinking_messages:
                            continue
                        seen_thinking_messages.add(detail_message)
                        yield f"data: {json.dumps({'type': 'thinking', 'content': detail_message}, ensure_ascii=False)}\n\n"
                elif event.node_id == 'message':
                    message_output = event.payload.get('output') or {}

            if message_output is None:
                raise RuntimeError('Canvas workflow did not produce a message output')

            yield f"data: {json.dumps({'type': 'thinking', 'content': '正在整理引用与可解释轨迹。'}, ensure_ascii=False)}\n\n"

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
            result = {
                'answer': citation_result.answer,
                'references': references,
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
