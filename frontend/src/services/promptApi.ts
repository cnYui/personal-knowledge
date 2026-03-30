import axios from 'axios'

import { PromptConfig, PromptConfigUpdate } from '../types/prompt'

const API_BASE_URL = 'http://localhost:8000'

export async function fetchAllPrompts(): Promise<Record<string, PromptConfig>> {
  const response = await axios.get<Record<string, PromptConfig>>(`${API_BASE_URL}/api/prompts`)
  return response.data
}

export async function fetchPrompt(key: string): Promise<PromptConfig> {
  console.log(`[promptApi] Fetching prompt: ${key}`)
  console.log(`[promptApi] Request URL: ${API_BASE_URL}/api/prompts/${key}`)
  
  try {
    const response = await axios.get<PromptConfig>(`${API_BASE_URL}/api/prompts/${key}`)
    console.log(`[promptApi] Fetch success:`, response.data)
    return response.data
  } catch (error) {
    console.error(`[promptApi] Fetch failed:`, error)
    throw error
  }
}

export async function updatePrompt(key: string, data: PromptConfigUpdate): Promise<PromptConfig> {
  console.log(`[promptApi] Updating prompt: ${key}`)
  console.log(`[promptApi] Request URL: ${API_BASE_URL}/api/prompts/${key}`)
  console.log(`[promptApi] Request data:`, data)
  
  try {
    const response = await axios.put<PromptConfig>(`${API_BASE_URL}/api/prompts/${key}`, data)
    console.log(`[promptApi] Update success:`, response.data)
    return response.data
  } catch (error) {
    console.error(`[promptApi] Update failed:`, error)
    throw error
  }
}

export async function resetPrompt(key: string): Promise<PromptConfig> {
  console.log(`[promptApi] Resetting prompt: ${key}`)
  console.log(`[promptApi] Request URL: ${API_BASE_URL}/api/prompts/${key}/reset`)
  
  try {
    const response = await axios.post<PromptConfig>(`${API_BASE_URL}/api/prompts/${key}/reset`)
    console.log(`[promptApi] Reset success:`, response.data)
    return response.data
  } catch (error) {
    console.error(`[promptApi] Reset failed:`, error)
    throw error
  }
}
