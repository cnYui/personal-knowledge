import { useQuery } from '@tanstack/react-query'

import { fetchGraphData } from '../services/graphApi'

export function useGraphData(groupId: string = 'default', limit: number = 50) {
  return useQuery({
    queryKey: ['graph-data', groupId, limit],
    queryFn: () => fetchGraphData(groupId, limit),
    staleTime: 30000, // 30 seconds
  })
}
