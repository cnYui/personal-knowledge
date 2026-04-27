from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.graph import GraphData
from app.services.graph_visualization_service import GraphVisualizationService


class _FakeNeo4jResult:
    def __init__(self, records):
        self.records = records

    async def data(self):
        return self.records


class _FakeNeo4jSession:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def run(self, query, **params):
        self.calls.append((query, params))
        if 'MATCH (node)' in query:
            return _FakeNeo4jResult(
                [
                    {
                        'node_id': 'entity-1',
                        'node_name': 'Alpha',
                        'node_summary': 'Alpha summary',
                        'node_labels': ['Entity'],
                    },
                    {
                        'node_id': 'episode-1',
                        'node_name': '孤立记忆',
                        'node_summary': None,
                        'node_labels': ['Episodic'],
                    },
                ]
            )

        return _FakeNeo4jResult(
            [
                {
                    'edge_id': 'edge-1',
                    'edge_name': 'RELATED_TO',
                    'edge_fact': 'Alpha relates to Beta',
                    'source_uuid': 'entity-1',
                    'target_uuid': 'entity-2',
                    'source_node_id': 'entity-1',
                    'source_name': 'Alpha',
                    'source_summary': 'Alpha summary',
                    'target_node_id': 'entity-2',
                    'target_name': 'Beta',
                    'target_summary': 'Beta summary',
                }
            ]
        )


class _FakeNeo4jDriver:
    def __init__(self):
        self.session_instance = _FakeNeo4jSession()

    def session(self):
        return self.session_instance


@pytest.mark.anyio
async def test_graph_visualization_service_uses_existing_graphiti_driver_when_available():
    service = GraphVisualizationService()
    service.graphiti_client = SimpleNamespace(
        client=SimpleNamespace(driver='driver'),
    )
    fetch_mock = AsyncMock(return_value=GraphData(nodes=[], edges=[], stats={'total_nodes': 0, 'total_edges': 0}))
    service._fetch_with_graphiti_driver = fetch_mock

    result = await service.get_graph_data(group_id='default', limit=10)

    fetch_mock.assert_awaited_once_with('driver', group_id='default', limit=10)
    assert result.stats == {'total_nodes': 0, 'total_edges': 0}


@pytest.mark.anyio
async def test_fetch_with_direct_driver_includes_isolated_nodes_and_stable_edge_order():
    service = GraphVisualizationService()
    driver = _FakeNeo4jDriver()

    result = await service._fetch_with_direct_driver(driver, group_id='default', limit=1000)

    assert result.stats == {'total_nodes': 3, 'total_edges': 1}
    assert {node.id for node in result.nodes} == {'entity-1', 'entity-2', 'episode-1'}
    assert next(node for node in result.nodes if node.id == 'episode-1').type == 'episode'
    assert result.edges[0].id == 'edge-1'

    node_query, node_params = driver.session_instance.calls[0]
    edge_query, edge_params = driver.session_instance.calls[1]
    assert 'ORDER BY node.created_at DESC, node.uuid ASC' in node_query
    assert 'ORDER BY edge.created_at DESC, edge.uuid ASC' in edge_query
    assert node_params == {'group_id': 'default'}
    assert edge_params == {'group_id': 'default', 'limit': 1000}


@pytest.mark.anyio
async def test_graph_visualization_service_falls_back_to_direct_neo4j_driver_without_graphiti_runtime():
    service = GraphVisualizationService()
    service.graphiti_client = SimpleNamespace(client=None)

    from app.services import graph_visualization_service as graph_module

    original_driver_factory = graph_module.AsyncGraphDatabase.driver
    fetch_direct_mock = AsyncMock(return_value=GraphData(nodes=[], edges=[], stats={'total_nodes': 0, 'total_edges': 0}))
    close_mock = AsyncMock()
    service._fetch_with_direct_driver = fetch_direct_mock

    graph_module.AsyncGraphDatabase.driver = lambda *args, **kwargs: SimpleNamespace(close=close_mock)
    try:
        result = await service.get_graph_data(group_id='default', limit=10)
    finally:
        graph_module.AsyncGraphDatabase.driver = original_driver_factory

    fetch_direct_mock.assert_awaited_once()
    close_mock.assert_awaited_once()
    assert result.stats == {'total_nodes': 0, 'total_edges': 0}
