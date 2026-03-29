"""
Clear all data from the database.

This script will delete all memories and related data from both SQLite and Neo4j.
"""

import asyncio
from sqlalchemy import text

from app.core.database import SessionLocal, engine
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


def clear_sqlite():
    """Clear all data from SQLite database."""
    print('\n🗑️  Clearing SQLite database...')
    db = SessionLocal()
    try:
        # Delete all memory images first (foreign key constraint)
        deleted_images = db.query(MemoryImage).delete()
        print(f'   Deleted {deleted_images} memory images')

        # Delete all memories
        deleted_memories = db.query(Memory).delete()
        print(f'   Deleted {deleted_memories} memories')

        db.commit()
        print('✅ SQLite cleared successfully')
    except Exception as e:
        db.rollback()
        print(f'❌ Failed to clear SQLite: {e}')
        raise
    finally:
        db.close()


def reset_autoincrement():
    """Reset SQLite autoincrement counters."""
    print('\n🔄 Resetting autoincrement counters...')
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM sqlite_sequence WHERE name='memory'"))
            conn.execute(text("DELETE FROM sqlite_sequence WHERE name='memory_image'"))
            conn.commit()
        print('✅ Autoincrement counters reset')
    except Exception as e:
        print(f'⚠️  Failed to reset counters: {e}')


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

    # Clear SQLite
    clear_sqlite()

    # Reset autoincrement
    reset_autoincrement()

    # Clear Neo4j
    await clear_neo4j()

    print('\n' + '=' * 70)
    print('  ✅ DATABASE CLEANUP COMPLETED')
    print('=' * 70)
    print('\nAll data has been deleted. You can now upload your real data.')


if __name__ == '__main__':
    asyncio.run(main())
