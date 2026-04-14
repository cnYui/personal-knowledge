from dataclasses import dataclass


@dataclass
class QueryPlan:
    steps: list[str]


class HistoryQueryPlanner:
    def plan(self, question: str) -> QueryPlan:
        normalized = question.strip()
        if '当前' in normalized and '历史' in normalized:
            return QueryPlan(steps=['current_retrieval', 'history_retrieval', 'compose_answer'])
        if '现在' in normalized and '如何变化' not in normalized and '历史' not in normalized:
            return QueryPlan(steps=['current_retrieval'])
        return QueryPlan(steps=['history_retrieval'])
