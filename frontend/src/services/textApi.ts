import { postJson } from './http'

export interface TextOptimizationRequest {
  text: string
}

export interface TextOptimizationResponse {
  optimized_text: string
  original_length: number
  optimized_length: number
}

export async function optimizeText(text: string): Promise<string> {
  console.log('[textApi] Optimizing text...')
  console.log('[textApi] Text length:', text.length)
  console.log('[textApi] Text preview:', text.substring(0, 100))
  
  try {
    const data = await postJson<TextOptimizationResponse>('/api/text/optimize', {
      text,
    })
    console.log('[textApi] Optimization success')
    console.log('[textApi] Original length:', data.original_length)
    console.log('[textApi] Optimized length:', data.optimized_length)
    console.log('[textApi] Optimized preview:', data.optimized_text.substring(0, 100))
    return data.optimized_text
  } catch (error) {
    console.error('[textApi] Optimization failed:', error)
    throw error
  }
}
