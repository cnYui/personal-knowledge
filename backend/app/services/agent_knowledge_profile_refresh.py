from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from dataclasses import dataclass
from inspect import isawaitable
import re
from typing import Any

from graphiti_core.edges import EntityEdge
from graphiti_core.errors import GroupsEdgesNotFoundError
from graphiti_core.nodes import EntityNode
from openai import AsyncOpenAI

from app.core.database import SessionLocal
from app.models.agent_knowledge_profile import AgentKnowledgeProfile
from app.repositories.agent_knowledge_profile_repository import AgentKnowledgeProfileRepository
from app.repositories.memory_repository import MemoryRepository
from app.services.graphiti_client import GraphitiClient
from app.services.model_client_runtime import ModelRuntimeGateway, model_runtime_gateway
from app.services.model_config_service import ModelConfigService, model_config_service

logger = logging.getLogger(__name__)

PROFILE_TYPE = 'global_agent_overlay'
REFRESH_DEBOUNCE_SECONDS = 10
RECENT_MEMORY_LIMIT = 50
MAX_GRAPH_EDGE_SAMPLE = 200

PROFILE_GENERATION_SYSTEM_PROMPT = """你是知识图谱画像整理助手。
你会收到一份来自知识图谱和最近记忆写入的候选摘要。请将其压缩为结构化 JSON。

输出要求：
1. 只输出 JSON。
2. JSON 必须包含：
   - major_topics
   - high_frequency_entities
   - high_frequency_relations
   - recent_focuses
3. 每个字段值都必须是中文字符串数组。
4. 每个数组控制在 3 到 8 项之间。
5. 只总结真实可见的知识范围，不要编造图谱里没有的信息。
6. major_topics 必须是更高层的主题，不要直接照抄实体名、关系枚举名或英文常量。
7. high_frequency_relations 需要尽量转成用户可理解的中文关系描述，不要保留全大写下划线枚举。
8. recent_focuses 应该是近期新增知识的“关注点”短语，不要直接原样抄整段标题。
9. 如果候选中存在明显噪声或关系枚举，请忽略它们。
"""


@dataclass
class ProfileCandidateSummary:
    top_entities: list[str]
    top_relations: list[str]
    recent_entities: list[str]
    recent_titles: list[str]


