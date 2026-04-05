from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from inspect import isawaitable
from typing import Any

from openai import AsyncOpenAI

from app.core.model_errors import map_model_api_error, missing_api_key_error
from app.services.model_config_service import ModelConfigService, model_config_service
from app.workflow.reference_store import ReferenceStore

FALLBACK_PREFIX = '知识库中未找到充分证据，以下内容为通用模型补充回答。'
logger = logging.getLogger(__name__)


@dataclass
class CitationResult:
    answer: str
    cited_answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    sentence_citations: list[dict[str, Any]] = field(default_factory=list)
    used_general_fallback: bool = False


class CitationPostProcessor:
    def __init__(
        self,
        *,
        fallback_prefix: str = FALLBACK_PREFIX,
        llm_client: AsyncOpenAI | None = None,
        model_config_service_instance: ModelConfigService | None = None,
    ) -> None:
        self.fallback_prefix = fallback_prefix
        self.model_config_service = model_config_service_instance or model_config_service
        self.llm_client = llm_client
        self._managed_llm_client = llm_client is None
        self._dialog_signature: tuple[str, str, str, int] | None = None
        self._dialog_model = 'deepseek-chat'

    def _normalize_snapshot(
        self,
        reference_store: ReferenceStore | dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        if isinstance(reference_store, ReferenceStore):
            snapshot = reference_store.snapshot()
        elif hasattr(reference_store, 'snapshot'):
            snapshot = reference_store.snapshot()
        else:
            snapshot = reference_store
        return {
            'chunks': list(snapshot.get('chunks', [])),
            'doc_aggs': list(snapshot.get('doc_aggs', [])),
            'graph_evidence': list(snapshot.get('graph_evidence', [])),
        }

    def _graph_label(self, evidence: dict[str, Any]) -> str:
        if evidence.get('fact'):
            return str(evidence['fact'])
        if evidence.get('name') and evidence.get('summary'):
            return f"{evidence['name']}：{evidence['summary']}"
        if evidence.get('name'):
            return str(evidence['name'])
        return str(evidence)

    def _doc_label(self, doc: dict[str, Any]) -> str:
        return str(doc.get('doc_name') or doc.get('title') or doc.get('id') or doc)

    def _chunk_label(self, chunk: dict[str, Any]) -> str:
        return str(chunk.get('content') or chunk.get('text') or chunk.get('id') or chunk)

    def _append_citation(
        self,
        citations: list[dict[str, Any]],
        seen_keys: set[str],
        *,
        citation_type: str,
        label: str,
        source: dict[str, Any],
    ) -> None:
        normalized_label = label.strip()
        if not normalized_label:
            return
        if normalized_label in seen_keys:
            return
        seen_keys.add(normalized_label)
        citations.append(
            {
                'index': len(citations) + 1,
                'type': citation_type,
                'label': normalized_label,
                'source': source,
            }
        )

    def _ensure_dialog_client(self) -> None:
        if not self._managed_llm_client:
            return

        config = self.model_config_service.get_dialog_config()
        signature = (
            config.provider,
            config.api_key,
            config.base_url,
            self.model_config_service.version,
        )
        if self.llm_client is not None and signature == self._dialog_signature:
            return

        if not config.api_key:
            raise missing_api_key_error(provider=config.provider, purpose='对话模型')

        self.llm_client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self._dialog_model = config.model
        self._dialog_signature = signature

    def _split_sentences(self, answer: str) -> list[str]:
        parts = re.split(r'(?<=[。！？!?；;])\s*|\n+', str(answer or '').strip())
        return [part.strip() for part in parts if part and part.strip()]

    async def _align_sentence_citations(
        self,
        *,
        answer: str,
        citations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not answer or not citations:
            return []

        sentences = self._split_sentences(answer)
        if not sentences:
            return []

        self._ensure_dialog_client()
        citation_lines = [f'[{citation["index"]}] {citation["label"]}' for citation in citations]
        sentence_lines = [f'{index}. {sentence}' for index, sentence in enumerate(sentences)]
        system_prompt = """你是一个学术引用对齐助手。
任务：判断回答中的每个句子是否能被给定证据明确支持。

要求：
1. 只返回 JSON 数组。
2. 每个元素格式为 {"sentence_index": number, "citation_indexes": number[], "confidence": number}。
3. 只有在句子与证据存在明确语义对应时才返回该句子的引用。
4. 如果句子无法被明确支持，就不要返回该句子。
5. confidence 取 0 到 1 之间的小数。
6. 每个句子最多返回 2 个 citation_indexes。
7. 不要编造不存在的 citation index。
"""
        user_prompt = (
            '【回答句子】\n'
            + '\n'.join(sentence_lines)
            + '\n\n【证据列表】\n'
            + '\n'.join(citation_lines)
            + '\n\n请只给出能明确匹配的句子级引用对齐结果。'
        )
        try:
            response = self.llm_client.chat.completions.create(
                model=self._dialog_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                temperature=0.0,
                max_tokens=800,
                response_format={'type': 'json_object'},
            )
            if isawaitable(response):
                response = await response
            raw_content = str(response.choices[0].message.content or '').strip()
            payload = json.loads(raw_content)
            items = payload.get('items') if isinstance(payload, dict) else payload
            if not isinstance(items, list):
                return []
        except Exception as error:
            provider = self.model_config_service.get_dialog_config().provider
            logger.warning('Sentence citation alignment skipped: %s', map_model_api_error(error, provider=provider))
            return []

        sentence_count = len(sentences)
        valid_indexes = {citation['index'] for citation in citations}
        aligned: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            sentence_index = item.get('sentence_index')
            citation_indexes = item.get('citation_indexes')
            confidence = item.get('confidence', 0)
            if not isinstance(sentence_index, int) or not (0 <= sentence_index < sentence_count):
                continue
            if not isinstance(citation_indexes, list):
                continue
            normalized_indexes = [
                index
                for index in citation_indexes[:2]
                if isinstance(index, int) and index in valid_indexes
            ]
            if not normalized_indexes:
                continue
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                continue
            if confidence_value < 0.8:
                continue
            aligned.append(
                {
                    'sentence_index': sentence_index,
                    'citation_indexes': normalized_indexes,
                }
            )
        return aligned

    async def process(
        self,
        *,
        answer: str,
        reference_store: ReferenceStore | dict[str, Any],
        include_reference_section: bool = True,
    ) -> CitationResult:
        normalized_answer = str(answer or '').strip()
        snapshot = self._normalize_snapshot(reference_store)
        citations: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        for evidence in snapshot['graph_evidence']:
            self._append_citation(
                citations,
                seen_keys,
                citation_type=str(evidence.get('type') or 'graph_evidence'),
                label=self._graph_label(evidence),
                source=evidence,
            )

        for doc in snapshot['doc_aggs']:
            self._append_citation(
                citations,
                seen_keys,
                citation_type='doc',
                label=self._doc_label(doc),
                source=doc,
            )

        for chunk in snapshot['chunks']:
            self._append_citation(
                citations,
                seen_keys,
                citation_type='chunk',
                label=self._chunk_label(chunk),
                source=chunk,
            )

        cited_answer = normalized_answer
        if include_reference_section and citations:
            reference_lines = [f"[{citation['index']}] {citation['label']}" for citation in citations]
            cited_answer = '\n'.join([normalized_answer, '', '参考引用：', *reference_lines]).strip()

        sentence_citations = await self._align_sentence_citations(
            answer=normalized_answer,
            citations=citations,
        )

        return CitationResult(
            answer=normalized_answer,
            cited_answer=cited_answer,
            citations=citations,
            sentence_citations=sentence_citations,
            used_general_fallback=normalized_answer.startswith(self.fallback_prefix),
        )
