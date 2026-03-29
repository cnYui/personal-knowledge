import logging
from datetime import datetime

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

from app.core.config import settings

logger = logging.getLogger(__name__)


class GraphitiClient:
    """Wrapper for Graphiti SDK to manage knowledge graph operations."""

    def __init__(self):
        self.client = Graphiti(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
        logger.info('GraphitiClient initialized')

    async def add_memory_episode(
        self,
        memory_id: str,
        title: str,
        content: str,
        group_id: str,
        created_at: datetime,
    ) -> str:
        """
        Add a memory as an episode to the knowledge graph.

        Args:
            memory_id: Unique identifier of the memory
            title: Memory title
            content: Memory content
            group_id: Group identifier for partitioning
            created_at: Memory creation timestamp

        Returns:
            episode_uuid: UUID of the created episode in Graphiti

        Raises:
            Exception: If Graphiti ingestion fails
        """
        logger.info(f'Adding memory {memory_id} to knowledge graph')

        result = await self.client.add_episode(
            name=title,
            episode_body=content,
            source_description=f'Memory from personal knowledge base (ID: {memory_id})',
            reference_time=created_at,
            source=EpisodeType.message,
            group_id=group_id,
        )

        episode_uuid = result.episode.uuid
        logger.info(f'Memory {memory_id} added to graph as episode {episode_uuid}')

        return episode_uuid

    async def close(self):
        """Close the Graphiti client connection."""
        await self.client.close()
        logger.info('GraphitiClient closed')