class AgentKnowledgeProfileRefreshService:
    def __init__(
        self,
        *,
        repository: AgentKnowledgeProfileRepository | None = None,
        memory_repository: MemoryRepository | None = None,
        graphiti_client: GraphitiClient | None = None,
        model_config_service_instance: ModelConfigService | None = None,
        model_runtime_gateway_instance: ModelRuntimeGateway | None = None,
        llm_client: AsyncOpenAI | None = None,
        session_factory=SessionLocal,
    ) -> None:
        self.repository = repository or AgentKnowledgeProfileRepository()
        self.memory_repository = memory_repository or MemoryRepository()
        self.graphiti_client = graphiti_client or GraphitiClient(
            model_config_service_instance=model_config_service_instance or model_config_service
        )
        self.model_config_service = model_config_service_instance or model_config_service
        self.model_runtime_gateway = model_runtime_gateway_instance or (
            ModelRuntimeGateway(model_config_service_instance=self.model_config_service)
            if model_config_service_instance is not None
            else model_runtime_gateway
        )
        self.llm_client = llm_client
        self.session_factory = session_factory
        self._managed_llm_client = llm_client is None
        self._dialog_signature: tuple[str, str, str, str, str, str, int] | None = None
        self._dialog_model = 'deepseek-chat'
        self._dialog_reasoning_effort = ''
        self._dialog_completion_extra: dict[str, str] = {}

    def _ensure_dialog_client(self) -> None:
        if not self._managed_llm_client:
            return
        runtime = self.model_runtime_gateway.get_runtime('dialog')
        if self.llm_client is not None and runtime.signature == self._dialog_signature:
            return
        self.llm_client = runtime.client
        self._dialog_model = runtime.model
        self._dialog_reasoning_effort = runtime.reasoning_effort
        self._dialog_completion_extra = runtime.completion_extra()
        self._dialog_signature = runtime.signature

    def _tokenize(self, text: str) -> list[str]:
        normalized = re.sub(r'[^\w\u4e00-\u9fff]+', ' ', str(text or ' '))
        pieces = [piece.strip() for piece in normalized.split() if piece.strip()]
        filtered: list[str] = []
        stop_words = {'的', '了', '和', '与', '并', '及', '是', '在', '将', '到', '对', '中', '后', '前'}
        for piece in pieces:
            if len(piece) <= 1:
                continue
            if piece in stop_words:
                continue
            filtered.append(piece)
        return filtered

    def _normalize_relation_label(self, value: str) -> str:
        text = str(value or '').strip()
        if not text:
            return ''
        if re.fullmatch(r'[A-Z_]{3,}', text):
            text = text.replace('_', ' ').lower()
        return text

    def _normalize_title(self, value: str) -> str:
        text = str(value or '').strip()
        text = text.strip('《》"“”')
        return re.sub(r'\s+', ' ', text)

    def _dedupe_preserve_order(self, values: list[str], *, limit: int = 8) -> list[str]:
        seen: set[str] = set()
        normalized_values: list[str] = []
        for value in values:
            key = str(value or '').strip()
            if not key:
                continue
            lowered = key.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized_values.append(key)
            if len(normalized_values) >= limit:
                break
        return normalized_values

    async def _extract_candidates(self) -> ProfileCandidateSummary:
        db = self.session_factory()
        try:
            recent_memories = self.memory_repository.list_recent_graph_added(db, limit=RECENT_MEMORY_LIMIT)
        finally:
            db.close()

        graph_group_ids = self._dedupe_preserve_order(
            [str(getattr(memory, 'group_id', '') or '').strip() for memory in recent_memories],
            limit=RECENT_MEMORY_LIMIT,
        ) or ['default']

        recent_titles = [memory.title for memory in recent_memories if getattr(memory, 'title', None)]
        recent_entities_counter: Counter[str] = Counter()
        for memory in recent_memories:
            recent_entities_counter.update(self._tokenize(memory.title))
            recent_entities_counter.update(self._tokenize(memory.content)[:20])

        top_entities_counter: Counter[str] = Counter()
        top_relations_counter: Counter[str] = Counter()

        try:
            await self.graphiti_client._ensure_runtime_client()
            client = self.graphiti_client.client
            if client is not None:
                driver = client.driver
                edges = await EntityEdge.get_by_group_ids(driver, graph_group_ids, limit=MAX_GRAPH_EDGE_SAMPLE)
                node_uuids = {
                    uuid
                    for edge in edges
                    for uuid in [getattr(edge, 'source_node_uuid', None), getattr(edge, 'target_node_uuid', None)]
                    if uuid
                }
                nodes = await EntityNode.get_by_uuids(driver, list(node_uuids)) if node_uuids else []
                for node in nodes:
                    name = getattr(node, 'name', None)
                    if name:
                        top_entities_counter[str(name)] += 1
                for edge in edges:
                    relation = getattr(edge, 'name', None) or getattr(edge, 'fact', None)
                    if relation:
                        top_relations_counter[str(relation)] += 1
        except GroupsEdgesNotFoundError:
            logger.debug(
                'No graph edges found for knowledge profile refresh group_ids=%s; falling back to memory-only data.',
                graph_group_ids,
            )
        except Exception:
            logger.warning('Failed to extract graph candidates for knowledge profile; falling back to memory-only data.', exc_info=True)

        if not top_entities_counter:
            top_entities_counter.update(recent_entities_counter)

        top_entities = self._dedupe_preserve_order(
            [str(item).strip() for item, _ in top_entities_counter.most_common(16)],
            limit=8,
        )
        top_relations = self._dedupe_preserve_order(
            [self._normalize_relation_label(str(item)) for item, _ in top_relations_counter.most_common(16)],
            limit=8,
        )
        recent_entities = self._dedupe_preserve_order(
            [str(item).strip() for item, _ in recent_entities_counter.most_common(16)],
            limit=8,
        )

        return ProfileCandidateSummary(
            top_entities=top_entities,
            top_relations=top_relations,
            recent_entities=recent_entities,
            recent_titles=self._dedupe_preserve_order(
                [self._normalize_title(title) for title in recent_titles],
                limit=10,
            ),
        )

    async def _compress_profile(self, candidates: ProfileCandidateSummary) -> dict[str, list[str]]:
        payload = {
            'top_entities': candidates.top_entities,
            'top_relations': candidates.top_relations,
            'recent_entities': candidates.recent_entities,
            'recent_titles': candidates.recent_titles,
        }
        self._ensure_dialog_client()
        try:
            response = self.llm_client.chat.completions.create(
                model=self._dialog_model,
                messages=[
                    {'role': 'system', 'content': PROFILE_GENERATION_SYSTEM_PROMPT},
                    {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
                ],
                temperature=0.2,
                response_format={'type': 'json_object'},
                **self._dialog_completion_extra,
            )
            if isawaitable(response):
                response = await response
        except Exception as error:
            raise self.model_runtime_gateway.get_runtime('dialog').map_error(error) from error

        content = str(response.choices[0].message.content or '').strip()
        data = json.loads(content)
        normalized: dict[str, list[str]] = {}
        for key in (
            'major_topics',
            'high_frequency_entities',
            'high_frequency_relations',
            'recent_focuses',
        ):
            raw_values = data.get(key) if isinstance(data, dict) else None
            values = [str(value).strip() for value in (raw_values or []) if str(value).strip()]
            normalized[key] = values[:8]
        return normalized

    def _render_overlay(self, profile: dict[str, list[str]]) -> str:
        sections = [
            '当前知识图谱知识画像（自动生成）：',
            f"- 主要主题：{'、'.join(profile['major_topics']) or '暂无明显主题'}",
            f"- 高频实体：{'、'.join(profile['high_frequency_entities']) or '暂无高频实体'}",
            f"- 高频关系：{'、'.join(profile['high_frequency_relations']) or '暂无高频关系'}",
            f"- 最近新增知识重点：{'、'.join(profile['recent_focuses']) or '暂无明显新增重点'}",
            '当用户问题与这些内容相关时，优先考虑调用 graph_retrieval_tool。',
        ]
        return '\n'.join(sections)

    async def refresh_global_profile(self) -> None:
        db = self.session_factory()
        profile = self.repository.create_building_profile(db, profile_type=PROFILE_TYPE)
        db.close()

        try:
            candidates = await self._extract_candidates()
            profile_data = await self._compress_profile(candidates)
            rendered_overlay = self._render_overlay(profile_data)

            db = self.session_factory()
            try:
                target = db.get(AgentKnowledgeProfile, profile.id)
                if target is None:
                    raise RuntimeError('Knowledge profile record disappeared before ready update.')
                self.repository.mark_profile_ready(
                    db,
                    target,
                    major_topics=profile_data['major_topics'],
                    high_frequency_entities=profile_data['high_frequency_entities'],
                    high_frequency_relations=profile_data['high_frequency_relations'],
                    recent_focuses=profile_data['recent_focuses'],
                    rendered_overlay=rendered_overlay,
                )
            finally:
                db.close()
            logger.info('Agent knowledge profile refresh completed successfully.')
        except Exception as error:
            logger.error('Agent knowledge profile refresh failed: %s', error, exc_info=True)
            db = self.session_factory()
            try:
                target = db.get(AgentKnowledgeProfile, profile.id)
                if target is not None:
                    self.repository.mark_profile_failed(db, target, error_message=str(error))
            finally:
                db.close()


class AgentKnowledgeProfileRefreshScheduler:
    def __init__(
        self,
        *,
        refresh_service: AgentKnowledgeProfileRefreshService | None = None,
        debounce_seconds: int = REFRESH_DEBOUNCE_SECONDS,
    ) -> None:
        self.refresh_service = refresh_service or AgentKnowledgeProfileRefreshService()
        self.debounce_seconds = debounce_seconds
        self._task: asyncio.Task[None] | None = None
        self._refresh_running = False
        self._rerun_requested = False

    def request_refresh(self, *, reason: str = 'graph_ingest_success') -> None:
        logger.info('Knowledge profile refresh requested: reason=%s', reason)
        if self._refresh_running:
            self._rerun_requested = True
            return
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(self._debounced_refresh())

    async def _debounced_refresh(self) -> None:
        try:
            await asyncio.sleep(self.debounce_seconds)
            self._refresh_running = True
            await self.refresh_service.refresh_global_profile()
        except asyncio.CancelledError:
            logger.debug('Knowledge profile refresh debounce task cancelled before execution.')
            raise
        finally:
            was_rerun_requested = self._rerun_requested
            self._refresh_running = False
            self._rerun_requested = False
            if was_rerun_requested:
                self.request_refresh(reason='rerun_after_active_refresh')


agent_knowledge_profile_refresh_scheduler = AgentKnowledgeProfileRefreshScheduler()
