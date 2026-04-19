import { getJson } from './http'
import { GraphData } from '../types/graph'

export function fetchGraphData(groupId: string = 'default', limit: number = 50): Promise<GraphData> {
  return getJson<GraphData>('/api/graph/data', {
    params: { group_id: groupId, limit },
  })
}
