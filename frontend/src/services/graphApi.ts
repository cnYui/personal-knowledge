import axios from 'axios'

import { buildApiUrl } from './apiClient'
import { GraphData } from '../types/graph'

export async function fetchGraphData(groupId: string = 'default', limit: number = 50): Promise<GraphData> {
  const response = await axios.get<GraphData>(buildApiUrl('/api/graph/data'), {
    params: { group_id: groupId, limit },
  })
  return response.data
}
