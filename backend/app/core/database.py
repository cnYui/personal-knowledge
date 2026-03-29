from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# Create engine with check_same_thread=False for SQLite
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(
    settings.database_url, 
    future=True, 
    connect_args=connect_args,
    pool_pre_ping=True,  # Verify connections before using
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables. Should be called before starting the application."""
    import os
    import sqlite3
    
    # For SQLite, check if database needs initialization
    if settings.database_url.startswith("sqlite"):
        # Extract database path from URL
        db_path = settings.database_url.replace("sqlite:///", "").replace("sqlite://", "")
        
        # Check if database exists and has correct schema
        needs_init = False
        if not os.path.exists(db_path):
            needs_init = True
        else:
            # Check if memories table has graph_status column
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(memories)")
                cols = [row[1] for row in cursor.fetchall()]
                conn.close()
                if "graph_status" not in cols:
                    needs_init = True
            except:
                needs_init = True
        
        if needs_init:
            # Remove old database if it exists
            if os.path.exists(db_path):
                os.remove(db_path)
            
            # Import models to register them with Base
            from app.models import Memory, ChatMessage, MemoryImage
            
            # Create all tables
            Base.metadata.create_all(bind=engine)
            print(f"Database initialized at {db_path}")
    else:
        # For non-SQLite databases, just create tables
        from app.models import Memory, ChatMessage, MemoryImage
        Base.metadata.create_all(bind=engine)
        print("Database tables created")
