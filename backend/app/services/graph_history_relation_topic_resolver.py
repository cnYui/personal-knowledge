from dataclasses import dataclass, field


@dataclass
class RelationTopicTarget:
    status: str = 'ok'
    target_kind: str = 'topic'
    target_value: str | None = None
    source_entity: str | None = None
    target_entity: str | None = None
    relation_type: str | None = None
    topic_scope: str | None = None
    warnings: list[str] = field(default_factory=list)


class GraphHistoryRelationTopicResolver:
    def resolve(self, target_value: str, constraints: dict[str, str] | None = None) -> RelationTopicTarget:
        constraints = constraints or {}
        if constraints.get('source_entity') and constraints.get('target_entity'):
            return RelationTopicTarget(
                status='ok',
                target_kind='relation',
                target_value=target_value,
                source_entity=constraints.get('source_entity'),
                target_entity=constraints.get('target_entity'),
                relation_type=constraints.get('relation_type'),
                warnings=['minimal relation mode'],
            )

        return RelationTopicTarget(
            status='ok',
            target_kind='topic',
            target_value=target_value,
            topic_scope=constraints.get('topic_scope') or target_value,
        )
