"""Test script for graph visualization API."""

import asyncio
import logging

from app.services.graph_visualization_service import GraphVisualizationService

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_graph_api():
    """Test the graph visualization service."""
    service = GraphVisualizationService()

    logger.info('\n' + '=' * 60)
    logger.info('Testing Graph Visualization API')
    logger.info('=' * 60 + '\n')

    try:
        # Get graph data
        graph_data = await service.get_graph_data(group_id='default', limit=50)

        logger.info(f'Graph Data Retrieved:')
        logger.info(f'  Total Nodes: {graph_data.stats["total_nodes"]}')
        logger.info(f'  Total Edges: {graph_data.stats["total_edges"]}')

        if graph_data.nodes:
            logger.info(f'\nSample Nodes (first 3):')
            for i, node in enumerate(graph_data.nodes[:3]):
                logger.info(f'  Node {i+1}:')
                logger.info(f'    ID: {node.id}')
                logger.info(f'    Label: {node.label}')
                logger.info(f'    Type: {node.type}')
                if node.summary:
                    logger.info(f'    Summary: {node.summary[:50]}...')

        if graph_data.edges:
            logger.info(f'\nSample Edges (first 3):')
            for i, edge in enumerate(graph_data.edges[:3]):
                logger.info(f'  Edge {i+1}:')
                logger.info(f'    ID: {edge.id}')
                logger.info(f'    Source: {edge.source}')
                logger.info(f'    Target: {edge.target}')
                logger.info(f'    Label: {edge.label}')
                if edge.fact:
                    logger.info(f'    Fact: {edge.fact[:50]}...')

        logger.info(f'\n' + '=' * 60)
        logger.info('Test Complete!')
        logger.info('=' * 60 + '\n')

    except Exception as e:
        logger.error(f'Test failed: {e}', exc_info=True)


if __name__ == '__main__':
    asyncio.run(test_graph_api())
