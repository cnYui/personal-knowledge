from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.workflow.reference_store import ReferenceStore

FALLBACK_PREFIX = '知识库中未找到充分证据，以下内容为通用模型补充回答。'


@dataclass
class CitationResult:
    answer: str
    cited_answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    used_general_fallback: bool = False


class CitationPostProcessor:
    def __init__(self, *, fallback_prefix: str = FALLBACK_PREFIX) -> None:
        self.fallback_prefix = fallback_prefix

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

    def process(
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

        return CitationResult(
            answer=normalized_answer,
            cited_answer=cited_answer,
            citations=citations,
            used_general_fallback=normalized_answer.startswith(self.fallback_prefix),
        )
