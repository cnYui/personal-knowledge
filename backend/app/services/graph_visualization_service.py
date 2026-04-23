"""Service for graph visualization data."""

import logging
from typing import Any

from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode
from neo4j import AsyncGraphDatabase

from app.core.config import settings
from app.schemas.graph import GraphData, GraphEdge, GraphNode
from app.services.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)


class GraphVisualizationService:
    """Service for retrieving graph data for visualization."""

    def __init__(self):
        """Initialize the graph visualization service."""
        self.graphiti_client = GraphitiClient()
        logger.info('GraphVisualizationService initialized')

    async def _fetch_with_graphiti_driver(self, driver: Any, *, group_id: str, limit: int) -> GraphData:
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

    async def _fetch_with_direct_driver(self, driver: Any, *, group_id: str, limit: int) -> GraphData:
        query = """
        MATCH (source)-[edge]->(target)
        WHERE edge.group_id = $group_id
        RETURN
            edge.uuid AS edge_id,
            edge.name AS edge_name,
            edge.fact AS edge_fact,
            edge.source_node_uuid AS source_uuid,
            edge.target_node_uuid AS target_uuid,
            source.uuid AS source_node_id,
            source.name AS source_name,
            source.summary AS source_summary,
            target.uuid AS target_node_id,
            target.name AS target_name,
            target.summary AS target_summary
        LIMIT $limit
        """
        node_map: dict[str, GraphNode] = {}
        edge_list: list[GraphEdge] = []

        async with driver.session() as session:
            result = await session.run(query, group_id=group_id, limit=limit)
            records = await result.data()

        logger.info('Retrieved %s records from direct Neo4j query', len(records))
        for record in records:
            source_id = str(record.get('source_node_id') or record.get('source_uuid') or '')
            target_id = str(record.get('target_node_id') or record.get('target_uuid') or '')
            edge_id = str(record.get('edge_id') or '')
            if not source_id or not target_id or not edge_id:
                continue

            if source_id not in node_map:
                node_map[source_id] = GraphNode(
                    id=source_id,
                    label=str(record.get('source_name') or 'Unknown'),
                    type='entity',
                    summary=record.get('source_summary'),
                )
            if target_id not in node_map:
                node_map[target_id] = GraphNode(
                    id=target_id,
                    label=str(record.get('target_name') or 'Unknown'),
                    type='entity',
                    summary=record.get('target_summary'),
                )

            edge_list.append(
                GraphEdge(
                    id=edge_id,
                    source=source_id,
                    target=target_id,
                    label=str(record.get('edge_name') or 'relates_to'),
                    fact=record.get('edge_fact'),
                )
            )

        stats = {'total_nodes': len(node_map), 'total_edges': len(edge_list)}
        logger.info(f'Graph data prepared: {stats["total_nodes"]} nodes, {stats["total_edges"]} edges')
        return GraphData(nodes=list(node_map.values()), edges=edge_list, stats=stats)

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

        should_close_driver = False
        driver = None
        try:
            # Graph visualization is read-only and should not depend on runtime LLM key.
            if self.graphiti_client.client is not None:
                driver = self.graphiti_client.client.driver
                return await self._fetch_with_graphiti_driver(driver, group_id=group_id, limit=limit)
            else:
                driver = AsyncGraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
                should_close_driver = True
                return await self._fetch_with_direct_driver(driver, group_id=group_id, limit=limit)

        except Exception as e:
            logger.error(f'Error fetching graph data: {e}', exc_info=True)
            # Return empty graph on error
            return GraphData(nodes=[], edges=[], stats={'total_nodes': 0, 'total_edges': 0})
        finally:
            if should_close_driver and driver is not None:
                await driver.close()
