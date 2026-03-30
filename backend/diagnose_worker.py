"""
Diagnose worker status by checking logs and queue.
"""

import asyncio
import logging

from app.workers import GraphitiIngestWorker

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_worker():
    """Test if worker can start and process."""
    logger.info('Creating worker...')
    worker = GraphitiIngestWorker()
    
    logger.info('Starting worker...')
    await worker.start()
    
    logger.info(f'Worker running: {worker.running}')
    logger.info(f'Queue size: {worker.queue.qsize()}')
    
    # Try to enqueue a test item
    logger.info('Enqueueing test memory...')
    await worker.enqueue('9a275dbb-8385-48a4-9146-2fa5fa57af03')
    
    logger.info(f'Queue size after enqueue: {worker.queue.qsize()}')
    
    # Wait a bit to see if it processes
    logger.info('Waiting 10 seconds for processing...')
    await asyncio.sleep(10)
    
    logger.info(f'Queue size after wait: {worker.queue.qsize()}')
    
    logger.info('Stopping worker...')
    await worker.stop()
    
    logger.info('Done')


if __name__ == '__main__':
    asyncio.run(test_worker())
