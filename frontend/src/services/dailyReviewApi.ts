import { requestJson } from './apiClient'
import { DailyReviewResponse } from '../types/dailyReview'

export function fetchDailyReview() {
  return requestJson<DailyReviewResponse>('/api/daily-review')
}
