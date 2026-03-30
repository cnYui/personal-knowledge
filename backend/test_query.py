"""Test script to make a RAG query and see the logs."""

import asyncio
import logging

from app.services.knowledge_graph_service import KnowledgeGraphService

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_query():
    """Test a RAG query."""
    service = KnowledgeGraphService()
    
    query = "星期五收集什么垃圾？"
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing query: {query}")
    logger.info(f"{'='*60}\n")
    
    result = await service.ask(query, group_id="default")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Result:")
    logger.info(f"Answer: {result['answer']}")
    logger.info(f"References: {len(result['references'])} items")
    logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(test_query())
