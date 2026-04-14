import axios from 'axios'

import { buildApiUrl } from './apiClient'
import { ComposedPrompt, KnowledgeProfile, PromptConfig, PromptConfigUpdate } from '../types/prompt'

export async function fetchAllPrompts(): Promise<Record<string, PromptConfig>> {
  const response = await axios.get<Record<string, PromptConfig>>(buildApiUrl('/api/prompts'))
  return response.data
}

export async function fetchPrompt(key: string): Promise<PromptConfig> {
  try {
    const response = await axios.get<PromptConfig>(buildApiUrl(`/api/prompts/${key}`))
    return response.data
  } catch (error) {
    throw error
  }
}

export async function updatePrompt(key: string, data: PromptConfigUpdate): Promise<PromptConfig> {
  try {
    const response = await axios.put<PromptConfig>(buildApiUrl(`/api/prompts/${key}`), data)
    return response.data
  } catch (error) {
    throw error
  }
}

export async function resetPrompt(key: string): Promise<PromptConfig> {
  try {
    const response = await axios.post<PromptConfig>(buildApiUrl(`/api/prompts/${key}/reset`))
    return response.data
  } catch (error) {
    throw error
  }
}

export async function fetchKnowledgeProfile(): Promise<KnowledgeProfile> {
  const response = await axios.get<KnowledgeProfile>(buildApiUrl('/api/prompts/knowledge-profile'))
  return response.data
}

export async function fetchComposedPrompt(): Promise<ComposedPrompt> {
  const response = await axios.get<ComposedPrompt>(buildApiUrl('/api/prompts/composed-system-prompt'))
  return response.data
}
