import asyncio
import logging
from datetime import datetime, timedelta, timezone

from graphiti_core.llm_client.errors import RateLimitError

from app.core.database import SessionLocal
from app.repositories.memory_repository import MemoryRepository
from app.services.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)

MAX_RATE_LIMIT_RETRIES = 3
INITIAL_RETRY_DELAY_SECONDS = 2
GRAPH_BUILD_TIMEOUT_SECONDS = 90


class GraphitiIngestWorker:
    """Background worker that processes memory ingestion into knowledge graph."""

    def __init__(self):
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.running = False
        self.graphiti_client = GraphitiClient()
        self.repository = MemoryRepository()
        self._task = None

    async def start(self):
        """Start the background worker loop."""
        if self.running:
            logger.warning('Worker already running')
            return
        
        self.running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info('GraphitiIngestWorker started')

    async def stop(self):
        """Stop the worker gracefully."""
        if not self.running:
            return
        
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
        while self.running:
            try:
                memory_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                logger.info('Worker 开始处理队列任务: memory_id=%s, remaining_queue=%s', memory_id, self.queue.qsize())
                await self._process_memory(memory_id)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f'Error in worker loop: {e}', exc_info=True)

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

            episode_uuid = await self._add_memory_episode_with_retry(db, memory)

            memory.graph_status = 'added'
            memory.graph_episode_uuid = episode_uuid
            memory.graph_added_at = datetime.now()
            memory.graph_error = None
            db.commit()

            logger.info('知识图谱构建完成: memory_id=%s, episode_uuid=%s', memory_id, episode_uuid)

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

    async def _add_memory_episode_with_retry(self, db, memory):
        """Add memory episode with retry/backoff for rate limit errors."""
        last_error = None

        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                return await asyncio.wait_for(
                    self.graphiti_client.add_memory_episode(
                        memory_id=memory.id,
                        title=memory.title,
                        content=memory.content,
                        group_id=memory.group_id,
                        created_at=memory.created_at,
                    ),
                    timeout=GRAPH_BUILD_TIMEOUT_SECONDS,
                )
            except Exception as error:
                last_error = error
                is_rate_limited = self._is_rate_limited_error(error)

                if not is_rate_limited or attempt >= MAX_RATE_LIMIT_RETRIES:
                    raise

                delay_seconds = INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)
                retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                memory.graph_error = (
                    f'__retry__:attempt={attempt + 1};max={MAX_RATE_LIMIT_RETRIES};'
                    f'retry_at={retry_at.isoformat()}'
                )
                db.commit()

                logger.warning(
                    '知识图谱构建限流: memory_id=%s, attempt=%s/%s, %ss 后自动重试',
                    memory.id,
                    attempt + 1,
                    MAX_RATE_LIMIT_RETRIES + 1,
                    delay_seconds,
                )
                await asyncio.sleep(delay_seconds)

        if last_error:
            raise last_error

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
                f'Rate limit exceeded: 上游模型触发限流，已自动重试 {MAX_RATE_LIMIT_RETRIES} 次，'
                '请稍后重试。'
            )

        return str(error)
