import json
import logging
from collections.abc import AsyncGenerator
from inspect import isawaitable

from app.schemas.agent import (
    AgentPlanningDecision,
    AgentTrace,
    AgentTraceStep,
    GraphRetrievalResult,
)
from app.services.agent_prompts import (
    CHITCHAT_PREFIXES,
    RETRIEVAL_RETRY_PLANNER_SYSTEM_PROMPT,
    STRICT_AGENT_SYSTEM_PROMPT,
)
from app.services.agent_tools.graph_retrieval_tool import GraphRetrievalTool
from app.services.knowledge_graph_service import KnowledgeGraphService

logger = logging.getLogger(__name__)


class AgentService:
    """Strict-mode agent that only uses graph retrieval for knowledge-grounded answers."""

    def __init__(
        self,
        graph_retrieval_tool: GraphRetrievalTool | None = None,
        knowledge_graph_service: KnowledgeGraphService | None = None,
        max_retrieval_rounds: int = 2,
    ) -> None:
        shared_knowledge_graph_service = knowledge_graph_service or getattr(
            graph_retrieval_tool, 'knowledge_graph_service', None
        )
        if shared_knowledge_graph_service is None and graph_retrieval_tool is None:
            shared_knowledge_graph_service = KnowledgeGraphService()

        self.knowledge_graph_service = shared_knowledge_graph_service
        self.graph_retrieval_tool = graph_retrieval_tool or GraphRetrievalTool(
            knowledge_graph_service=shared_knowledge_graph_service
        )
        self.system_prompt = STRICT_AGENT_SYSTEM_PROMPT
        self.max_retrieval_rounds = max_retrieval_rounds

    def _get_knowledge_graph_service(self) -> KnowledgeGraphService:
        if self.knowledge_graph_service is None:
            self.knowledge_graph_service = KnowledgeGraphService()
        return self.knowledge_graph_service

    def _normalize_query(self, query: str) -> str:
        return query.strip()

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
        rewritten_query: str = '',
        action: str = '',
    ) -> None:
        trace.steps.append(
            AgentTraceStep(
                step_type=step_type,
                query=query,
                message=message,
                evidence_found=evidence_found,
                retrieved_edge_count=retrieved_edge_count,
                rewritten_query=rewritten_query,
                action=action,
            )
        )

    def _strip_json_block(self, content: str) -> str:
        normalized = content.strip()
        if normalized.startswith('```'):
            lines = normalized.splitlines()
            if len(lines) >= 3:
                normalized = '\n'.join(lines[1:-1]).strip()
        return normalized

    async def _complete_json(self, *, system_prompt: str, user_prompt: str) -> str:
        knowledge_graph_service = self._get_knowledge_graph_service()
        response = knowledge_graph_service.llm_client.chat.completions.create(
            model='step-1-8k',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            temperature=0.1,
        )
        if isawaitable(response):
            response = await response
        return str(response.choices[0].message.content or '')

    async def _plan_retry(
        self,
        *,
        original_query: str,
        attempted_query: str,
        retrieval_result: GraphRetrievalResult,
        retrieval_round: int,
    ) -> AgentPlanningDecision:
        if retrieval_round >= self.max_retrieval_rounds:
            return AgentPlanningDecision(
                action='give_up',
                reason='已达到最大检索轮数，不再继续重检索。',
            )

        user_prompt = (
            f'原始用户问题：{original_query}\n'
            f'本轮检索问题：{attempted_query}\n'
            f'当前轮次：{retrieval_round}\n'
            f'命中边数量：{retrieval_result.retrieved_edge_count}\n'
            f'是否有足够证据：{retrieval_result.has_enough_evidence}\n'
            f'空结果原因：{retrieval_result.empty_reason or "无"}\n'
            '请判断是否值得改写问题后再检索一次。'
        )

        try:
            content = await self._complete_json(
                system_prompt=RETRIEVAL_RETRY_PLANNER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            payload = json.loads(self._strip_json_block(content))
            decision = AgentPlanningDecision.model_validate(payload)
        except Exception as exc:
            logger.warning('Retry planner failed, fallback to give_up: %s', exc, exc_info=True)
            return AgentPlanningDecision(
                action='give_up',
                reason='重检索规划失败，采用保守兜底策略。',
            )

        rewritten_query = self._normalize_query(decision.rewritten_query)
        if decision.action == 'rewrite' and rewritten_query and rewritten_query != attempted_query:
            return decision.model_copy(update={'rewritten_query': rewritten_query})

        return AgentPlanningDecision(
            action='give_up',
            reason=decision.reason or '未生成有效的重写问题。',
        )

    async def _resolve_retrieval_result(
        self,
        *,
        query: str,
        group_id: str,
        trace: AgentTrace,
    ) -> GraphRetrievalResult:
        current_query = self._normalize_query(query)
        retrieval_round = 1
        retrieval_result = await self.graph_retrieval_tool.run(current_query, group_id=group_id)
        trace.retrieval_rounds = retrieval_round
        self._append_trace_step(
            trace,
            step_type='retrieval',
            query=current_query,
            message='执行图谱检索',
            evidence_found=retrieval_result.has_enough_evidence,
            retrieved_edge_count=retrieval_result.retrieved_edge_count,
            action='retrieve',
        )
        logger.info(
            'Agent retrieval round=%s query=%s evidence=%s edges=%s',
            retrieval_round,
            current_query,
            retrieval_result.has_enough_evidence,
            retrieval_result.retrieved_edge_count,
        )

        while not retrieval_result.has_enough_evidence and retrieval_round < self.max_retrieval_rounds:
            decision = await self._plan_retry(
                original_query=query,
                attempted_query=current_query,
                retrieval_result=retrieval_result,
                retrieval_round=retrieval_round,
            )
            logger.info(
                'Agent retry decision round=%s action=%s rewritten_query=%s reason=%s',
                retrieval_round,
                decision.action,
                decision.rewritten_query,
                decision.reason,
            )
            self._append_trace_step(
                trace,
                step_type='planner',
                query=current_query,
                message=decision.reason,
                rewritten_query=decision.rewritten_query,
                action=decision.action,
            )
            if decision.action != 'rewrite':
                break

            retrieval_round += 1
            current_query = decision.rewritten_query
            retrieval_result = await self.graph_retrieval_tool.run(current_query, group_id=group_id)
            trace.retrieval_rounds = retrieval_round
            self._append_trace_step(
                trace,
                step_type='retrieval',
                query=current_query,
                message='执行重写后的图谱检索',
                evidence_found=retrieval_result.has_enough_evidence,
                retrieved_edge_count=retrieval_result.retrieved_edge_count,
                action='retrieve',
            )
            logger.info(
                'Agent retrieval round=%s query=%s evidence=%s edges=%s',
                retrieval_round,
                current_query,
                retrieval_result.has_enough_evidence,
                retrieval_result.retrieved_edge_count,
            )

        return retrieval_result

    def is_obvious_chitchat(self, query: str) -> bool:
        normalized_query = self._normalize_query(query).lower()
        return any(normalized_query.startswith(prefix.lower()) for prefix in CHITCHAT_PREFIXES)

    def _build_chitchat_answer(self, query: str) -> str:
        normalized_query = self._normalize_query(query)
        if normalized_query.startswith('早上好'):
            return '早上好！我是你的个人知识库助手，有什么想了解的可以直接问我。'
        if normalized_query.startswith('晚上好'):
            return '晚上好！我是你的个人知识库助手，需要我帮你查点什么吗？'
        return '你好！我是你的个人知识库助手，可以陪你简单聊聊，也可以帮你查询知识图谱里的信息。'

    async def ask(self, query: str, group_id: str = 'default') -> dict:
        try:
            if self.is_obvious_chitchat(query):
                trace = self._new_trace('chitchat')
                trace.final_action = 'chitchat_answer'
                self._append_trace_step(
                    trace,
                    step_type='chitchat',
                    query=query,
                    message='识别为闲聊，直接回答。',
                    action='direct_answer',
                )
                return {
                    'answer': self._build_chitchat_answer(query),
                    'references': [],
                    'agent_trace': trace,
                }

            trace = self._new_trace('graph_rag')
            retrieval_result = await self._resolve_retrieval_result(
                query=query,
                group_id=group_id,
                trace=trace,
            )
            knowledge_graph_service = self._get_knowledge_graph_service()
            trace.final_action = 'answer'
            self._append_trace_step(
                trace,
                step_type='answer',
                query=query,
                message='基于图谱证据生成最终答案。',
                evidence_found=retrieval_result.has_enough_evidence,
                retrieved_edge_count=retrieval_result.retrieved_edge_count,
                action='answer',
            )
            result = await knowledge_graph_service.answer_with_context(query, retrieval_result)
            result['agent_trace'] = trace
            return result
        except Exception as exc:
            logger.error('Error in strict agent ask: %s', exc, exc_info=True)
            return {
                'answer': f'抱歉，处理您的问题时出现错误：{str(exc)}',
                'references': [],
                'agent_trace': None,
            }

    async def ask_stream(self, query: str, group_id: str = 'default') -> AsyncGenerator[dict, None]:
        try:
            if self.is_obvious_chitchat(query):
                trace = self._new_trace('chitchat')
                trace.final_action = 'chitchat_answer'
                self._append_trace_step(
                    trace,
                    step_type='chitchat',
                    query=query,
                    message='识别为闲聊，直接回答。',
                    action='direct_answer',
                )
                yield {'type': 'trace', 'content': trace.model_dump()}
                yield {'type': 'references', 'content': []}
                yield {'type': 'content', 'content': self._build_chitchat_answer(query)}
                yield {'type': 'done', 'content': ''}
                return

            trace = self._new_trace('graph_rag')
            retrieval_result = await self._resolve_retrieval_result(
                query=query,
                group_id=group_id,
                trace=trace,
            )
            trace.final_action = 'answer'
            self._append_trace_step(
                trace,
                step_type='answer',
                query=query,
                message='基于图谱证据生成最终答案。',
                evidence_found=retrieval_result.has_enough_evidence,
                retrieved_edge_count=retrieval_result.retrieved_edge_count,
                action='answer',
            )
            yield {'type': 'trace', 'content': trace.model_dump()}
            yield {
                'type': 'references',
                'content': [reference.model_dump() for reference in retrieval_result.references],
            }

            knowledge_graph_service = self._get_knowledge_graph_service()
            async for chunk in knowledge_graph_service.answer_with_context_stream(
                query, retrieval_result
            ):
                yield chunk
        except Exception as exc:
            logger.error('Error in strict agent stream: %s', exc, exc_info=True)
            yield {'type': 'error', 'content': str(exc)}
