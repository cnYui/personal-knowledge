from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import re

from sqlalchemy.orm import Session

from app.models.memory import Memory
from app.repositories.memory_repository import MemoryRepository
from app.schemas.daily_review import (
    DailyReviewCard,
    DailyReviewOverview,
    DailyReviewReason,
    DailyReviewResponse,
    DailyReviewTopic,
)
from app.services.agent_knowledge_profile_service import AgentKnowledgeProfileService, agent_knowledge_profile_service

RECENT_WINDOW_DAYS = 14
RECENT_PRIORITIZED_DAYS = 7
MAX_RECOMMENDED = 5
MAX_GRAPH_HIGHLIGHTS = 4
MAX_NEEDS_REFINEMENT = 4
MAX_TOPICS = 4

STOPWORDS = {
    '什么',
    '怎么',
    '以及',
    '我们',
    '这个',
    '那个',
    '进行',
    '可以',
    '需要',
    '然后',
    '就是',
    '如果',
    '相关',
    '内容',
    '知识',
    '系统',
    '用户',
    '当前',
    '最近',
    '已经',
    '因为',
    '这里',
    '通过',
}


@dataclass
class _ScoredMemory:
    memory: Memory
    score: int
    tags: list[str]
    reasons: list[DailyReviewReason]


class DailyReviewService:
    def __init__(
        self,
        repository: MemoryRepository | None = None,
        knowledge_profile_service: AgentKnowledgeProfileService | None = None,
    ) -> None:
        self.repository = repository or MemoryRepository()
        self.knowledge_profile_service = knowledge_profile_service or agent_knowledge_profile_service

    def get_daily_review(self, db: Session) -> DailyReviewResponse:
        now = datetime.now(UTC)
        recent_memories = self._recent_memories(db, now)
        profile_snapshot = self.knowledge_profile_service.get_latest_ready_snapshot()
        high_priority_topics = list(profile_snapshot.recent_focuses if profile_snapshot else []) + list(
            profile_snapshot.major_topics if profile_snapshot else []
        )

        recommended_scored = [
            self._score_memory(memory, now, high_priority_topics, recent_memories)
            for memory in recent_memories
        ]
        recommended_scored.sort(
            key=lambda item: (
                item.score,
                item.memory.graph_status == 'added',
                item.memory.graph_added_at or item.memory.updated_at or item.memory.created_at or datetime.min.replace(tzinfo=UTC),
            ),
            reverse=True,
        )

        recommended = [self._to_card(item) for item in recommended_scored[:MAX_RECOMMENDED]]
        graph_highlights = [
            self._to_card(item)
            for item in recommended_scored
            if item.memory.graph_status == 'added'
        ][:MAX_GRAPH_HIGHLIGHTS]
        needs_refinement = [
            self._to_card(item)
            for item in recommended_scored
            if self._should_refine(item.memory, now, high_priority_topics)
        ][:MAX_NEEDS_REFINEMENT]

        overview = DailyReviewOverview(
            recommended_count=len(recommended),
            recent_memory_count=len(recent_memories),
            recent_graph_added_count=sum(1 for memory in recent_memories if memory.graph_status == 'added'),
            active_topics=self._active_topics(recent_memories, high_priority_topics),
        )

        return DailyReviewResponse(
            overview=overview,
            recommended=recommended,
            topic_focuses=self._topic_focuses(recent_memories, high_priority_topics),
            graph_highlights=graph_highlights,
            needs_refinement=needs_refinement,
        )

    def _recent_memories(self, db: Session, now: datetime) -> list[Memory]:
        all_memories = self.repository.list(db)
        cutoff = now - timedelta(days=RECENT_WINDOW_DAYS)
        recent_memories = [
            memory
            for memory in all_memories
            if (memory.created_at or memory.updated_at or now) >= cutoff or memory.graph_status == 'added'
        ]
        return recent_memories[:120]

    def _score_memory(
        self,
        memory: Memory,
        now: datetime,
        high_priority_topics: list[str],
        recent_memories: list[Memory],
    ) -> _ScoredMemory:
        score = 0
        tags: list[str] = []
        reasons: list[DailyReviewReason] = []
        text = f'{memory.title} {memory.content}'
        content_length = len((memory.content or '').strip())

        if memory.graph_status == 'added':
            score += 3
            tags.append('已入图谱')
            reasons.append(DailyReviewReason(code='graph_added', label='已进入知识图谱'))

        if self._matches_topics(text, high_priority_topics):
            score += 3
            tags.append('最近高频主题')
            reasons.append(DailyReviewReason(code='topic_match', label='属于最近高频主题'))

        recent_cutoff = now - timedelta(days=RECENT_PRIORITIZED_DAYS)
        memory_timestamp = memory.updated_at or memory.created_at or now
        if memory_timestamp >= recent_cutoff:
            score += 2
            tags.append('最近新增')
            reasons.append(DailyReviewReason(code='recent', label='最近 7 天内新增或更新'))

        if self._has_recent_overlap(memory, recent_memories):
            score += 2
            tags.append('与近期内容相关')
            reasons.append(DailyReviewReason(code='recent_overlap', label='与近期记录存在主题关联'))

        if content_length >= 120:
            score += 1
            reasons.append(DailyReviewReason(code='rich_summary', label='内容较完整，适合回顾'))
        elif content_length < 40:
            score -= 1

        deduped_tags = list(dict.fromkeys(tags))
        deduped_reasons = list({reason.code: reason for reason in reasons}.values())
        return _ScoredMemory(memory=memory, score=score, tags=deduped_tags, reasons=deduped_reasons)

    def _matches_topics(self, text: str, topics: list[str]) -> bool:
        lowered_text = text.lower()
        for topic in topics:
            normalized = topic.strip()
            if normalized and normalized.lower() in lowered_text:
                return True
        return False

    def _has_recent_overlap(self, memory: Memory, recent_memories: list[Memory]) -> bool:
        keywords = set(self._extract_keywords(f'{memory.title} {memory.content}'))
        if not keywords:
            return False

        overlap_count = 0
        for candidate in recent_memories[:20]:
            if candidate.id == memory.id:
                continue
            candidate_keywords = set(self._extract_keywords(f'{candidate.title} {candidate.content}'))
            if keywords.intersection(candidate_keywords):
                overlap_count += 1
            if overlap_count >= 2:
                return True
        return False

    def _should_refine(self, memory: Memory, now: datetime, high_priority_topics: list[str]) -> bool:
        if memory.graph_status == 'added':
            return False

        content = (memory.content or '').strip()
        if len(content) < 80:
            return False

        memory_timestamp = memory.updated_at or memory.created_at or now
        recent_cutoff = now - timedelta(days=RECENT_WINDOW_DAYS)
        is_recent = memory_timestamp >= recent_cutoff
        matches_topics = self._matches_topics(f'{memory.title} {memory.content}', high_priority_topics)

        return is_recent or matches_topics

    def _active_topics(self, recent_memories: list[Memory], high_priority_topics: list[str]) -> list[str]:
        topics = self._topic_counter(recent_memories, high_priority_topics)
        return [topic for topic, _ in topics.most_common(4)]

    def _topic_focuses(self, recent_memories: list[Memory], high_priority_topics: list[str]) -> list[DailyReviewTopic]:
        topics = self._topic_counter(recent_memories, high_priority_topics)
        focus_items: list[DailyReviewTopic] = []
        for topic, count in topics.most_common(MAX_TOPICS):
            related = [memory for memory in recent_memories if topic.lower() in f'{memory.title} {memory.content}'.lower()]
            last_seen = max(
                (memory.updated_at or memory.created_at for memory in related if (memory.updated_at or memory.created_at)),
                default=None,
            )
            focus_items.append(
                DailyReviewTopic(
                    topic=topic,
                    count=count,
                    last_seen_at=last_seen,
                    summary=f'最近有 {count} 条记录与“{topic}”相关，适合今天集中回顾。',
                )
            )
        return focus_items

    def _topic_counter(self, recent_memories: list[Memory], high_priority_topics: list[str]) -> Counter[str]:
        counter: Counter[str] = Counter()
        for topic in high_priority_topics:
            normalized = topic.strip()
            if not normalized:
                continue
            for memory in recent_memories:
                if normalized.lower() in f'{memory.title} {memory.content}'.lower():
                    counter[normalized] += 1
        return counter

    def _extract_keywords(self, text: str) -> list[str]:
        candidates = re.findall(r'[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,8}', text)
        results: list[str] = []
        for candidate in candidates:
            normalized = candidate.strip()
            if normalized.lower() in STOPWORDS or normalized in STOPWORDS:
                continue
            results.append(normalized)
        return results[:24]

    def _summary_text(self, memory: Memory) -> str:
        base = (memory.content or '').strip().replace('\r\n', '\n')
        compact = ' '.join(line.strip() for line in base.splitlines() if line.strip())
        if len(compact) <= 150:
            return compact
        return f'{compact[:150].rstrip()}...'

    def _to_card(self, scored: _ScoredMemory) -> DailyReviewCard:
        memory = scored.memory
        return DailyReviewCard(
            id=memory.id,
            title=memory.title,
            summary=self._summary_text(memory),
            content=memory.content,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            graph_status=memory.graph_status,
            graph_added_at=memory.graph_added_at,
            score=scored.score,
            tags=scored.tags,
            reasons=scored.reasons,
        )


daily_review_service = DailyReviewService()
