export interface PromptConfig {
  key: string
  content: string
  description: string | null
}

export interface PromptConfigUpdate {
  content: string
}
