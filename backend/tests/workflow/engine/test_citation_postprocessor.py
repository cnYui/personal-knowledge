from app.workflow.engine.citation_postprocessor import CitationPostProcessor
from app.workflow.reference_store import ReferenceStore


def test_citation_postprocessor_reads_merged_reference_store_and_renders_citations():
    reference_store = ReferenceStore()
    reference_store.merge(
        graph_evidence=[
            {'type': 'relationship', 'fact': 'Alice likes green tea', 'name': None, 'summary': None},
            {'type': 'entity', 'name': 'Alice', 'summary': '喜欢喝茶', 'fact': None},
        ],
        chunks=[
            {'id': 'chunk-1', 'content': 'Alice likes green tea'},
            {'id': 'chunk-2', 'content': 'Alice usually orders green tea after lunch'},
        ],
    )

    result = CitationPostProcessor().process(
        answer='Alice 喜欢绿茶。',
        reference_store=reference_store,
    )

    assert result.answer == 'Alice 喜欢绿茶。'
    assert result.used_general_fallback is False
    assert [citation['label'] for citation in result.citations] == [
        'Alice likes green tea',
        'Alice：喜欢喝茶',
        'Alice usually orders green tea after lunch',
    ]
    assert '参考引用：' in result.cited_answer
    assert '[1] Alice likes green tea' in result.cited_answer
    assert '[3] Alice usually orders green tea after lunch' in result.cited_answer


def test_citation_postprocessor_marks_general_fallback_but_only_uses_real_evidence():
    reference_store = ReferenceStore()
    reference_store.merge(
        graph_evidence=[
            {'type': 'relationship', 'fact': '星期一收集不可燃垃圾', 'name': None, 'summary': None},
        ]
    )
    answer = '知识库中未找到充分证据，以下内容为通用模型补充回答。\n\n从一般垃圾分类规则来看，星期一通常会安排某一类垃圾收运。'

    result = CitationPostProcessor().process(
        answer=answer,
        reference_store=reference_store,
    )

    assert result.used_general_fallback is True
    assert len(result.citations) == 1
    assert result.citations[0]['label'] == '星期一收集不可燃垃圾'
    assert result.cited_answer.startswith('知识库中未找到充分证据')
    assert '从一般垃圾分类规则来看' in result.cited_answer
