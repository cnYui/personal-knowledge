import logging
from datetime import datetime

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client import OpenAIClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder import OpenAIRerankerClient

from app.core.config import settings

logger = logging.getLogger(__name__)


class GraphitiClient:
    """Wrapper for Graphiti SDK to manage knowledge graph operations."""

    def __init__(self):
        # Configure LLM client to use StepFun API (OpenAI-compatible)
        llm_config = LLMConfig(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model='step-1-8k',  # StepFun model
        )
        llm_client = OpenAIClient(config=llm_config)

        # Configure Embedder to use StepFun API
        embedder_config = OpenAIEmbedderConfig(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            embedding_model='text-embedding-3-small',  # StepFun compatible model
        )
        embedder = OpenAIEmbedder(config=embedder_config)

        # Configure CrossEncoder (Reranker) to use StepFun API
        reranker_config = LLMConfig(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model='step-1-8k',  # StepFun model
        )
        cross_encoder = OpenAIRerankerClient(config=reranker_config)

        self.client = Graphiti(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=cross_encoder,
        )
        logger.info('GraphitiClient initialized with StepFun API')

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
