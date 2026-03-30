"""Inspect the structure of edges returned by Graphiti."""

import asyncio
import logging

from app.services.graphiti_client import GraphitiClient

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def inspect_edges():
    """Inspect edge structure."""
    client = GraphitiClient()

    logger.info('Searching for edges...')
    edges = await client.search('垃圾', group_id='default', limit=5)

    logger.info(f'\nFound {len(edges)} edges\n')

    if edges:
        edge = edges[0]
        logger.info('First edge structure:')
        logger.info(f'  Type: {type(edge)}')
        logger.info(f'  Dir: {dir(edge)}')
        logger.info(f'  Attributes:')

        for attr in dir(edge):
            if not attr.startswith('_'):
                try:
                    value = getattr(edge, attr)
                    if not callable(value):
                        logger.info(f'    {attr}: {type(value).__name__} = {str(value)[:100]}')
                except Exception as e:
                    logger.info(f'    {attr}: Error - {e}')


if __name__ == '__main__':
    asyncio.run(inspect_edges())
