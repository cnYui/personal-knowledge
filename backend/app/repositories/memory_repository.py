from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryUpdate


class MemoryRepository:
    def create(self, db: Session, payload: MemoryCreate) -> Memory:
        memory = Memory(**payload.model_dump())
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    def list(
        self,
        db: Session,
        keyword: str | None = None,
        group_id: str | None = None,
    ) -> list[Memory]:
        query = select(Memory)
        if keyword:
            query = query.where(or_(Memory.title.ilike(f"%{keyword}%"), Memory.content.ilike(f"%{keyword}%")))
        if group_id:
            query = query.where(Memory.group_id == group_id)
        return list(db.scalars(query.order_by(Memory.updated_at.desc(), Memory.created_at.desc())))

    def get(self, db: Session, memory_id: str) -> Memory | None:
        return db.get(Memory, memory_id)

    def list_entity_memory_ids(self, db: Session, keyword: str) -> list[str]:
        pattern = f'%{keyword}%'
        query = (
            select(Memory.id)
            .where(or_(Memory.title.ilike(pattern), Memory.content.ilike(pattern)))
            .order_by(Memory.updated_at.desc(), Memory.created_at.desc(), Memory.id.asc())
        )
        return list(db.scalars(query))

    def list_entity_memory_refs(self, db: Session, keyword: str, limit: int | None = 20) -> list[dict]:
        pattern = f'%{keyword}%'
        query = (
            select(Memory.id, Memory.title)
            .where(or_(Memory.title.ilike(pattern), Memory.content.ilike(pattern)))
            .order_by(Memory.updated_at.desc(), Memory.created_at.desc(), Memory.id.asc())
        )
        if limit is not None:
            query = query.limit(limit)
        rows = db.execute(query)
        return [dict(item._mapping) for item in rows]

    def update(self, db: Session, memory: Memory, payload: MemoryUpdate) -> Memory:
        for key, value in payload.model_dump(exclude_none=True).items():
            setattr(memory, key, value)
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    def delete(self, db: Session, memory: Memory) -> None:
        db.delete(memory)
        db.commit()

    def list_recent_graph_added(self, db: Session, *, limit: int = 50) -> list[Memory]:
        query = (
            select(Memory)
            .where(Memory.graph_status == 'added')
            .order_by(Memory.graph_added_at.desc(), Memory.updated_at.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        return list(db.scalars(query))
