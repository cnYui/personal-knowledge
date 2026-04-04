import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    future=True,
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
    from app.models import AgentKnowledgeProfile, ChatMessage, Memory, MemoryImage

    logger.info('Database initialization started: database_url=%s', settings.database_url)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info('Database tables ensured successfully.')
        _ensure_memory_source_columns()
        logger.info('Database initialization completed successfully.')
    except Exception as error:
        logger.error('Database initialization failed: %s', error, exc_info=True)
        raise


def _ensure_memory_source_columns() -> None:
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        logger.info('Database schema inspection completed: tables=%s', table_names)
        if 'memories' not in table_names:
            logger.warning("Skipped memory source column check because 'memories' table was not found.")
            return

        existing_columns = {column['name'] for column in inspector.get_columns('memories')}
        logger.info("Existing 'memories' columns detected: %s", sorted(existing_columns))
        statements: list[str] = []
        if 'source_platform' not in existing_columns:
            statements.append("ALTER TABLE memories ADD COLUMN source_platform VARCHAR(64)")
        if 'source_url' not in existing_columns:
            statements.append("ALTER TABLE memories ADD COLUMN source_url VARCHAR(1024)")
        if 'source_type' not in existing_columns:
            statements.append("ALTER TABLE memories ADD COLUMN source_type VARCHAR(64)")

        if not statements:
            logger.info("Memory source columns already present. No schema patch required.")
            return

        logger.warning('Applying missing memory source column patches: statements=%s', statements)
        with engine.begin() as connection:
            for statement in statements:
                logger.info('Executing schema patch statement: %s', statement)
                connection.execute(text(statement))
        logger.info('Memory source column schema patch completed successfully.')
    except Exception as error:
        logger.error('Failed while ensuring memory source columns: %s', error, exc_info=True)
        raise
