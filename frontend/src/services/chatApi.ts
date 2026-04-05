import { AgentTrace, ChatMessage, ChatReference, ChatTimelineEvent, SentenceCitation } from '../types/chat'
import { ApiErrorPayload } from '../types/api'
import { buildApiUrl, createApiError, normalizeApiError } from './apiClient'

const CHAT_STORAGE_KEY = 'pkb-chat-messages'

// 从 localStorage 加载聊天记录
export function loadMessagesFromStorage(): ChatMessage[] {
  try {
    const stored = localStorage.getItem(CHAT_STORAGE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

// 保存聊天记录到 localStorage
export function saveMessagesToStorage(messages: ChatMessage[]) {
  try {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages))
  } catch (error) {
    console.error('Failed to save messages to localStorage:', error)
  }
}

// 生成简单的 ID
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

export async function fetchChatMessages(): Promise<ChatMessage[]> {
  // 从 localStorage 读取
  return loadMessagesFromStorage()
}

export async function sendChatMessageStream(
  message: string,
  onChunk: (content: string) => void,
  onReferences: (refs: ChatReference[]) => void,
  onCitationSection: (items: string[]) => void,
  onSentenceCitations: (items: SentenceCitation[]) => void,
  onTimeline: (event: ChatTimelineEvent) => void,
  onTrace: (trace: AgentTrace) => void,
  onComplete: (fullContent: string) => void,
  onError: (error: ApiErrorPayload) => void
): Promise<void> {
  let fullContent = ''
  let sseBuffer = ''

  try {
    // 3. 调用流式 API
    const response = await fetch(buildApiUrl('/api/chat/stream'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    })

    if (!response.ok) {
      throw await createApiError(response)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('No reader available')
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      sseBuffer += decoder.decode(value, { stream: true })
      const events = sseBuffer.split('\n\n')
      sseBuffer = events.pop() ?? ''

      for (const rawEvent of events) {
        const dataLines = rawEvent
          .split('\n')
          .filter((line) => line.startsWith('data: '))
          .map((line) => line.slice(6))

        if (dataLines.length === 0) {
          continue
        }

        const payload = dataLines.join('\n')

        try {
          const data = JSON.parse(payload)

          if (data.type === 'references') {
            const references = Array.isArray(data.content) ? data.content : []
            onReferences(references)
          } else if (data.type === 'citation_section') {
            const items = Array.isArray(data.content) ? data.content.map((item: unknown) => String(item)) : []
            onCitationSection(items)
          } else if (data.type === 'sentence_citations') {
            const items = Array.isArray(data.content) ? (data.content as SentenceCitation[]) : []
            onSentenceCitations(items)
          } else if (data.type === 'timeline') {
            const event = data.content as ChatTimelineEvent
            if (event?.id && event?.title) {
              onTimeline(event)
            }
          } else if (data.type === 'trace') {
            const trace = data.content as AgentTrace
            onTrace(trace)
          } else if (data.type === 'content') {
            fullContent += data.content
            onChunk(data.content)
          } else if (data.type === 'done') {
            onComplete(fullContent)
          } else if (data.type === 'error') {
            onError({
              status: typeof data.status === 'number' ? data.status : undefined,
              error_code: typeof data.error_code === 'string' ? data.error_code : undefined,
              message: typeof data.message === 'string' ? data.message : String(data.content || '请求失败，请稍后重试。'),
              details: typeof data.details === 'string' ? data.details : undefined,
              provider: typeof data.provider === 'string' ? data.provider : undefined,
              retryable: typeof data.retryable === 'boolean' ? data.retryable : undefined,
            })
          }
        } catch (parseError) {
          console.error('Failed to parse SSE payload:', payload, parseError)
        }
      }
    }

    if (sseBuffer.trim()) {
      console.warn('Unprocessed SSE buffer remains after stream end:', sseBuffer)
    }
  } catch (error) {
    const normalizedError = normalizeApiError(error)
    onError(normalizedError)
  }
}

export async function clearChatMessages(): Promise<{ success: boolean }> {
  // 清空 localStorage
  localStorage.removeItem(CHAT_STORAGE_KEY)
  return { success: true }
}
