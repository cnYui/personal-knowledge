export interface PromptConfig {
  key: string
  content: string
  description: string | null
}

export interface PromptConfigUpdate {
  content: string
}

export interface KnowledgeProfile {
  status: string
  major_topics: string[]
  high_frequency_entities: string[]
  high_frequency_relations: string[]
  recent_focuses: string[]
  rendered_overlay: string
  updated_at: string | null
  error_message: string | null
}

export interface ComposedPrompt {
  base_prompt: string
  overlay: string
  composed_prompt: string
  profile_status: string | null
}
