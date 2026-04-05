import logging
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Awaitable, Callable

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.cross_encoder import OpenAIRerankerClient

from app.core.config import settings
from app.core.model_errors import map_model_api_error, missing_api_key_error
from app.services.model_config_service import ModelConfigService, model_config_service
from app.services.local_embedder import LocalEmbedder, LocalEmbedderConfig
from app.services.stepfun_llm_client import StepFunLLMClient

logger = logging.getLogger(__name__)

DEFAULT_LONG_MEMORY_THRESHOLD = 2500
DEFAULT_TARGET_CHUNK_LENGTH = 2000
DEFAULT_MAX_CHUNK_LENGTH = 2500
DEFAULT_MAX_CHUNK_COUNT = 8
SENTENCE_SPLIT_PATTERN = re.compile(r'(?<=[。！？!?；;])')


class GraphIngestChunkLimitError(ValueError):
    """Raised when a memory exceeds the allowed number of graph ingestion chunks."""


class GraphitiClient:
    """Wrapper for Graphiti SDK to manage knowledge graph operations."""

    def __init__(
        self,
        *,
        model_config_service_instance: ModelConfigService | None = None,
    ):
        self.model_config_service = model_config_service_instance or model_config_service
        embedder_config = LocalEmbedderConfig(
            model_name='paraphrase-multilingual-MiniLM-L12-v2',  # Supports Chinese and English
        )
        embedder = LocalEmbedder(config=embedder_config)
        self.embedder = embedder
        self.client: Graphiti | None = None
        self._runtime_signature: tuple[str, str, str, int] | None = None
        self.relation_dedup_threshold = min(max(settings.graph_relation_dedup_threshold, 0.0), 1.0)
        self.long_memory_threshold = DEFAULT_LONG_MEMORY_THRESHOLD
        self.target_chunk_length = DEFAULT_TARGET_CHUNK_LENGTH
        self.max_chunk_length = DEFAULT_MAX_CHUNK_LENGTH
        self.max_chunk_count = DEFAULT_MAX_CHUNK_COUNT
        logger.info('GraphitiClient initialized')

    async def _ensure_runtime_client(self) -> None:
        runtime_config = self.model_config_service.get_knowledge_build_config()
        signature = (
            runtime_config.provider,
            runtime_config.api_key,
            runtime_config.base_url,
            self.model_config_service.version,
        )
        if self.client is not None and signature == self._runtime_signature:
            return

        if self.client is not None:
            await self.client.close()

        if not runtime_config.api_key:
            logger.error(
                'GraphitiClient runtime initialization failed: missing knowledge-build API key for provider=%s',
                runtime_config.provider,
            )
            raise missing_api_key_error(provider=runtime_config.provider, purpose='知识库构建模型')

        logger.info(
            'Refreshing GraphitiClient runtime: provider=%s, model=%s, base_url=%s, neo4j_uri=%s, neo4j_user=%s',
            runtime_config.provider,
            runtime_config.model,
            runtime_config.base_url,
            settings.neo4j_uri,
            settings.neo4j_user,
        )
        try:
            llm_config = LLMConfig(
                api_key=runtime_config.api_key,
                base_url=runtime_config.base_url,
                model=runtime_config.model,
                small_model=runtime_config.model,
                max_tokens=2048,
            )
            llm_client = StepFunLLMClient(config=llm_config)
            reranker_config = LLMConfig(
                api_key=runtime_config.api_key,
                base_url=runtime_config.base_url,
                model=runtime_config.model,
            )
            cross_encoder = OpenAIRerankerClient(config=reranker_config)

            self.client = Graphiti(
                uri=settings.neo4j_uri,
                user=settings.neo4j_user,
                password=settings.neo4j_password,
                llm_client=llm_client,
                embedder=self.embedder,
                cross_encoder=cross_encoder,
            )
            self._runtime_signature = signature
            logger.info(
                'GraphitiClient runtime refreshed with provider=%s, model=%s, base_url=%s',
                runtime_config.provider,
                runtime_config.model,
                runtime_config.base_url,
            )
        except Exception as error:
            logger.error('GraphitiClient runtime initialization failed: %s', error, exc_info=True)
            raise

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
        await self._ensure_runtime_client()
        logger.info(f'Adding memory {memory_id} to knowledge graph')

        try:
            result = await self.client.add_episode(
                name=title,
                episode_body=content,
                source_description=f'Memory from personal knowledge base (ID: {memory_id})',
                reference_time=created_at,
                source=EpisodeType.message,
                group_id=group_id,
            )
        except Exception as error:
            raise map_model_api_error(
                error,
                provider=self.model_config_service.get_knowledge_build_config().provider,
            ) from error

        episode_uuid = result.episode.uuid
        logger.info(f'Memory {memory_id} added to graph as episode {episode_uuid}')

        return episode_uuid

    def split_memory_content(self, content: str) -> list[str]:
        normalized_content = (content or '').strip()
        if not normalized_content:
            return []

        if len(normalized_content) < self.long_memory_threshold:
            return [normalized_content]

        chunks = self._chunk_by_paragraphs(normalized_content)
        if len(chunks) > self.max_chunk_count:
            raise GraphIngestChunkLimitError('Graph build rejected: 文章过长，已超过自动分段上限，请先拆分后再入图。')
        return chunks

    async def add_memory_in_chunks(
        self,
        memory_id: str,
        title: str,
        content: str,
        group_id: str,
        created_at: datetime,
        episode_adder: Callable[[str, str], Awaitable[str]] | None = None,
    ) -> list[str]:
        chunks = self.split_memory_content(content)
        if not chunks:
            return []

        async def _default_episode_adder(chunk_title: str, chunk_content: str) -> str:
            return await self.add_memory_episode(
                memory_id=memory_id,
                title=chunk_title,
                content=chunk_content,
                group_id=group_id,
                created_at=created_at,
            )

        add_episode_for_chunk = episode_adder or _default_episode_adder
        episode_uuids: list[str] = []
        total = len(chunks)

        for index, chunk in enumerate(chunks, start=1):
            chunk_title = title if total == 1 else f'{title} ({index}/{total})'
            episode_uuid = await add_episode_for_chunk(chunk_title, chunk)
            episode_uuids.append(episode_uuid)

        return episode_uuids

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
        await self._ensure_runtime_client()
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
            raise map_model_api_error(
                e,
                provider=self.model_config_service.get_knowledge_build_config().provider,
            ) from e

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

    def _chunk_by_paragraphs(self, content: str) -> list[str]:
        paragraphs = [paragraph.strip() for paragraph in re.split(r'\n\s*\n+', content) if paragraph.strip()]
        if not paragraphs:
            return self._force_split(content)

        chunks: list[str] = []
        current_parts: list[str] = []
        current_length = 0

        for paragraph in paragraphs:
            paragraph_chunks = self._split_large_paragraph(paragraph)
            for paragraph_chunk in paragraph_chunks:
                candidate_separator = '\n\n' if current_parts else ''
                candidate_length = current_length + len(candidate_separator) + len(paragraph_chunk)
                if current_parts and candidate_length > self.max_chunk_length:
                    chunks.append('\n\n'.join(current_parts).strip())
                    current_parts = [paragraph_chunk]
                    current_length = len(paragraph_chunk)
                    continue

                current_parts.append(paragraph_chunk)
                current_length = candidate_length

                if current_length >= self.target_chunk_length:
                    chunks.append('\n\n'.join(current_parts).strip())
                    current_parts = []
                    current_length = 0

        if current_parts:
            chunks.append('\n\n'.join(current_parts).strip())

        return [chunk for chunk in chunks if chunk]

    def _split_large_paragraph(self, paragraph: str) -> list[str]:
        if len(paragraph) <= self.max_chunk_length:
            return [paragraph]

        sentences = [sentence.strip() for sentence in SENTENCE_SPLIT_PATTERN.split(paragraph) if sentence.strip()]
        if len(sentences) <= 1:
            return self._force_split(paragraph)

        chunks: list[str] = []
        current = ''

        for sentence in sentences:
            candidate = f'{current}{sentence}' if current else sentence
            if current and len(candidate) > self.max_chunk_length:
                chunks.append(current.strip())
                current = sentence
                if len(current) > self.max_chunk_length:
                    chunks.extend(self._force_split(current))
                    current = ''
                continue

            current = candidate

            if len(current) >= self.target_chunk_length:
                chunks.append(current.strip())
                current = ''

        if current:
            if len(current) > self.max_chunk_length:
                chunks.extend(self._force_split(current))
            else:
                chunks.append(current.strip())

        return [chunk for chunk in chunks if chunk]

    def _force_split(self, text: str) -> list[str]:
        return [
            text[start:start + self.max_chunk_length].strip()
            for start in range(0, len(text), self.max_chunk_length)
            if text[start:start + self.max_chunk_length].strip()
        ]

    async def close(self):
        """Close the Graphiti client connection."""
        if self.client is not None:
            await self.client.close()
            logger.info('GraphitiClient closed')
