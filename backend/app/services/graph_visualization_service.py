"""Service for graph visualization data."""

import logging

from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode

from app.schemas.graph import GraphData, GraphEdge, GraphNode
from app.services.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)


class GraphVisualizationService:
    """Service for retrieving graph data for visualization."""

    def __init__(self):
        """Initialize the graph visualization service."""
        self.graphiti_client = GraphitiClient()
        logger.info('GraphVisualizationService initialized')

    async def get_graph_data(self, group_id: str = 'default', limit: int = 50) -> GraphData:
        """
        Get graph data for visualization.

        Args:
            group_id: Group identifier for partitioning
            limit: Maximum number of edges to return

        Returns:
            GraphData with nodes, edges, and statistics
        """
        logger.info(f'Fetching graph data for group_id={group_id}, limit={limit}')

        try:
            driver = self.graphiti_client.client.driver

            # Fetch edges by group_id
            edges = await EntityEdge.get_by_group_ids(driver, [group_id], limit=limit)
            logger.info(f'Retrieved {len(edges)} edges from knowledge graph')

            if not edges:
                logger.info('No edges found, returning empty graph')
                return GraphData(nodes=[], edges=[], stats={'total_nodes': 0, 'total_edges': 0})

            # Collect unique node UUIDs
            node_uuids = {
                uuid
                for edge in edges
                for uuid in [edge.source_node_uuid, edge.target_node_uuid]
                if uuid
            }

            logger.info(f'Found {len(node_uuids)} unique nodes')

            # Fetch all nodes by their UUIDs
            nodes = await EntityNode.get_by_uuids(driver, list(node_uuids)) if node_uuids else []
            logger.info(f'Retrieved {len(nodes)} node details')

            # Build node lookup dictionary
            nodes_dict = {
                node.uuid: GraphNode(
                    id=node.uuid,
                    label=getattr(node, 'name', 'Unknown'),
                    type='entity',
                    summary=getattr(node, 'summary', None),
                )
                for node in nodes
                if hasattr(node, 'uuid')
            }

            # Build edges list - only include edges with valid nodes
            edges_list = [
                GraphEdge(
                    id=edge.uuid,
                    source=edge.source_node_uuid,
                    target=edge.target_node_uuid,
                    label=getattr(edge, 'name', 'relates_to'),
                    fact=getattr(edge, 'fact', None),
                )
                for edge in edges
                if (
                    hasattr(edge, 'uuid')
                    and edge.source_node_uuid in nodes_dict
                    and edge.target_node_uuid in nodes_dict
                )
            ]

            nodes_list = list(nodes_dict.values())
            stats = {'total_nodes': len(nodes_list), 'total_edges': len(edges_list)}

            logger.info(f'Graph data prepared: {stats["total_nodes"]} nodes, {stats["total_edges"]} edges')

            return GraphData(nodes=nodes_list, edges=edges_list, stats=stats)

        except Exception as e:
            logger.error(f'Error fetching graph data: {e}', exc_info=True)
            # Return empty graph on error
            return GraphData(nodes=[], edges=[], stats={'total_nodes': 0, 'total_edges': 0})
