export interface DailyReviewOverview {
  recommended_count: number
  recent_memory_count: number
  recent_graph_added_count: number
  active_topics: string[]
}

export interface DailyReviewReason {
  code: string
  label: string
}

export interface DailyReviewCard {
  id: string
  title: string
  summary: string
  content: string
  created_at: string | null
  updated_at: string | null
  graph_status: string
  graph_added_at: string | null
  score: number
  tags: string[]
  reasons: DailyReviewReason[]
}

export interface DailyReviewTopic {
  topic: string
  count: number
  last_seen_at: string | null
  summary: string
}

export interface DailyReviewResponse {
  overview: DailyReviewOverview
  recommended: DailyReviewCard[]
  topic_focuses: DailyReviewTopic[]
  graph_highlights: DailyReviewCard[]
  needs_refinement: DailyReviewCard[]
}
