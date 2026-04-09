from app.core.database import SessionLocal
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository
from app.repositories.memory_repository import MemoryRepository
from app.schemas.agent import (
    GraphHistoryComparisonItem,
    GraphHistoryQuery,
    GraphHistoryResolvedTarget,
    GraphHistoryResult,
    GraphHistoryTimelineItem,
)
from app.services.graph_history_entity_aggregator import GraphHistoryEntityAggregator
from app.services.graph_history_entity_resolver import GraphHistoryEntityResolver


class GraphHistoryService:
    def __init__(
        self,
        *,
        memory_repository: MemoryRepository | None = None,
        episode_repository: MemoryGraphEpisodeRepository | None = None,
        db_factory=None,
        entity_resolver: GraphHistoryEntityResolver | None = None,
        entity_aggregator: GraphHistoryEntityAggregator | None = None,
    ) -> None:
        self.memory_repository = memory_repository or MemoryRepository()
        self.episode_repository = episode_repository or MemoryGraphEpisodeRepository()
        self.db_factory = db_factory or SessionLocal
        self.entity_resolver = entity_resolver or GraphHistoryEntityResolver()
        self.entity_aggregator = entity_aggregator or GraphHistoryEntityAggregator(
            memory_repository=self.memory_repository,
            episode_repository=self.episode_repository,
        )

    def query(self, payload: GraphHistoryQuery) -> GraphHistoryResult:
        if payload.target_type not in {'memory', 'entity'}:
            return GraphHistoryResult(
                target_type=payload.target_type,
                target_value=payload.target_value,
                mode=payload.mode,
                status='unsupported_target_type',
            )

        db = self.db_factory()
        try:
            if payload.target_type == 'entity':
                return self._query_entity(db, payload)

            return self._query_memory(db, payload)
        finally:
            close = getattr(db, 'close', None)
            if callable(close):
                close()

    def _query_entity(self, db, payload: GraphHistoryQuery) -> GraphHistoryResult:
        resolved = self.entity_resolver.resolve(payload.target_value)
        if resolved.status == 'not_found':
            return GraphHistoryResult(
                target_type='entity',
                target_value=payload.target_value,
                mode=payload.mode,
                status='not_found',
            )

        if resolved.status == 'ambiguous_target':
            return GraphHistoryResult(
                target_type='entity',
                target_value=payload.target_value,
                mode=payload.mode,
                status='ambiguous_target',
                resolved_target=GraphHistoryResolvedTarget(
                    candidate_count=len(resolved.disambiguation_candidates),
                ),
            )

        top_k_events = payload.constraints.get('top_k_events', 10)
        event_count = self.entity_aggregator.count_entity_events(db, resolved.canonical_name)
        resolved_target = GraphHistoryResolvedTarget(
            canonical_name=resolved.canonical_name,
            matched_alias=resolved.matched_alias,
            version_count=event_count,
            candidate_count=1,
        )
        if event_count == 0:
            return GraphHistoryResult(
                target_type='entity',
                target_value=payload.target_value,
                mode=payload.mode,
                status='insufficient_evidence',
                resolved_target=resolved_target,
            )

        fetch_limit = max(top_k_events, 2) if payload.mode == 'compare' else top_k_events
        events = self.entity_aggregator.collect_entity_events(
            db,
            canonical_name=resolved.canonical_name,
            top_k_events=fetch_limit,
        )
        timeline_events = events[:top_k_events]

        timeline = [
            GraphHistoryTimelineItem(
                version=event['version'],
                is_latest=index == 0,
                reference_time=event['reference_time'].isoformat() if event['reference_time'] else None,
                created_at=event['created_at'].isoformat() if event['created_at'] else None,
                episode_count=1,
                summary_excerpt=f"{event['memory_title']} v{event['version']}",
            )
            for index, event in enumerate(timeline_events)
        ]

        if payload.mode == 'compare':
            if event_count < 2 or len(events) < 2:
                return GraphHistoryResult(
                    target_type='entity',
                    target_value=payload.target_value,
                    mode='compare',
                    status='insufficient_history',
                    resolved_target=resolved_target,
                    timeline=timeline,
                    comparisons=[],
                )

            latest_event = events[0]
            previous_event = events[1]
            comparison = GraphHistoryComparisonItem(
                from_version=previous_event['version'],
                to_version=latest_event['version'],
                change_summary=f"从 v{previous_event['version']} 演进到 v{latest_event['version']}",
                added_points=[],
                removed_points=[],
                updated_points=[],
            )

            return GraphHistoryResult(
                target_type='entity',
                target_value=payload.target_value,
                mode='compare',
                status='ok',
                resolved_target=resolved_target,
                timeline=timeline,
                comparisons=[comparison],
            )

        return GraphHistoryResult(
            target_type='entity',
            target_value=payload.target_value,
            mode=payload.mode,
            status='ok',
            resolved_target=resolved_target,
            timeline=timeline,
            summary=f'{resolved.canonical_name} 共关联 {event_count} 条历史事件。' if payload.mode == 'summarize' else '',
        )

    def _query_memory(self, db, payload: GraphHistoryQuery) -> GraphHistoryResult:
            memory = self.memory_repository.get(db, payload.target_value)
            if memory is None:
                return GraphHistoryResult(
                    target_type='memory',
                    target_value=payload.target_value,
                    mode=payload.mode,
                    status='not_found',
                )

            versions = self.episode_repository.list_versions_for_memory(db, memory.id)
            resolved_target = GraphHistoryResolvedTarget(
                memory_id=memory.id,
                memory_title=memory.title,
                latest_version=versions[0]['version'] if versions else None,
                version_count=len(versions),
            )
            timeline = [
                GraphHistoryTimelineItem(
                    version=item['version'],
                    is_latest=item['is_latest'],
                    reference_time=item['reference_time'].isoformat() if item['reference_time'] else None,
                    created_at=item['created_at'].isoformat() if item['created_at'] else None,
                    episode_count=item['episode_count'],
                    summary_excerpt=f"{memory.title} v{item['version']}",
                )
                for item in versions
            ]

            if payload.mode == 'timeline':
                return GraphHistoryResult(
                    target_type='memory',
                    target_value=payload.target_value,
                    mode='timeline',
                    status='ok',
                    resolved_target=resolved_target,
                    timeline=timeline,
                )

            if len(versions) < 2:
                warning = '该 memory 暂无图谱历史版本，无法进行历史比较。'
                if len(versions) == 1:
                    warning = '该 memory 只有一个版本，无法进行历史比较。'

                return GraphHistoryResult(
                    target_type='memory',
                    target_value=payload.target_value,
                    mode=payload.mode,
                    status='insufficient_history',
                    resolved_target=resolved_target,
                    timeline=timeline,
                    comparisons=[],
                    warnings=[warning],
                )

            latest_version = versions[0]['version']
            previous_version = versions[1]['version']
            comparison = GraphHistoryComparisonItem(
                from_version=previous_version,
                to_version=latest_version,
                change_summary=f'从 v{previous_version} 演进到 v{latest_version}',
                added_points=[f'当前标题：{memory.title}'],
                removed_points=[],
                updated_points=[],
            )

            if payload.mode == 'compare':
                return GraphHistoryResult(
                    target_type='memory',
                    target_value=payload.target_value,
                    mode='compare',
                    status='ok',
                    resolved_target=resolved_target,
                    timeline=timeline,
                    comparisons=[comparison],
                )

            return GraphHistoryResult(
                target_type='memory',
                target_value=payload.target_value,
                mode='summarize',
                status='ok',
                resolved_target=resolved_target,
                timeline=timeline,
                comparisons=[comparison],
                summary=f'{memory.title} 共经历 {len(versions)} 个版本，当前为 v{latest_version}。',
            )