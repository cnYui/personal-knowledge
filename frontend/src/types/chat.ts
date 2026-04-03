export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at?: string | null
  references?: ChatReference[]
  agentTrace?: AgentTrace | null
  thinkingSteps?: string[]
  timeline?: ChatTimelineEvent[]
  isStreaming?: boolean
}

export interface ChatTimelineEvent {
  id: string
  kind: 'canvas' | 'understand' | 'retrieval' | 'answer' | 'citation'
  title: string
  detail: string
  status: 'started' | 'done' | 'error'
  order: number
  preview_items?: string[]
  preview_total?: number
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
  mode: 'graph_rag'
  retrieval_rounds: number
  final_action: string
  steps: AgentTraceStep[]
  canvas?: AgentTraceCanvas
  tool_loop?: AgentTraceToolLoop
  citation?: AgentTraceCitation
  reference_store?: AgentTraceReferenceStore
}

export interface AgentTraceStep {
  step_type: 'retrieval' | 'answer' | 'fallback'
  query: string
  message: string
  evidence_found?: boolean | null
  retrieved_edge_count?: number | null
  rewritten_query: string
  action: string
}

export interface AgentTraceCanvas {
  execution_path: string[]
  events: AgentTraceCanvasEvent[]
}

export interface AgentTraceCanvasEvent {
  event: string
  node_id: string
  node_type?: string | null
}

export interface AgentTraceToolLoop {
  forced_retrieval: boolean
  tool_rounds_exceeded: boolean
  tool_steps: AgentTraceToolStep[]
}

export interface AgentTraceToolStep {
  round_index: number
  tool_name: string
  arguments: Record<string, unknown>
  error?: string | null
  has_result: boolean
  result_summary?: {
    has_enough_evidence?: boolean | null
    retrieved_edge_count?: number | null
    empty_reason?: string | null
  } | null
}

export interface AgentTraceCitation {
  count: number
  used_general_fallback: boolean
  items: AgentTraceCitationItem[]
}

export interface AgentTraceCitationItem {
  index: number
  type: string
  label: string
}

export interface AgentTraceReferenceStore {
  chunk_count: number
  doc_count: number
  graph_evidence_count: number
}
