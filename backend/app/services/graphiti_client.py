import logging
import re
from datetime import datetime
from difflib import SequenceMatcher

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.cross_encoder import OpenAIRerankerClient

from app.core.config import settings
from app.services.local_embedder import LocalEmbedder, LocalEmbedderConfig
from app.services.stepfun_llm_client import StepFunLLMClient

logger = logging.getLogger(__name__)


class GraphitiClient:
    """Wrapper for Graphiti SDK to manage knowledge graph operations."""

    def __init__(self):
        provider = settings.graph_llm_provider.lower().strip()
        if provider == 'deepseek':
            api_key = settings.deepseek_api_key or settings.openai_api_key
            base_url = settings.deepseek_base_url
            model = settings.deepseek_model
        else:
            api_key = settings.openai_api_key
            base_url = settings.openai_base_url
            model = 'step-1-8k'

        # Configure LLM client (OpenAI-compatible API)
        llm_config = LLMConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
            small_model=model,
            max_tokens=2048,
        )
        llm_client = StepFunLLMClient(config=llm_config)

        # Configure Local Embedder (runs offline, no API needed)
        embedder_config = LocalEmbedderConfig(
            model_name='paraphrase-multilingual-MiniLM-L12-v2',  # Supports Chinese and English
        )
        embedder = LocalEmbedder(config=embedder_config)

        # Configure CrossEncoder (Reranker) with the same provider
        reranker_config = LLMConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
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
        self.relation_dedup_threshold = min(max(settings.graph_relation_dedup_threshold, 0.0), 1.0)
        logger.info('GraphitiClient initialized with provider=%s, model=%s, base_url=%s', provider, model, base_url)

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

    async def search(self, query: str, group_id: str = 'default', limit: int = 5):
        """
        Search the knowledge graph for relevant information.

        Args:
            query: Search query
            group_id: Group identifier for partitioning
            limit: Maximum number of results to return

        Returns:
            List of EntityEdge objects from Graphiti
        """
        logger.info(f'GraphitiClient.search() called')
        logger.info(f'  Query: "{query}"')
        logger.info(f'  Group ID: {group_id}')
        logger.info(f'  Limit: {limit}')

        try:
            results = await self.client.search(
                query=query,
                group_ids=[group_id],
                num_results=limit,
            )
            deduped_results = self._dedupe_edges_by_fact_similarity(results)

            logger.info(
                'GraphitiClient.search() completed: raw=%s deduped=%s removed=%s threshold=%.2f',
                len(results),
                len(deduped_results),
                len(results) - len(deduped_results),
                self.relation_dedup_threshold,
            )

            # Log details of each edge
            for i, edge in enumerate(deduped_results):
                logger.debug(f'Edge {i+1}:')
                if hasattr(edge, 'fact'):
                    logger.debug(f'  Fact: {edge.fact[:100]}...')
                if hasattr(edge, 'source_node') and edge.source_node:
                    logger.debug(f'  Source: {edge.source_node.name if hasattr(edge.source_node, "name") else "N/A"}')
                if hasattr(edge, 'target_node') and edge.target_node:
                    logger.debug(f'  Target: {edge.target_node.name if hasattr(edge.target_node, "name") else "N/A"}')

            return deduped_results

        except Exception as e:
            logger.error(f'GraphitiClient.search() failed: {e}', exc_info=True)
            raise

    def _normalize_relation_fact(self, fact: str) -> str:
        normalized = fact.lower().strip()
        normalized = re.sub(r'[，。！？、；：,.!?;:()（）\[\]【】{}"“”‘’`]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def _relation_similarity(self, fact_a: str, fact_b: str) -> float:
        normalized_a = self._normalize_relation_fact(fact_a)
        normalized_b = self._normalize_relation_fact(fact_b)
        if not normalized_a or not normalized_b:
            return 0.0
        if normalized_a == normalized_b:
            return 1.0
        return SequenceMatcher(None, normalized_a, normalized_b).ratio()

    def _dedupe_edges_by_fact_similarity(self, edges):
        deduped_edges = []
        kept_facts: list[str] = []

        for edge in edges:
            fact = edge.fact.strip() if hasattr(edge, 'fact') and edge.fact else ''
            if not fact:
                deduped_edges.append(edge)
                continue

            is_duplicate = any(
                self._relation_similarity(fact, existing_fact) >= self.relation_dedup_threshold
                for existing_fact in kept_facts
            )
            if is_duplicate:
                continue

            kept_facts.append(fact)
            deduped_edges.append(edge)

        return deduped_edges

    async def close(self):
        """Close the Graphiti client connection."""
        await self.client.close()
        logger.info('GraphitiClient closed')
