export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at?: string | null
}

export interface ChatResponse {
  answer: string
  references: string[]
}
