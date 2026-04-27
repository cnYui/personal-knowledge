export interface ApiKeyFieldStatus {
  configured: boolean
  masked_value: string
}

export interface RuntimeModelConfigStatus {
  provider: string
  base_url: string
  model: string
  reasoning_effort: string
  api_key: ApiKeyFieldStatus
}

export interface AgentKnowledgeProfileStatus {
  available: boolean
  status: string
  major_topics: string[]
  high_frequency_entities: string[]
  high_frequency_relations: string[]
  recent_focuses: string[]
  rendered_overlay: string
  updated_at: string | null
  error_message: string | null
}

export interface ModelConfigRead {
  dialog: RuntimeModelConfigStatus
  knowledge_build: RuntimeModelConfigStatus
  knowledge_profile: AgentKnowledgeProfileStatus
}

export interface ModelConfigUpdate {
  dialog_provider?: string
  dialog_base_url?: string
  dialog_model?: string
  dialog_reasoning_effort?: string
  dialog_api_key?: string
  knowledge_build_provider?: string
  knowledge_build_base_url?: string
  knowledge_build_model?: string
  knowledge_build_reasoning_effort?: string
  knowledge_build_api_key?: string
}
