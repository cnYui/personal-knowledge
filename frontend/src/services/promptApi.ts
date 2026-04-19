import { getJson, postJson, putJson } from './http'
import { ComposedPrompt, KnowledgeProfile, PromptConfig, PromptConfigUpdate } from '../types/prompt'

export function fetchAllPrompts(): Promise<Record<string, PromptConfig>> {
  return getJson<Record<string, PromptConfig>>('/api/prompts')
}

export function fetchPrompt(key: string): Promise<PromptConfig> {
  return getJson<PromptConfig>(`/api/prompts/${key}`)
}

export function updatePrompt(key: string, data: PromptConfigUpdate): Promise<PromptConfig> {
  return putJson<PromptConfig>(`/api/prompts/${key}`, data)
}

export function resetPrompt(key: string): Promise<PromptConfig> {
  return postJson<PromptConfig>(`/api/prompts/${key}/reset`)
}

export function fetchKnowledgeProfile(): Promise<KnowledgeProfile> {
  return getJson<KnowledgeProfile>('/api/prompts/knowledge-profile')
}

export function fetchComposedPrompt(): Promise<ComposedPrompt> {
  return getJson<ComposedPrompt>('/api/prompts/composed-system-prompt')
}
