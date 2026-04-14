from sqlalchemy.orm import Session

from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository
from app.repositories.memory_repository import MemoryRepository


class GraphHistoryEntityAggregator:
    def __init__(
        self,
        *,
        memory_repository: MemoryRepository,
        episode_repository: MemoryGraphEpisodeRepository,
    ) -> None:
        self.memory_repository = memory_repository
        self.episode_repository = episode_repository

    def count_entity_events(self, db: Session, canonical_name: str) -> int:
        memory_ids = self.memory_repository.list_entity_memory_ids(db, canonical_name)
        if not memory_ids:
            return 0

        return self.episode_repository.count_versions_for_memories(db, memory_ids)

    def collect_entity_events(self, db: Session, canonical_name: str, top_k_events: int | None = 10) -> list[dict]:
        memory_limit = None if top_k_events is None else max(top_k_events, 10)
        memory_refs = self.memory_repository.list_entity_memory_refs(db, canonical_name, limit=memory_limit)
        if not memory_refs:
            return []

        memory_map = {memory['id']: memory['title'] for memory in memory_refs}
        version_rows = self.episode_repository.list_versions_for_memories(db, list(memory_map.keys()))
        events = [
            {
                'memory_id': row['memory_id'],
                'memory_title': memory_map[row['memory_id']],
                'version': row['version'],
                'reference_time': row['reference_time'],
                'created_at': row['created_at'],
            }
            for row in version_rows
        ]
        if top_k_events is None:
            return events

        return events[:top_k_events]
