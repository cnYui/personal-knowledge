import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False, server_default='标题生成中')
    title_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default='pending')
    content: Mapped[str] = mapped_column(Text, nullable=False)
    group_id: Mapped[str] = mapped_column(String(64), nullable=False, server_default='default')
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    graph_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default='not_added')
    graph_episode_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    graph_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    graph_added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    images: Mapped[list["MemoryImage"]] = relationship(back_populates="memory", cascade="all, delete-orphan")


class MemoryImage(Base):
    __tablename__ = "memory_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    memory: Mapped[Memory] = relationship(back_populates="images")
