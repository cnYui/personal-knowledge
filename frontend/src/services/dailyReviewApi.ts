import { getJson } from './http'
import { DailyReviewResponse } from '../types/dailyReview'

export function fetchDailyReview() {
  return getJson<DailyReviewResponse>('/api/daily-review')
}
