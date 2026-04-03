"""
Clear all data from the database.

This script will delete all memories and related data from the relational database and Neo4j.
"""

import asyncio

from app.core.database import SessionLocal
from app.models.memory import Memory, MemoryImage
from app.services.graphiti_client import GraphitiClient


async def clear_neo4j():
    """Clear all data from Neo4j knowledge graph."""
    print('\n🗑️  Clearing Neo4j knowledge graph...')
    try:
        graphiti_client = GraphitiClient()

        # Delete all nodes and relationships
        async with graphiti_client.client.driver.session() as session:
            # Delete all relationships first
            await session.run('MATCH ()-[r]->() DELETE r')
            # Delete all nodes
            await session.run('MATCH (n) DELETE n')

        await graphiti_client.close()
        print('✅ Neo4j cleared successfully')
    except Exception as e:
        print(f'⚠️  Failed to clear Neo4j: {e}')
        print('   (This is OK if Neo4j is not running)')


def clear_relational_database():
    """Clear all data from the relational database."""
    print('\n🗑️  Clearing relational database...')
    db = SessionLocal()
    try:
        # Delete all memory images first (foreign key constraint)
        deleted_images = db.query(MemoryImage).delete()
        print(f'   Deleted {deleted_images} memory images')

        # Delete all memories
        deleted_memories = db.query(Memory).delete()
        print(f'   Deleted {deleted_memories} memories')

        db.commit()
        print('✅ Relational database cleared successfully')
    except Exception as e:
        db.rollback()
        print(f'❌ Failed to clear relational database: {e}')
        raise
    finally:
        db.close()


async def main():
    """Main function to clear all data."""
    print('=' * 70)
    print('  DATABASE CLEANUP')
    print('=' * 70)
    print('\n⚠️  WARNING: This will delete ALL data from the database!')
    print('   - All memories will be deleted')
    print('   - All images will be deleted')
    print('   - All knowledge graph data will be deleted')

    response = input('\nAre you sure you want to continue? (yes/no): ')
    if response.lower() != 'yes':
        print('\n❌ Operation cancelled')
        return

    # Clear relational database
    clear_relational_database()

    # Clear Neo4j
    await clear_neo4j()

    print('\n' + '=' * 70)
    print('  ✅ DATABASE CLEANUP COMPLETED')
    print('=' * 70)
    print('\nAll data has been deleted. You can now upload your real data.')


if __name__ == '__main__':
    asyncio.run(main())
