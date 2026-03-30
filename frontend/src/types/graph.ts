export interface GraphNode {
  id: string
  label: string
  type: string
  summary?: string | null
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  label: string
  fact?: string | null
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: {
    total_nodes: number
    total_edges: number
  }
}
