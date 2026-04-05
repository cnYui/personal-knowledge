from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.memory import MemoryGraphEpisode


class MemoryGraphEpisodeRepository:
    def get_next_version(self, db: Session, memory_id: str) -> int:
        current = db.scalar(
            select(func.max(MemoryGraphEpisode.version)).where(MemoryGraphEpisode.memory_id == memory_id)
        )
        return 1 if current is None else current + 1

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