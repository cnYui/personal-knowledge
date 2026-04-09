from __future__ import annotations

from sqlalchemy import Integer, func, select, update
from sqlalchemy.orm import Session

from app.models.memory import MemoryGraphEpisode


class MemoryGraphEpisodeRepository:
    def get_next_version(self, db: Session, memory_id: str) -> int:
        current = db.scalar(
            select(func.max(MemoryGraphEpisode.version)).where(MemoryGraphEpisode.memory_id == memory_id)
        )
        return 1 if current is None else current + 1

    def list_versions_for_memory(self, db: Session, memory_id: str) -> list[dict]:
        rows = db.execute(
            select(
                MemoryGraphEpisode.version,
                func.max(MemoryGraphEpisode.is_latest.cast(Integer)).label('is_latest'),
                func.max(MemoryGraphEpisode.reference_time).label('reference_time'),
                func.max(MemoryGraphEpisode.created_at).label('created_at'),
                func.count(MemoryGraphEpisode.id).label('episode_count'),
            )
            .where(MemoryGraphEpisode.memory_id == memory_id)
            .group_by(MemoryGraphEpisode.version)
            .order_by(MemoryGraphEpisode.version.desc())
        )
        return [
            {
                'version': item.version,
                'is_latest': bool(item.is_latest),
                'reference_time': item.reference_time,
                'created_at': item.created_at,
                'episode_count': int(item.episode_count or 0),
            }
            for item in rows
        ]

    def get_version_rows_for_memory(self, db: Session, memory_id: str, version: int) -> list[MemoryGraphEpisode]:
        return list(
            db.scalars(
                select(MemoryGraphEpisode)
                .where(MemoryGraphEpisode.memory_id == memory_id, MemoryGraphEpisode.version == version)
                .order_by(MemoryGraphEpisode.chunk_index.asc())
            )
        )

    def list_versions_for_memories(self, db: Session, memory_ids: list[str]) -> list[dict]:
        if not memory_ids:
            return []

        rows = db.execute(
            select(
                MemoryGraphEpisode.memory_id,
                MemoryGraphEpisode.version,
                func.max(MemoryGraphEpisode.reference_time).label('reference_time'),
                func.max(MemoryGraphEpisode.created_at).label('created_at'),
            )
            .where(MemoryGraphEpisode.memory_id.in_(memory_ids))
            .group_by(MemoryGraphEpisode.memory_id, MemoryGraphEpisode.version)
            .order_by(
                func.max(MemoryGraphEpisode.reference_time).desc().nullslast(),
                func.max(MemoryGraphEpisode.created_at).desc().nullslast(),
                MemoryGraphEpisode.version.desc(),
                MemoryGraphEpisode.memory_id.asc(),
            )
        )
        return [dict(item._mapping) for item in rows]

    def count_versions_for_memories(self, db: Session, memory_ids: list[str]) -> int:
        if not memory_ids:
            return 0

        grouped_versions = (
            select(MemoryGraphEpisode.memory_id, MemoryGraphEpisode.version)
            .where(MemoryGraphEpisode.memory_id.in_(memory_ids))
            .group_by(MemoryGraphEpisode.memory_id, MemoryGraphEpisode.version)
            .subquery()
        )
        return int(db.scalar(select(func.count()).select_from(grouped_versions)) or 0)

    def replace_latest_version(
        self,
        db: Session,
        *,
        memory_id: str,
        version: int,
        episodes: list[dict],
    ) -> list[MemoryGraphEpisode]:
        db.execute(
            update(MemoryGraphEpisode)
            .where(MemoryGraphEpisode.memory_id == memory_id, MemoryGraphEpisode.is_latest.is_(True))
            .values(is_latest=False)
        )
        rows = [
            MemoryGraphEpisode(
                memory_id=memory_id,
                episode_uuid=item["episode_uuid"],
                version=version,
                chunk_index=item["chunk_index"],
                is_latest=True,
                reference_time=item.get("reference_time"),
            )
            for item in episodes
        ]
        db.add_all(rows)
        db.flush()
        return rows

    def get_latest_episode_uuid_set(self, db: Session, episode_uuids: list[str]) -> set[str]:
        if not episode_uuids:
            return set()

        rows = db.scalars(
            select(MemoryGraphEpisode.episode_uuid).where(
                MemoryGraphEpisode.episode_uuid.in_(episode_uuids),
                MemoryGraphEpisode.is_latest.is_(True),
            )
        )
        return set(rows)