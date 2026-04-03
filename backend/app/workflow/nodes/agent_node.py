from __future__ import annotations

import logging
from inspect import isawaitable
from typing import Any

from app.schemas.agent import AgentTrace, AgentTraceStep, GraphRetrievalResult
from app.services.agent_prompts import (
    GENERAL_FALLBACK_SYSTEM_PROMPT,
    STRICT_AGENT_SYSTEM_PROMPT,
)
from app.services.agent_knowledge_profile_service import (
    AgentKnowledgeProfileService,
    agent_knowledge_profile_service,
)
from app.services.agent_tools.graph_retrieval_tool import GraphRetrievalTool
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.workflow.engine.tool_loop import ToolLoopEngine
from app.workflow.nodes.base import WorkflowNode

logger = logging.getLogger(__name__)

FOCUS_EXTRACTION_SYSTEM_PROMPT = """你是一个问题理解助手。
请将用户问题提炼为 2 到 4 个简短的中文检索重点短语。
要求：
1. 只返回短语本身。
2. 使用 " / " 分隔。
3. 不要输出序号、解释或其他文字。
"""


class _CanvasGraphRetrievalTool:
    name = GraphRetrievalTool.name
    description = GraphRetrievalTool.description

    def __init__(
        self,
        *,
        graph_retrieval_tool: GraphRetrievalTool,
        canvas,
        node_id: str,
        group_id: str,
    ) -> None:
        self.graph_retrieval_tool = graph_retrieval_tool
        self.canvas = canvas
        self.node_id = node_id
        self.group_id = group_id
        self.results: list[GraphRetrievalResult] = []

    @property
    def last_result(self) -> GraphRetrievalResult | None:
        return self.results[-1] if self.results else None

    def _write_reference_store(self, result: GraphRetrievalResult) -> None:
        self.canvas.reference_store.merge(
            chunks=[
                {
                    'id': f'{self.node_id}-chunk-{len(self.results)}-{index}',
                    'content': reference.fact or reference.summary or reference.name or reference.type,
                }
                for index, reference in enumerate(result.references)
            ],
            graph_evidence=[reference.model_dump() for reference in result.references],
        )

    async def run(self, query: str) -> dict[str, Any]:
        result = await self.graph_retrieval_tool.run(query, group_id=self.group_id)
        self.results.append(result)
        self._write_reference_store(result)
        return {
            'context': result.context,
            'references': [reference.model_dump() for reference in result.references],
            'has_enough_evidence': result.has_enough_evidence,
            'empty_reason': result.empty_reason,
            'retrieved_edge_count': result.retrieved_edge_count,
            'group_id': result.group_id,
        }


