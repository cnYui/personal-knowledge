import pytest

from app.schemas.agent import GraphRetrievalResult
from app.schemas.chat import ChatReference
from app.workflow.canvas import Canvas
from app.workflow.dsl import WorkflowDSL, WorkflowNodeSpec
from app.workflow.nodes.retrieval_node import RetrievalNode
from app.workflow.runtime_context import RuntimeContext


class StubKnowledgeGraphService:
    async def retrieve_graph_context(self, query: str, group_id: str = 'default'):
        return GraphRetrievalResult(
            context='关系: Alice likes green tea',
            references=[ChatReference(type='relationship', fact='Alice likes green tea')],
            has_enough_evidence=True,
            retrieved_edge_count=1,
            group_id=group_id,
        )


@pytest.mark.anyio
async def test_retrieval_node_writes_result_to_reference_store():
    spec = WorkflowNodeSpec(id='retrieval', type='retrieval', config={'query_ref': 'sys.query'})
    node = RetrievalNode(spec, knowledge_graph_service=StubKnowledgeGraphService())
    context = RuntimeContext(query='Alice 喜欢什么？')
    canvas = Canvas(
        WorkflowDSL(entry_node_id='retrieval', nodes=[spec]),
        context=context,
    )

    result = await node.execute(context, canvas)

    assert result.has_enough_evidence is True
    assert context.get_global('retrieval.result').context == '关系: Alice likes green tea'
    snapshot = canvas.reference_store.snapshot()
    assert snapshot['graph_evidence'] == [{'type': 'relationship', 'name': None, 'summary': None, 'fact': 'Alice likes green tea'}]
    assert snapshot['chunks'][0]['content'] == 'Alice likes green tea'
