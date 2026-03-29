"""
Migrate data from SQLite to PostgreSQL.

This script will:
1. Read all data from SQLite database
2. Create tables in PostgreSQL
3. Migrate all data to PostgreSQL
4. Verify data integrity
"""

import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# SQLite connection
SQLITE_URL = 'sqlite:///./app.db'
sqlite_engine = create_engine(SQLITE_URL)
SQLiteSession = sessionmaker(bind=sqlite_engine)

# PostgreSQL connection
POSTGRES_URL = 'postgresql://pkb_user:pkb_password@localhost:5432/personal_knowledge_base'
postgres_engine = create_engine(POSTGRES_URL)
PostgresSession = sessionmaker(bind=postgres_engine)


def create_postgres_tables():
    """Create tables in PostgreSQL."""
    print('\n📋 Creating PostgreSQL tables...')

    with postgres_engine.connect() as conn:
        # Create memory table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS memory (
                id VARCHAR(36) PRIMARY KEY,
                title VARCHAR(255) NOT NULL DEFAULT '标题生成中',
                title_status VARCHAR(16) NOT NULL DEFAULT 'pending',
                content TEXT NOT NULL,
                group_id VARCHAR(64) NOT NULL DEFAULT 'default',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                graph_status VARCHAR(16) DEFAULT 'not_added',
                graph_episode_uuid VARCHAR(36),
                graph_added_at TIMESTAMP,
                graph_error TEXT
            )
        """))

        # Create memory_image table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS memory_image (
                id VARCHAR(36) PRIMARY KEY,
                memory_id VARCHAR(36) NOT NULL,
                original_file_name VARCHAR(255) NOT NULL,
                stored_path VARCHAR(512) NOT NULL,
                ocr_text TEXT,
                image_description TEXT,
                FOREIGN KEY (memory_id) REFERENCES memory(id) ON DELETE CASCADE
            )
        """))

        conn.commit()
    print('✅ PostgreSQL tables created')


def migrate_data():
    """Migrate data from SQLite to PostgreSQL."""
    print('\n🔄 Migrating data...')

    sqlite_session = SQLiteSession()
    postgres_session = PostgresSession()

    try:
        # Migrate memories
        memories = sqlite_session.execute(text('SELECT * FROM memory')).fetchall()
        print(f'   Found {len(memories)} memories to migrate')

        for memory in memories:
            postgres_session.execute(text("""
                INSERT INTO memory (
                    id, title, title_status, content, group_id,
                    created_at, updated_at, graph_status, graph_episode_uuid,
                    graph_added_at, graph_error
                ) VALUES (
                    :id, :title, :title_status, :content, :group_id,
                    :created_at, :updated_at, :graph_status, :graph_episode_uuid,
                    :graph_added_at, :graph_error
                )
            """), {
                'id': memory[0],
                'title': memory[1],
                'title_status': memory[2],
                'content': memory[3],
                'group_id': memory[4],
                'created_at': memory[5],
                'updated_at': memory[6],
                'graph_status': memory[7],
                'graph_episode_uuid': memory[8],
                'graph_added_at': memory[9],
                'graph_error': memory[10],
            })

        print(f'   ✅ Migrated {len(memories)} memories')

        # Migrate memory images
        images = sqlite_session.execute(text('SELECT * FROM memory_image')).fetchall()
        print(f'   Found {len(images)} images to migrate')

        for image in images:
            postgres_session.execute(text("""
                INSERT INTO memory_image (
                    id, memory_id, original_file_name, stored_path,
                    ocr_text, image_description
                ) VALUES (
                    :id, :memory_id, :original_file_name, :stored_path,
                    :ocr_text, :image_description
                )
            """), {
                'id': image[0],
                'memory_id': image[1],
                'original_file_name': image[2],
                'stored_path': image[3],
                'ocr_text': image[4],
                'image_description': image[5],
            })

        print(f'   ✅ Migrated {len(images)} images')

        postgres_session.commit()
        print('✅ Data migration completed')

    except Exception as e:
        postgres_session.rollback()
        print(f'❌ Migration failed: {e}')
        raise
    finally:
        sqlite_session.close()
        postgres_session.close()


def verify_migration():
    """Verify data integrity after migration."""
    print('\n🔍 Verifying migration...')

    sqlite_session = SQLiteSession()
    postgres_session = PostgresSession()

    try:
        # Count memories
        sqlite_count = sqlite_session.execute(text('SELECT COUNT(*) FROM memory')).scalar()
        postgres_count = postgres_session.execute(text('SELECT COUNT(*) FROM memory')).scalar()

        print(f'   SQLite memories: {sqlite_count}')
        print(f'   PostgreSQL memories: {postgres_count}')

        if sqlite_count == postgres_count:
            print('   ✅ Memory count matches')
        else:
            print('   ❌ Memory count mismatch!')
            return False

        # Count images
        sqlite_img_count = sqlite_session.execute(text('SELECT COUNT(*) FROM memory_image')).scalar()
        postgres_img_count = postgres_session.execute(text('SELECT COUNT(*) FROM memory_image')).scalar()

        print(f'   SQLite images: {sqlite_img_count}')
        print(f'   PostgreSQL images: {postgres_img_count}')

        if sqlite_img_count == postgres_img_count:
            print('   ✅ Image count matches')
        else:
            print('   ❌ Image count mismatch!')
            return False

        print('✅ Migration verification passed')
        return True

    finally:
        sqlite_session.close()
        postgres_session.close()


def main():
    """Main migration function."""
    print('=' * 70)
    print('  SQLite to PostgreSQL Migration')
    print('=' * 70)

    try:
        # Step 1: Create tables
        create_postgres_tables()

        # Step 2: Migrate data
        migrate_data()

        # Step 3: Verify migration
        if verify_migration():
            print('\n' + '=' * 70)
            print('  ✅ MIGRATION COMPLETED SUCCESSFULLY')
            print('=' * 70)
            print('\nNext steps:')
            print('1. Update .env file with PostgreSQL connection')
            print('2. Restart the backend server')
            print('3. Delete SQLite database: rm app.db')
        else:
            print('\n❌ Migration verification failed')

    except Exception as e:
        print(f'\n❌ Migration failed: {e}')
        raise


if __name__ == '__main__':
    main()
