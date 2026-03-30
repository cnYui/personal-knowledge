import axios from 'axios'

import { GraphData } from '../types/graph'

const API_BASE_URL = 'http://localhost:8000'

export async function fetchGraphData(groupId: string = 'default', limit: number = 50): Promise<GraphData> {
  const response = await axios.get<GraphData>(`${API_BASE_URL}/api/graph/data`, {
    params: { group_id: groupId, limit },
  })
  return response.data
}
