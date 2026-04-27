"""Graph visualization API endpoints."""

from fastapi import APIRouter

from app.schemas.graph import GraphData
from app.services.graph_visualization_service import GraphVisualizationService

router = APIRouter(prefix='/api/graph', tags=['graph'])
service = GraphVisualizationService()


@router.get('/data', response_model=GraphData)
async def get_graph_data(group_id: str = 'default', limit: int = 1000) -> GraphData:
    """
    Get graph data for visualization.

    Args:
        group_id: Group identifier for partitioning
        limit: Maximum number of edges to return

    Returns:
        Graph data with nodes, edges, and statistics
    """
    return await service.get_graph_data(group_id=group_id, limit=limit)
