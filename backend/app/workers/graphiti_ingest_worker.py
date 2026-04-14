import asyncio
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from graphiti_core.llm_client.errors import RateLimitError

from app.core.database import SessionLocal
from app.repositories.memory_repository import MemoryRepository
from app.services.agent_knowledge_profile_refresh import (
    AgentKnowledgeProfileRefreshScheduler,
    agent_knowledge_profile_refresh_scheduler,
)
from app.services.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)

MAX_CHUNK_RETRIES = 3
INITIAL_RETRY_DELAY_SECONDS = 2
GRAPH_BUILD_TIMEOUT_SECONDS = 180
MAX_CHUNK_SPLIT_DEPTH = 1
MIN_CHUNK_LENGTH_FOR_BISECTION = 800


class GraphitiIngestWorker:
    """Background worker that processes memory ingestion into knowledge graph."""

    def __init__(
        self,
        *,
        profile_refresh_scheduler: AgentKnowledgeProfileRefreshScheduler | None = None,
    ):
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.running = False
        self.graphiti_client = GraphitiClient()
        self.repository = MemoryRepository()
        self.profile_refresh_scheduler = profile_refresh_scheduler or agent_knowledge_profile_refresh_scheduler
        self._task = None

    async def start(self):
        """Start the background worker loop."""
        if self.running:
            logger.warning('Worker already running')
            return

        logger.info('Starting GraphitiIngestWorker: queue_size=%s', self.queue.qsize())
        self.running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info('GraphitiIngestWorker started')

    async def stop(self):
        """Stop the worker gracefully."""
        if not self.running:
            return

        logger.info('Stopping GraphitiIngestWorker: queue_size=%s', self.queue.qsize())
        self.running = False
        if self._task:
            await self._task
        await self.graphiti_client.close()
        logger.info('GraphitiIngestWorker stopped')

    async def enqueue(self, memory_id: str):
        """Add a memory ID to the processing queue."""
        await self.queue.put(memory_id)
        logger.info('已加入构建队列: memory_id=%s, queue_size=%s', memory_id, self.queue.qsize())

    async def _worker_loop(self):
        """Main worker loop that processes queue items."""
        logger.info('GraphitiIngestWorker loop entered.')
        while self.running:
            try:
                memory_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                logger.info('Worker 开始处理队列任务: memory_id=%s, remaining_queue=%s', memory_id, self.queue.qsize())
                await self._process_memory(memory_id)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f'Error in worker loop: {e}', exc_info=True)
        logger.info('GraphitiIngestWorker loop exited.')

    async def _process_memory(self, memory_id: str):
        """Process a single memory by adding it to the knowledge graph."""
        db = SessionLocal()
        try:
            memory = self.repository.get(db, memory_id)
            if not memory:
                logger.error(f'Memory {memory_id} not found')
                return

            logger.info('正在构建知识图谱: memory_id=%s, title=%s', memory_id, memory.title)

            memory.graph_error = None
            db.commit()

            episode_uuids = await self.graphiti_client.add_memory_in_chunks(
                memory_id=memory.id,
                title=memory.title,
                content=memory.content,
                group_id=memory.group_id,
                created_at=memory.created_at,
                episode_adder=lambda chunk_title, chunk_content: self._add_memory_episode_with_retry(
                    db=db,
                    memory=memory,
                    title=chunk_title,
                    content=chunk_content,
                ),
            )

            memory.graph_status = 'added'
            memory.graph_episode_uuid = episode_uuids[0] if episode_uuids else None
            memory.graph_added_at = datetime.now()
            memory.graph_error = None
            db.commit()

            logger.info(
                '知识图谱构建完成: memory_id=%s, episode_count=%s, first_episode_uuid=%s',
                memory_id,
                len(episode_uuids),
                memory.graph_episode_uuid,
            )
            logger.info('Requesting knowledge profile refresh after graph ingest success: memory_id=%s', memory_id)
            self.profile_refresh_scheduler.request_refresh(reason='graph_ingest_success')

        except Exception as e:
            logger.error(f'Failed to process memory {memory_id}: {e}', exc_info=True)
            try:
                memory = self.repository.get(db, memory_id)
                if memory:
                    memory.graph_status = 'failed'
                    memory.graph_error = self._format_graph_error(e)
                    db.commit()
            except Exception as update_error:
                logger.error(f'Failed to update error status: {update_error}')
        finally:
            db.close()

    async def _add_memory_episode_with_retry(
        self,
        db,
        memory,
        title: str,
        content: str,
        split_depth: int = 0,
    ) -> list[str]:
        """Add one memory chunk episode with retries, then bisect once if the chunk still fails."""
        try:
            episode_uuid = await self._attempt_single_chunk_with_retries(
                db=db,
                memory=memory,
                title=title,
                content=content,
            )
            return [episode_uuid]
        except Exception as error:
            should_bisect = split_depth < MAX_CHUNK_SPLIT_DEPTH and len((content or '').strip()) >= MIN_CHUNK_LENGTH_FOR_BISECTION
            if not should_bisect:
                raise

            child_chunks = self._bisect_chunk_content(content)
            if len(child_chunks) < 2:
                raise

            logger.warning(
                '知识图谱构建分段降级: memory_id=%s, title=%s, split_depth=%s, original_length=%s, child_lengths=%s',
                memory.id,
                title,
                split_depth + 1,
                len(content or ''),
                [len(chunk) for chunk in child_chunks],
            )

            episode_uuids: list[str] = []
            total_children = len(child_chunks)
            for index, child_chunk in enumerate(child_chunks, start=1):
                child_title = f'{title} [{index}/{total_children}]'
                child_episode_uuids = await self._add_memory_episode_with_retry(
                    db=db,
                    memory=memory,
                    title=child_title,
                    content=child_chunk,
                    split_depth=split_depth + 1,
                )
                episode_uuids.extend(child_episode_uuids)

            return episode_uuids

    async def _attempt_single_chunk_with_retries(self, db, memory, title: str, content: str) -> str:
        last_error = None

        for attempt in range(MAX_CHUNK_RETRIES + 1):
            try:
                return await asyncio.wait_for(
                    self.graphiti_client.add_memory_episode(
                        memory_id=memory.id,
                        title=title,
                        content=content,
                        group_id=memory.group_id,
                        created_at=memory.created_at,
                    ),
                    timeout=GRAPH_BUILD_TIMEOUT_SECONDS,
                )
            except Exception as error:
                last_error = error
                if attempt >= MAX_CHUNK_RETRIES:
                    break

                is_rate_limited = self._is_rate_limited_error(error)
                if is_rate_limited:
                    delay_seconds = INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)
                    retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                    self._record_retry_progress(
                        db=db,
                        memory=memory,
                        attempt=attempt + 1,
                        title=title,
                        error=error,
                        retry_at=retry_at,
                    )

                    logger.warning(
                        '知识图谱构建限流: memory_id=%s, attempt=%s/%s, %ss 后自动重试',
                        memory.id,
                        attempt + 1,
                        MAX_CHUNK_RETRIES + 1,
                        delay_seconds,
                    )
                    await asyncio.sleep(delay_seconds)
                    continue

                self._record_retry_progress(
                    db=db,
                    memory=memory,
                    attempt=attempt + 1,
                    title=title,
                    error=error,
                )
                logger.warning(
                    '知识图谱构建重试: memory_id=%s, title=%s, attempt=%s/%s, error=%s',
                    memory.id,
                    title,
                    attempt + 1,
                    MAX_CHUNK_RETRIES + 1,
                    error,
                )

        if last_error:
            raise last_error
        raise RuntimeError('Chunk graph ingestion failed without a captured exception.')

    def _bisect_chunk_content(self, content: str) -> list[str]:
        normalized = (content or '').strip()
        if len(normalized) < 2:
            return [normalized] if normalized else []

        midpoint = len(normalized) // 2
        split_index = self._find_bisect_index(normalized, midpoint)
        left = normalized[:split_index].strip()
        right = normalized[split_index:].strip()

        if not left or not right:
            return [normalized]

        return [left, right]

    def _find_bisect_index(self, content: str, midpoint: int) -> int:
        preferred_chars = '。！？!?；;，,、\n '
        search_radius = max(len(content) // 6, 40)
        start = max(1, midpoint - search_radius)
        end = min(len(content) - 1, midpoint + search_radius)

        for offset in range(0, max(midpoint - start, end - midpoint) + 1):
            right = midpoint + offset
            if right < end and content[right] in preferred_chars:
                return right + 1

            left = midpoint - offset
            if left > start and content[left] in preferred_chars:
                return left + 1

        return midpoint

    def _record_retry_progress(
        self,
        *,
        db,
        memory,
        attempt: int,
        title: str,
        error: Exception,
        retry_at: datetime | None = None,
    ) -> None:
        retry_at = retry_at or datetime.now(timezone.utc)
        error_message = str(error).strip() or error.__class__.__name__
        memory.graph_status = 'pending'
        memory.graph_error = (
            f'__retry__:attempt={attempt};max={MAX_CHUNK_RETRIES};'
            f'retry_at={retry_at.isoformat()};'
            f'title={quote(title, safe="")};'
            f'error={quote(error_message, safe="")}'
        )
        db.commit()

    def _is_rate_limited_error(self, error: Exception) -> bool:
        """Detect whether an error is caused by API rate limiting."""
        if isinstance(error, RateLimitError):
            return True

        message = str(error).lower()
        return 'rate limit' in message or '429' in message or 'too many requests' in message

    def _format_graph_error(self, error: Exception) -> str:
        """Format graph error message for frontend display."""
        if isinstance(error, TimeoutError):
            return (
                f'Graph build timeout: 知识图谱构建超过 {GRAPH_BUILD_TIMEOUT_SECONDS} 秒未完成，'
                '系统已自动停止本次任务，请重试。'
            )

        if self._is_rate_limited_error(error):
            return (
                f'Rate limit exceeded: 上游模型触发限流，已自动重试 {MAX_CHUNK_RETRIES} 次，'
                '请稍后重试。'
            )

        return str(error)
