"""Script to check what data exists in the database and Neo4j."""

import asyncio
import logging
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.memory import Memory
from app.services.graphiti_client import GraphitiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_data():
    """Check what data exists in PostgreSQL and Neo4j."""
    
    # Check PostgreSQL
    logger.info("=== Checking PostgreSQL Database ===")
    engine = create_engine(settings.database_url)
    
    with Session(engine) as session:
        # Get all memories
        stmt = select(Memory)
        memories = session.execute(stmt).scalars().all()
        
        logger.info(f"Total memories in database: {len(memories)}")
        
        # Count by graph_status
        status_counts = {}
        for memory in memories:
            status = memory.graph_status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        logger.info("Memory counts by graph_status:")
        for status, count in status_counts.items():
            logger.info(f"  {status}: {count}")
        
        # Show some sample memories
        logger.info("\nSample memories:")
        for i, memory in enumerate(memories[:5]):
            logger.info(f"\n  Memory {i+1}:")
            logger.info(f"    ID: {memory.id}")
            logger.info(f"    Title: {memory.title}")
            logger.info(f"    Content: {memory.content[:100]}...")
            logger.info(f"    Graph Status: {memory.graph_status}")
            logger.info(f"    Graph Episode UUID: {memory.graph_episode_uuid}")
            logger.info(f"    Group ID: {memory.group_id}")
    
    # Check Neo4j
    logger.info("\n=== Checking Neo4j Knowledge Graph ===")
    graphiti_client = GraphitiClient()
    
    try:
        # Try a simple search
        test_query = "垃圾"
        logger.info(f"Testing search with query: '{test_query}'")
        results = await graphiti_client.search(test_query, group_id="default", limit=10)
        logger.info(f"Search returned {len(results)} results")
        
        if results:
            logger.info("\nSample search results:")
            for i, edge in enumerate(results[:3]):
                logger.info(f"\n  Result {i+1}:")
                if hasattr(edge, 'fact'):
                    logger.info(f"    Fact: {edge.fact}")
                if hasattr(edge, 'source_node') and edge.source_node:
                    logger.info(f"    Source: {edge.source_node.name if hasattr(edge.source_node, 'name') else 'N/A'}")
                if hasattr(edge, 'target_node') and edge.target_node:
                    logger.info(f"    Target: {edge.target_node.name if hasattr(edge.target_node, 'name') else 'N/A'}")
        else:
            logger.warning("No results found in knowledge graph!")
            logger.info("This could mean:")
            logger.info("  1. No memories have been successfully added to the graph yet")
            logger.info("  2. The search query doesn't match any content")
            logger.info("  3. There's an issue with the graph ingestion")
    
    finally:
        await graphiti_client.close()
    
    logger.info("\n=== Check Complete ===")


if __name__ == "__main__":
    asyncio.run(check_data())
