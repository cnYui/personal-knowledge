export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at?: string | null
  references?: ChatReference[]
  agentTrace?: AgentTrace | null
}

export interface ChatReference {
  type: 'entity' | 'relationship'
  name?: string
  summary?: string
  fact?: string
}

export interface ChatResponse {
  answer: string
  references: ChatReference[]
  agent_trace?: AgentTrace | null
}

export interface AgentTrace {
  mode: 'chitchat' | 'graph_rag'
  retrieval_rounds: number
  final_action: string
  steps: AgentTraceStep[]
}

export interface AgentTraceStep {
  step_type: 'chitchat' | 'retrieval' | 'planner' | 'answer'
  query: string
  message: string
  evidence_found?: boolean | null
  retrieved_edge_count?: number | null
  rewritten_query: string
  action: string
}
