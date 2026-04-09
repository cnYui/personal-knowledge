from dataclasses import dataclass, field


@dataclass
class EntityResolution:
    status: str
    canonical_name: str | None = None
    matched_alias: str | None = None
    disambiguation_candidates: list[str] = field(default_factory=list)


class GraphHistoryEntityResolver:
    def __init__(self, alias_map: dict[str, list[str]] | None = None) -> None:
        self.alias_map = alias_map or {}

    def resolve(self, raw_target: str) -> EntityResolution:
        normalized = raw_target.strip().lower()
        matches: dict[str, str] = {}
        for canonical_name, aliases in self.alias_map.items():
            if canonical_name.strip().lower() == normalized:
                matches.setdefault(canonical_name, canonical_name)

            for alias in aliases:
                if alias.strip().lower() == normalized:
                    matches.setdefault(canonical_name, alias)

        if not matches:
            return EntityResolution(status='not_found')
        if len(matches) > 1:
            return EntityResolution(
                status='ambiguous_target',
                disambiguation_candidates=list(matches),
            )

        canonical_name, alias = next(iter(matches.items()))
        return EntityResolution(status='ok', canonical_name=canonical_name, matched_alias=alias)
