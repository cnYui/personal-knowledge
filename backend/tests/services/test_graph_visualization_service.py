from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.graph import GraphData
from app.services.graph_visualization_service import GraphVisualizationService


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
