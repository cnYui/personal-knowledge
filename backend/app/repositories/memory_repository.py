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
