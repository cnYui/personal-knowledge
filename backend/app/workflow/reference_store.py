from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _chunk_key(chunk: dict[str, Any]) -> str:
    return str(chunk.get('id') or chunk.get('chunk_id') or hash(str(sorted(chunk.items()))))


def _doc_key(doc: dict[str, Any]) -> str:
    return str(doc.get('doc_name') or doc.get('id') or hash(str(sorted(doc.items()))))


def _evidence_key(evidence: dict[str, Any]) -> str:
    return str(evidence.get('id') or evidence.get('name') or hash(str(sorted(evidence.items()))))


@dataclass
class ReferenceStore:
    chunks: dict[str, dict[str, Any]] = field(default_factory=dict)
    doc_aggs: dict[str, dict[str, Any]] = field(default_factory=dict)
    graph_evidence: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_chunks(self, chunks: list[dict[str, Any]]) -> None:
        for chunk in chunks:
            self.chunks[_chunk_key(chunk)] = chunk

    def add_doc_aggs(self, doc_aggs: list[dict[str, Any]]) -> None:
        for doc in doc_aggs:
            self.doc_aggs[_doc_key(doc)] = doc

    def add_graph_evidence(self, evidence: list[dict[str, Any]]) -> None:
        for item in evidence:
            self.graph_evidence[_evidence_key(item)] = item

    def merge(
        self,
        *,
        chunks: list[dict[str, Any]] | None = None,
        doc_aggs: list[dict[str, Any]] | None = None,
        graph_evidence: list[dict[str, Any]] | None = None,
    ) -> None:
        if chunks:
            self.add_chunks(chunks)
        if doc_aggs:
            self.add_doc_aggs(doc_aggs)
        if graph_evidence:
            self.add_graph_evidence(graph_evidence)

    def has_evidence(self) -> bool:
        return bool(self.chunks or self.doc_aggs or self.graph_evidence)

    def clear(self) -> None:
        self.chunks.clear()
        self.doc_aggs.clear()
        self.graph_evidence.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            'chunks': list(self.chunks.values()),
            'doc_aggs': list(self.doc_aggs.values()),
            'graph_evidence': list(self.graph_evidence.values()),
        }
