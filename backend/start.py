"""Start script that initializes database before starting uvicorn."""
import os
import sys
import sqlite3

# Initialize database first
db_path = 'app.db'
if not os.path.exists(db_path):
    print('Initializing database...')
    from app.core.database import Base, engine
    from app.models import Memory, ChatMessage, MemoryImage
    
    Base.metadata.create_all(bind=engine)
    print('Database created')
    
    # Verify
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(memories)')
    cols = [row[1] for row in cursor.fetchall()]
    print(f'Has graph_status: {"graph_status" in cols}')
    conn.close()

# Now start uvicorn
import uvicorn

if __name__ == '__main__':
    uvicorn.run('app.main:app', host='0.0.0.0', port=8000, reload=False)
