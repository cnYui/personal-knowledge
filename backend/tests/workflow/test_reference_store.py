from app.workflow.reference_store import ReferenceStore


def test_reference_store_merges_and_deduplicates_items():
    store = ReferenceStore()

    store.merge(
        chunks=[{'id': 'c1', 'text': 'chunk-1'}, {'id': 'c1', 'text': 'chunk-1'}],
        doc_aggs=[{'doc_name': 'doc-a', 'count': 1}],
        graph_evidence=[{'id': 'g1', 'fact': 'Alice likes tea'}],
    )

    assert store.has_evidence() is True
    snapshot = store.snapshot()
    assert snapshot['chunks'] == [{'id': 'c1', 'text': 'chunk-1'}]
    assert snapshot['doc_aggs'] == [{'doc_name': 'doc-a', 'count': 1}]
    assert snapshot['graph_evidence'] == [{'id': 'g1', 'fact': 'Alice likes tea'}]


def test_reference_store_clear_resets_all_collections():
    store = ReferenceStore()
    store.merge(chunks=[{'id': 'c1', 'text': 'chunk-1'}])

    store.clear()

    assert store.has_evidence() is False
    assert store.snapshot() == {'chunks': [], 'doc_aggs': [], 'graph_evidence': []}
