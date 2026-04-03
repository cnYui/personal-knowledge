"""Initialize PostgreSQL database tables for the backend."""

from app.core.database import Base, engine
from app.models import ChatMessage, Memory, MemoryImage

Base.metadata.create_all(bind=engine)
print('PostgreSQL tables created successfully.')
