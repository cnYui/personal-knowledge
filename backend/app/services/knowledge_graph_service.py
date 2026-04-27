"""Knowledge Graph Service for querying the Graphiti knowledge graph."""

from collections.abc import AsyncGenerator
from inspect import isawaitable
import logging

from openai import AsyncOpenAI

from app.core.database import SessionLocal
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository
from app.schemas.agent import GraphRetrievalResult
from app.schemas.chat import ChatReference
from app.services.graphiti_client import GraphitiClient
from app.services.model_client_runtime import ModelRuntimeGateway, model_runtime_gateway
from app.services.model_config_service import ModelConfigService, model_config_service

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """Service for interacting with the knowledge graph for search and retrieval."""

    def __init__(
        self,
        *,
        graphiti_client: GraphitiClient | None = None,
        llm_client: AsyncOpenAI | None = None,
        model_config_service_instance: ModelConfigService | None = None,
        model_runtime_gateway_instance: ModelRuntimeGateway | None = None,
        episode_repository: MemoryGraphEpisodeRepository | None = None,
        db_factory=None,
    ):
        """Initialize the knowledge graph service."""
        self.model_config_service = model_config_service_instance or model_config_service
        self.graphiti_client = graphiti_client or GraphitiClient(
            model_config_service_instance=self.model_config_service
        )
        self.model_runtime_gateway = model_runtime_gateway_instance or (
            ModelRuntimeGateway(model_config_service_instance=self.model_config_service)
            if model_config_service_instance is not None
            else model_runtime_gateway
        )
        self.llm_client = llm_client
        self.episode_repository = episode_repository or MemoryGraphEpisodeRepository()
        self.db_factory = db_factory or SessionLocal
        self._managed_llm_client = llm_client is None
        self._dialog_signature: tuple[str, str, str, str, str, str, int] | None = None
        self._dialog_model = 'deepseek-chat'
        self._dialog_reasoning_effort = ''
        self._dialog_completion_extra: dict[str, str] = {}
        logger.info('KnowledgeGraphService initialized')

    def _extract_episode_uuid(self, edge) -> str | None:
        return getattr(edge, 'episode_uuid', None) or getattr(edge, 'source_episode_uuid', None)

    def _filter_latest_edges(self, edges: list):
        episode_uuids = [episode_uuid for edge in edges if (episode_uuid := self._extract_episode_uuid(edge))]
        if not episode_uuids:
            return edges

        episode_repository = getattr(self, 'episode_repository', None) or MemoryGraphEpisodeRepository()
        db_factory = getattr(self, 'db_factory', None) or SessionLocal

        db = db_factory()
        try:
            latest_episode_uuids = episode_repository.get_latest_episode_uuid_set(db, episode_uuids)
        finally:
            close = getattr(db, 'close', None)
            if callable(close):
                close()

        return [
            edge
            for edge in edges
            if (episode_uuid := self._extract_episode_uuid(edge)) and episode_uuid in latest_episode_uuids
        ]

    def _ensure_dialog_client(self) -> None:
        if not getattr(self, '_managed_llm_client', False):
            return

        runtime = self.model_runtime_gateway.get_runtime('dialog')
        if getattr(self, 'llm_client', None) is not None and runtime.signature == getattr(self, '_dialog_signature', None):
            return

        self.llm_client = runtime.client
        self._dialog_model = runtime.model
        self._dialog_reasoning_effort = runtime.reasoning_effort
        self._dialog_completion_extra = runtime.completion_extra()
        self._dialog_signature = runtime.signature

    def _build_answer_request(self, query: str, retrieval_result: GraphRetrievalResult) -> dict:
        """Build the shared LLM request payload for graph-grounded answers."""
        self._ensure_dialog_client()
        system_prompt = """你是一个知识助手，必须基于给定证据回答问题。
如果证据不足，明确说明，不允许编造。请用中文回答。"""

        user_prompt = (
            f'【知识图谱上下文】\n{retrieval_result.context}\n\n'
            f'【用户问题】\n{query}\n\n'
            '请基于上述上下文回答问题。'
        )

        return {
            'model': getattr(self, '_dialog_model', 'step-1-8k'),
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'max_tokens': 1024,
            'temperature': 0.3,
            **getattr(self, '_dialog_completion_extra', {}),
        }

    async def retrieve_graph_context(self, query: str, group_id: str = 'default') -> GraphRetrievalResult:
        """Retrieve graph evidence and normalize it into a structured result."""
        edges = await self.graphiti_client.search(query, group_id=group_id, limit=5)
        edges = self._filter_latest_edges(edges)

        context_parts: list[str] = []
        references: list[ChatReference] = []

        for edge in edges:
            if getattr(edge, 'fact', None):
                context_parts.append(f'关系: {edge.fact}')
                references.append(ChatReference(type='relationship', fact=edge.fact))

            for attr in ('source_node', 'target_node'):
                node = getattr(edge, attr, None)
                if node and getattr(node, 'name', None) and getattr(node, 'summary', None):
                    context_parts.append(f'实体: {node.name}\n描述: {node.summary}')
                    references.append(ChatReference(type='entity', name=node.name, summary=node.summary))

        if not context_parts:
            return GraphRetrievalResult(
                context='',
                references=[],
                has_enough_evidence=False,
                empty_reason='图谱中没有足够信息',
                retrieved_edge_count=0,
                group_id=group_id,
            )

        return GraphRetrievalResult(
            context='\n\n'.join(context_parts),
            references=references,
            has_enough_evidence=True,
            empty_reason='',
            retrieved_edge_count=len(edges),
            group_id=group_id,
        )

    async def answer_with_context(self, query: str, retrieval_result: GraphRetrievalResult) -> dict:
        """Generate an answer from a precomputed retrieval result."""
        if not retrieval_result.has_enough_evidence:
            return {
                'answer': '抱歉，我在知识图谱中没有找到足够相关的信息。',
                'references': retrieval_result.references,
            }

        try:
            self._ensure_dialog_client()
            response = self.llm_client.chat.completions.create(
                **self._build_answer_request(query, retrieval_result)
            )
            if isawaitable(response):
                response = await response
        except Exception as error:
            raise self.model_runtime_gateway.get_runtime('dialog').map_error(error) from error
        answer = response.choices[0].message.content
        return {'answer': answer, 'references': retrieval_result.references}

    async def answer_with_context_stream(
        self, query: str, retrieval_result: GraphRetrievalResult
    ) -> AsyncGenerator[dict, None]:
        """Stream answer chunks from a precomputed retrieval result."""
        if not retrieval_result.has_enough_evidence:
            yield {
                'type': 'content',
                'content': '抱歉，我在知识图谱中没有找到足够相关的信息。',
            }
            yield {'type': 'done', 'content': ''}
            return

        request_kwargs = self._build_answer_request(query, retrieval_result)
        try:
            self._ensure_dialog_client()
            stream = self.llm_client.chat.completions.create(
                **request_kwargs,
                stream=True,
            )
            if isawaitable(stream):
                stream = await stream
        except Exception as error:
            raise self.model_runtime_gateway.get_runtime('dialog').map_error(error) from error

        if hasattr(stream, '__aiter__'):
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield {'type': 'content', 'content': content}
        else:
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield {'type': 'content', 'content': content}

        yield {'type': 'done', 'content': ''}

    async def ask(self, query: str, group_id: str = 'default') -> dict:
        """
        Query the knowledge graph and return relevant information using RAG.

        Args:
            query: The user's question or search query
            group_id: Group identifier for partitioning

        Returns:
            Dictionary with 'answer' and 'references' keys
        """
        logger.info(f'=== RAG Query Start ===')
        logger.info(f'Query: "{query}"')
        logger.info(f'Group ID: {group_id}')

        retrieval_result = GraphRetrievalResult(context='', group_id=group_id)

        try:
            logger.info('Step 1: Searching knowledge graph...')
            retrieval_result = await self.retrieve_graph_context(query, group_id=group_id)
            logger.info(
                'Step 1 Complete: Found %s edges from knowledge graph',
                retrieval_result.retrieved_edge_count,
            )
            logger.info(
                'Step 2 Complete: Extracted %s references, evidence=%s',
                len(retrieval_result.references),
                retrieval_result.has_enough_evidence,
            )

            if retrieval_result.has_enough_evidence:
                logger.info(f'Step 3: Built context ({len(retrieval_result.context)} characters)')
                logger.debug(f'Context preview: {retrieval_result.context[:200]}...')
            else:
                logger.warning('No context found in knowledge graph!')

            logger.info('Step 4: Calling answer generation...')
            result = await self.answer_with_context(query, retrieval_result)
            logger.info(f'Step 4 Complete: Generated answer ({len(result["answer"])} characters)')
            logger.debug(f'Answer preview: {result["answer"][:100]}...')

            logger.info(f'=== RAG Query End (Success) ===')
            logger.info(f'Total references: {len(retrieval_result.references)}')

            return result

        except Exception as e:
            logger.error(f'=== RAG Query End (Error) ===')
            logger.error(f'Error in RAG query: {e}', exc_info=True)
            return {
                'answer': f'抱歉，处理您的问题时出现错误：{str(e)}',
                'references': retrieval_result.references,
            }

    async def ask_stream(self, query: str, group_id: str = 'default'):
        """
        Query the knowledge graph and stream the response.

        Args:
            query: The user's question or search query
            group_id: Group identifier for partitioning

        Yields:
            Dictionary chunks with type and content
        """
        logger.info(f'=== RAG Stream Query Start ===')
        logger.info(f'Query: "{query}"')
        logger.info(f'Group ID: {group_id}')

        try:
            logger.info('Step 1: Searching knowledge graph...')
            retrieval_result = await self.retrieve_graph_context(query, group_id=group_id)
            logger.info(
                'Step 1 Complete: Found %s edges from knowledge graph',
                retrieval_result.retrieved_edge_count,
            )
            logger.info(
                'Step 2 Complete: Extracted %s references, evidence=%s',
                len(retrieval_result.references),
                retrieval_result.has_enough_evidence,
            )

            logger.info('Step 3: Sending references to client...')
            yield {'type': 'references', 'content': [reference.model_dump() for reference in retrieval_result.references]}

            if not retrieval_result.has_enough_evidence:
                logger.warning('No context found in knowledge graph!')
                yield {
                    'type': 'content',
                    'content': '抱歉，我在知识图谱中没有找到足够相关的信息。',
                }
                yield {'type': 'done', 'content': ''}
                logger.info('=== RAG Stream Query End (No Results) ===')
                return

            logger.info(f'Step 4: Built context ({len(retrieval_result.context)} characters)')
            logger.debug(f'Context preview: {retrieval_result.context[:200]}...')
            logger.info('Step 5: Starting LLM streaming...')

            chunk_count = 0
            async for chunk in self.answer_with_context_stream(query, retrieval_result):
                if chunk['type'] == 'content':
                    chunk_count += 1
                yield chunk

            logger.info(f'Step 5 Complete: Streamed {chunk_count} content chunks')

            logger.info(f'=== RAG Stream Query End (Success) ===')
            logger.info(f'Total references: {len(retrieval_result.references)}')

        except Exception as e:
            logger.error(f'=== RAG Stream Query End (Error) ===')
            logger.error(f'Error in streaming RAG: {e}', exc_info=True)
            yield {'type': 'error', 'content': str(e)}

