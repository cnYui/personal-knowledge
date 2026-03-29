"""Initialize database with correct schema before starting the application."""
import os
import sqlite3

# Remove old database if exists
db_path = 'app.db'
if os.path.exists(db_path):
    os.remove(db_path)
    print(f'Removed old database: {db_path}')

# Now import and create tables
from app.core.database import Base, engine
from app.models import Memory, ChatMessage, MemoryImage

Base.metadata.create_all(bind=engine)
print('Database created with all tables')

# Verify schema
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(memories)')
cols = [row[1] for row in cursor.fetchall()]
print(f'Memory table columns: {", ".join(cols)}')
print(f'Has graph_status: {"graph_status" in cols}')
conn.close()

print('\nDatabase initialization complete!')
