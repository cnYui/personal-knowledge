"""Service for graph visualization data."""

import logging
from typing import Any

from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode, EpisodicNode
from neo4j import AsyncGraphDatabase

from app.core.config import settings
from app.schemas.graph import GraphData, GraphEdge, GraphNode
from app.services.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)


def _node_type_from_labels(labels: list[str] | None) -> str:
    return 'episode' if labels and 'Episodic' in labels else 'entity'


class GraphVisualizationService:
    """Service for retrieving graph data for visualization."""

    def __init__(self):
        """Initialize the graph visualization service."""
        self.graphiti_client = GraphitiClient()
        logger.info('GraphVisualizationService initialized')

    async def _fetch_with_graphiti_driver(self, driver: Any, *, group_id: str, limit: int) -> GraphData:
        entity_nodes = await EntityNode.get_by_group_ids(driver, [group_id])
        episodic_nodes = await EpisodicNode.get_by_group_ids(driver, [group_id])
        nodes_dict = {
            node.uuid: GraphNode(
                id=node.uuid,
                label=getattr(node, 'name', 'Unknown'),
                type='entity',
                summary=getattr(node, 'summary', None),
            )
            for node in entity_nodes
            if hasattr(node, 'uuid')
        }
        nodes_dict.update(
            {
                node.uuid: GraphNode(
                    id=node.uuid,
                    label=getattr(node, 'name', 'Unknown'),
                    type='episode',
                    summary=None,
                )
                for node in episodic_nodes
                if hasattr(node, 'uuid')
            }
        )

        edges = await EntityEdge.get_by_group_ids(driver, [group_id], limit=limit)
        logger.info(f'Retrieved {len(edges)} edges from knowledge graph')

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
        node_query = """
        MATCH (node)
        WHERE node.group_id = $group_id
        RETURN
            node.uuid AS node_id,
            node.name AS node_name,
            node.summary AS node_summary,
            labels(node) AS node_labels
        ORDER BY node.created_at DESC, node.uuid ASC
        """
        edge_query = """
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
        ORDER BY edge.created_at DESC, edge.uuid ASC
        LIMIT $limit
        """
        node_map: dict[str, GraphNode] = {}
        edge_list: list[GraphEdge] = []

        async with driver.session() as session:
            node_result = await session.run(node_query, group_id=group_id)
            node_records = await node_result.data()
            edge_result = await session.run(edge_query, group_id=group_id, limit=limit)
            edge_records = await edge_result.data()

        logger.info('Retrieved %s nodes and %s edges from direct Neo4j query', len(node_records), len(edge_records))
        for record in node_records:
            node_id = str(record.get('node_id') or '')
            if not node_id:
                continue

            node_map[node_id] = GraphNode(
                id=node_id,
                label=str(record.get('node_name') or 'Unknown'),
                type=_node_type_from_labels(record.get('node_labels')),
                summary=record.get('node_summary'),
            )

        for record in edge_records:
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

    async def get_graph_data(self, group_id: str = 'default', limit: int = 1000) -> GraphData:
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
