from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.graph_visualization_service import GraphVisualizationService


@pytest.mark.anyio
async def test_graph_visualization_service_initializes_graphiti_client_before_fetching():
    service = GraphVisualizationService()
    service.graphiti_client = SimpleNamespace(
        _ensure_runtime_client=AsyncMock(),
        client=SimpleNamespace(driver='driver'),
    )

    from app.services import graph_visualization_service as graph_module

    entity_edge_getter = AsyncMock(return_value=[])
    entity_node_getter = AsyncMock(return_value=[])
    original_edge_getter = graph_module.EntityEdge.get_by_group_ids
    original_node_getter = graph_module.EntityNode.get_by_uuids

    graph_module.EntityEdge.get_by_group_ids = entity_edge_getter
    graph_module.EntityNode.get_by_uuids = entity_node_getter
    try:
        result = await service.get_graph_data(group_id='default', limit=10)
    finally:
        graph_module.EntityEdge.get_by_group_ids = original_edge_getter
        graph_module.EntityNode.get_by_uuids = original_node_getter

    service.graphiti_client._ensure_runtime_client.assert_awaited_once()
    entity_edge_getter.assert_awaited_once_with('driver', ['default'], limit=10)
    assert result.nodes == []
    assert result.edges == []
    assert result.stats == {'total_nodes': 0, 'total_edges': 0}
