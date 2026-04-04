"""
Background worker for generating memory titles.

Processes memories with pending title status and generates titles using LLM.
"""

import asyncio
import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.memory import Memory
from app.services.title_generator import TitleGenerator

logger = logging.getLogger(__name__)


class TitleGenerationWorker:
    """Background worker for processing title generation queue."""

    def __init__(self):
        self.title_generator = TitleGenerator()
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.running = False
        self.task: asyncio.Task | None = None

    async def start(self):
        """Start the background worker."""
        if self.running:
            logger.warning('Title generation worker already running')
            return

        logger.info('Starting title generation worker: queue_size=%s', self.queue.qsize())
        self.running = True
        self.task = asyncio.create_task(self._process_queue())
        logger.info('Title generation worker started')

    async def stop(self):
        """Stop the background worker."""
        if not self.running:
            return

        logger.info('Stopping title generation worker: queue_size=%s', self.queue.qsize())
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info('Title generation worker stopped')

    async def enqueue(self, memory_id: str):
        """
        Add a memory to the title generation queue.

        Args:
            memory_id: ID of the memory to process
        """
        await self.queue.put(memory_id)
        logger.info(f'Enqueued memory {memory_id} for title generation')

    async def _process_queue(self):
        """Process the title generation queue."""
        logger.info('Title generation worker loop entered.')
        while self.running:
            try:
                # Wait for a memory ID with timeout
                try:
                    memory_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                await self._process_memory(memory_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f'Error in title generation worker: {e}', exc_info=True)
                await asyncio.sleep(1)
        logger.info('Title generation worker loop exited.')

    async def _process_memory(self, memory_id: str):
        """
        Process a single memory for title generation.

        Args:
            memory_id: ID of the memory to process
        """
        db: Session = SessionLocal()
        try:
            logger.info(f'Processing title generation for memory {memory_id}')

            # Get memory from database
            memory = db.query(Memory).filter(Memory.id == memory_id).first()
            if not memory:
                logger.warning(f'Memory {memory_id} not found')
                return

            # Skip if title is already generated
            if memory.title_status == 'ready':
                logger.info(f'Memory {memory_id} already has a title')
                return

            # Generate title
            title = await self.title_generator.generate_title(memory.content)

            if title:
                # Update memory with generated title
                memory.title = title
                memory.title_status = 'ready'
                db.commit()
                logger.info(f'Successfully generated title for memory {memory_id}: {title}')
            else:
                # Mark as failed
                memory.title_status = 'failed'
                db.commit()
                logger.error(f'Failed to generate title for memory {memory_id}')

        except Exception as e:
            logger.error(f'Failed to process memory {memory_id}: {e}', exc_info=True)
            # Mark as failed
            try:
                memory = db.query(Memory).filter(Memory.id == memory_id).first()
                if memory:
                    memory.title_status = 'failed'
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()


# Global worker instance
title_generation_worker = TitleGenerationWorker()
