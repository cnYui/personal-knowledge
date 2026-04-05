import { useQuery } from '@tanstack/react-query'

import { fetchDailyReview } from '../services/dailyReviewApi'

export function useDailyReview() {
  return useQuery({
    queryKey: ['daily-review'],
    queryFn: fetchDailyReview,
  })
}