class AgentNode(WorkflowNode):
    node_type = 'agent'

    def __init__(
        self,
        spec,
        *,
        tool_loop_engine: ToolLoopEngine | None = None,
        knowledge_graph_service: KnowledgeGraphService | None = None,
        graph_retrieval_tool: GraphRetrievalTool | None = None,
        llm_client: Any | None = None,
        knowledge_profile_service: AgentKnowledgeProfileService | None = None,
    ) -> None:
        super().__init__(spec)
        shared_knowledge_graph_service = knowledge_graph_service or getattr(
            graph_retrieval_tool, 'knowledge_graph_service', None
        )
        self.knowledge_graph_service = shared_knowledge_graph_service
        self.graph_retrieval_tool = graph_retrieval_tool
        self.llm_client = llm_client or getattr(shared_knowledge_graph_service, 'llm_client', None)
        self.knowledge_profile_service = knowledge_profile_service or agent_knowledge_profile_service
        self.tool_loop_engine = tool_loop_engine
        self.max_rounds = int(self.config.get('max_rounds', 2))
        self.model = self.config.get('model')

    def _normalize_query(self, query: str) -> str:
        return str(query or '').strip()

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

    def _get_llm_client(self) -> Any:
        if self.llm_client is None:
            if self.tool_loop_engine is not None and getattr(self.tool_loop_engine, 'llm_client', None) is not None:
                self.llm_client = self.tool_loop_engine.llm_client
                return self.llm_client
            knowledge_graph_service = self._get_knowledge_graph_service()
            if hasattr(knowledge_graph_service, '_ensure_dialog_client'):
                knowledge_graph_service._ensure_dialog_client()
            self.llm_client = knowledge_graph_service.llm_client
        return self.llm_client

    def _get_tool_loop_engine(self) -> ToolLoopEngine:
        if self.tool_loop_engine is None:
            self.tool_loop_engine = ToolLoopEngine(
                self._get_llm_client(),
                max_rounds=self.max_rounds,
                model=self._get_model_name(),
            )
        elif not getattr(self.tool_loop_engine, 'model', None):
            self.tool_loop_engine.model = self._get_model_name()
        return self.tool_loop_engine

    def _get_model_name(self) -> str:
        if self.model:
            return str(self.model)

        if self.tool_loop_engine is not None and getattr(self.tool_loop_engine, 'model', None):
            self.model = str(self.tool_loop_engine.model)
            return self.model

        if self.llm_client is not None:
            self.model = 'deepseek-chat'
            return self.model

        knowledge_graph_service = self._get_knowledge_graph_service()
        if hasattr(knowledge_graph_service, '_ensure_dialog_client'):
            knowledge_graph_service._ensure_dialog_client()
        model_name = getattr(knowledge_graph_service, '_dialog_model', None)
        if model_name:
            self.model = str(model_name)
            return self.model

        self.model = 'deepseek-chat'
        return self.model

    def _new_trace(self, mode: str) -> AgentTrace:
        return AgentTrace(mode=mode, final_action='')

    def _append_trace_step(
        self,
        trace: AgentTrace,
        *,
        step_type: str,
        query: str = '',
        message: str = '',
        evidence_found: bool | None = None,
        retrieved_edge_count: int | None = None,
        action: str = '',
    ) -> None:
        trace.steps.append(
            AgentTraceStep(
                step_type=step_type,
                query=query,
                message=message,
                evidence_found=evidence_found,
                retrieved_edge_count=retrieved_edge_count,
                action=action,
            )
        )

    def _tool_schema(self) -> dict[str, Any]:
        return {
            'type': 'function',
            'function': {
                'name': GraphRetrievalTool.name,
                'description': GraphRetrievalTool.description,
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'query': {
                            'type': 'string',
                            'description': 'The search query used to retrieve evidence from the knowledge graph.',
                        }
                    },
                    'required': ['query'],
                },
            },
        }

    def _build_messages(self, context, query: str) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for item in context.history:
            if not isinstance(item, dict):
                continue
            if 'role' in item and 'content' in item:
                history.append({'role': item['role'], 'content': item['content']})

        if not history or history[-1].get('role') != 'user' or history[-1].get('content') != query:
            history.append({'role': 'user', 'content': query})
        return history

    async def _complete_text(self, *, system_prompt: str, user_prompt: str) -> str:
        response = self._get_llm_client().chat.completions.create(
            model=self._get_model_name(),
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            temperature=0.3,
        )
        if isawaitable(response):
            response = await response
        return str(response.choices[0].message.content or '')

    def _combine_retrieval_results(self, results: list[GraphRetrievalResult]) -> GraphRetrievalResult:
        if not results:
            return GraphRetrievalResult(
                context='',
                references=[],
                has_enough_evidence=False,
                empty_reason='图谱中没有足够信息',
                retrieved_edge_count=0,
                group_id='default',
            )

        merged_context_parts: list[str] = []
        merged_references: list[Any] = []
        seen_reference_keys: set[tuple[Any, ...]] = set()
        total_edges = 0
        group_id = results[0].group_id
        has_enough_evidence = False
        empty_reason = '图谱中没有足够信息'

        for result in results:
            total_edges += result.retrieved_edge_count
            has_enough_evidence = has_enough_evidence or result.has_enough_evidence
            if result.empty_reason:
                empty_reason = result.empty_reason
            if result.context.strip():
                merged_context_parts.append(result.context.strip())
            for reference in result.references:
                key = (reference.type, reference.name, reference.summary, reference.fact)
                if key in seen_reference_keys:
                    continue
                seen_reference_keys.add(key)
                merged_references.append(reference)

        return GraphRetrievalResult(
            context='\n\n'.join(merged_context_parts),
            references=merged_references,
            has_enough_evidence=has_enough_evidence,
            empty_reason='' if has_enough_evidence else empty_reason,
            retrieved_edge_count=total_edges,
            group_id=group_id,
        )

    async def _answer_with_general_model(
        self,
        query: str,
        retrieval_result: GraphRetrievalResult | None,
    ) -> str:
        context_hint = retrieval_result.context.strip() if retrieval_result else ''
        user_prompt = query
        if context_hint:
            user_prompt = (
                f'【用户问题】\n{query}\n\n'
                f'【知识库已有但不足的上下文】\n{context_hint}\n\n'
                '请在知识库证据不足的前提下，给出通用模型补充回答。'
            )
        return await self._complete_text(
            system_prompt=GENERAL_FALLBACK_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

    async def _extract_focus_points(self, query: str) -> str:
        if not query:
            return ''
        try:
            summary = await self._complete_text(
                system_prompt=FOCUS_EXTRACTION_SYSTEM_PROMPT,
                user_prompt=query,
            )
            normalized = str(summary or '').strip().replace('\n', ' ')
            return normalized or query
        except Exception:
            logger.debug('Failed to extract focus points, falling back to raw query.', exc_info=True)
            return query

    def _result_payload(self, *, answer: str, references: list[Any], trace: AgentTrace) -> dict[str, Any]:
        return {
            'answer': answer,
            'references': references,
            'agent_trace': trace,
        }

    async def execute(self, context, canvas):
        query_ref = self.config.get('query_ref', 'sys.query')
        group_id = self.config.get('group_id', 'default')
        output_key = self.config.get('output_key', f'{self.node_id}.result')
        base_system_prompt = self.config.get('system_prompt', STRICT_AGENT_SYSTEM_PROMPT)
        system_prompt = self.knowledge_profile_service.compose_system_prompt(base_system_prompt)
        query = self.resolve_reference(query_ref, context) if isinstance(query_ref, str) else query_ref
        query = self._normalize_query(str(query or ''))

        trace = self._new_trace('graph_rag')

        graph_tool = _CanvasGraphRetrievalTool(
            graph_retrieval_tool=self._get_graph_retrieval_tool(),
            canvas=canvas,
            node_id=self.node_id,
            group_id=group_id,
        )

        def emit_timeline(event: dict[str, Any]) -> None:
            canvas.emit_runtime_event(event)

        focus_points = await self._extract_focus_points(query)
        emit_timeline(
            {
                'type': 'timeline',
                'id': 'understand-question',
                'kind': 'understand',
                'title': '理解问题',
                'detail': f'已提炼检索重点：{focus_points}',
                'status': 'done',
            }
        )

        tool_loop_result = await self._get_tool_loop_engine().run(
            messages=self._build_messages(context, query),
            tool_schemas=[self._tool_schema()],
            tool_registry={graph_tool.name: graph_tool},
            system_prompt=system_prompt,
            completion_kwargs={'temperature': float(self.config.get('temperature', 0.2))},
            event_callback=emit_timeline,
        )

        for step in tool_loop_result.steps:
            retrieved_edge_count = None
            evidence_found = None
            if isinstance(step.result, dict):
                retrieved_edge_count = step.result.get('retrieved_edge_count')
                evidence_found = step.result.get('has_enough_evidence')
            self._append_trace_step(
                trace,
                step_type='retrieval',
                query=str(step.arguments.get('query', '')),
                message='执行图谱检索' if not step.error else f'图谱检索失败：{step.error}',
                evidence_found=evidence_found,
                retrieved_edge_count=retrieved_edge_count,
                action='retrieve' if not step.error else 'retrieve_error',
            )
        trace.retrieval_rounds = len([step for step in tool_loop_result.steps if step.tool_name == graph_tool.name])

        workflow_debug = {
            'forced_retrieval': False,
            'tool_rounds_exceeded': tool_loop_result.exceeded_max_rounds,
            'tool_steps': [
                {
                    'round_index': step.round_index,
                    'tool_name': step.tool_name,
                    'arguments': step.arguments,
                    'error': step.error,
                    'has_result': step.result is not None,
                    'result_summary': {
                        'has_enough_evidence': step.result.get('has_enough_evidence'),
                        'retrieved_edge_count': step.result.get('retrieved_edge_count'),
                        'empty_reason': step.result.get('empty_reason'),
                    }
                    if isinstance(step.result, dict)
                    else None,
                }
                for step in tool_loop_result.steps
            ],
        }

        retrieval_result = self._combine_retrieval_results(graph_tool.results)

        if not tool_loop_result.steps:
            emit_timeline(
                {
                    'type': 'timeline',
                    'id': 'final-answer',
                    'kind': 'answer',
                    'title': '直接回答',
                    'detail': '本轮问题无需检索，Agent 直接生成回答。',
                    'status': 'started',
                }
            )
            answer = tool_loop_result.answer.strip()
            if not answer:
                answer = await self._answer_with_general_model(query, None)
            trace.final_action = 'direct_general_answer'
            self._append_trace_step(
                trace,
                step_type='answer',
                query=query,
                message='Agent 判断无需检索，直接生成最终答案。',
                action='answer_directly',
            )
            result = self._result_payload(answer=answer, references=[], trace=trace)
            result['workflow_debug'] = workflow_debug
            context.set_global(output_key, result)
            return result

        if retrieval_result.has_enough_evidence:
            emit_timeline(
                {
                    'type': 'timeline',
                    'id': 'final-answer',
                    'kind': 'answer',
                    'title': '组织最终回答',
                    'detail': 'Agent 已停止继续检索，正在基于当前证据生成最终回答。',
                    'status': 'started',
                }
            )
            answer = tool_loop_result.answer.strip()
            if not answer:
                knowledge_result = await self._get_knowledge_graph_service().answer_with_context(
                    query,
                    retrieval_result,
                )
                answer = str(knowledge_result.get('answer') or '').strip()

            trace.final_action = 'kb_grounded_answer'
            self._append_trace_step(
                trace,
                step_type='answer',
                query=query,
                message='基于知识库证据生成最终答案。',
                evidence_found=True,
                retrieved_edge_count=retrieval_result.retrieved_edge_count,
                action='answer_from_kb',
            )
            result = self._result_payload(
                answer=answer,
                references=retrieval_result.references,
                trace=trace,
            )
            result['workflow_debug'] = workflow_debug
            context.set_global(output_key, result)
            return result

        emit_timeline(
            {
                'type': 'timeline',
                'id': 'final-answer',
                'kind': 'answer',
                'title': '补充通用回答',
                'detail': '知识库证据不足，正在补充通用模型回答并保留已有引用。',
                'status': 'started',
            }
        )
        fallback_answer = tool_loop_result.answer.strip()
        if not fallback_answer:
            fallback_answer = await self._answer_with_general_model(query, retrieval_result)
        fallback_prefix = '知识库中未找到充分证据，以下内容为通用模型补充回答。'
        if not fallback_answer.startswith(fallback_prefix):
            fallback_answer = f'{fallback_prefix}\n\n{fallback_answer}'

        trace.final_action = 'kb_plus_general_answer'
        self._append_trace_step(
            trace,
            step_type='fallback',
            query=query,
            message='知识库证据不足，切换到通用大模型补充回答。',
            evidence_found=False,
            retrieved_edge_count=retrieval_result.retrieved_edge_count if retrieval_result else 0,
            action='fallback_to_general_llm',
        )
        result = self._result_payload(
            answer=fallback_answer,
            references=retrieval_result.references if retrieval_result else [],
            trace=trace,
        )
        result['workflow_debug'] = workflow_debug
        context.set_global(output_key, result)
        return result
