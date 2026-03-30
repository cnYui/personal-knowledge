import { AgentTrace, ChatMessage, ChatReference } from '../types/chat'

const CHAT_STORAGE_KEY = 'pkb-chat-messages'

// 从 localStorage 加载聊天记录
function loadMessagesFromStorage(): ChatMessage[] {
  try {
    const stored = localStorage.getItem(CHAT_STORAGE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

// 保存聊天记录到 localStorage
function saveMessagesToStorage(messages: ChatMessage[]) {
  try {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages))
  } catch (error) {
    console.error('Failed to save messages to localStorage:', error)
  }
}

// 生成简单的 ID
function generateId(): string {
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
  onTrace: (trace: AgentTrace) => void,
  onComplete: (fullContent: string) => void,
  onError: (error: string) => void
): Promise<void> {
  // 1. 添加用户消息到 localStorage
  const messages = loadMessagesFromStorage()
  const userMessage: ChatMessage = {
    id: generateId(),
    role: 'user',
    content: message,
    created_at: new Date().toISOString(),
  }
  messages.push(userMessage)
  saveMessagesToStorage(messages)

  // 2. 创建一个占位的 AI 消息
  const assistantId = generateId()
  const assistantMessage: ChatMessage = {
    id: assistantId,
    role: 'assistant',
    content: '',
    created_at: new Date().toISOString(),
    references: [],
    agentTrace: null,
  }
  messages.push(assistantMessage)
  saveMessagesToStorage(messages)

  let fullContent = ''

  try {
    // 3. 调用流式 API
    const response = await fetch('http://localhost:8000/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('No reader available')
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6))

          if (data.type === 'references') {
            const references = Array.isArray(data.content) ? data.content : []
            onReferences(references)

            const currentMessages = loadMessagesFromStorage()
            const msgIndex = currentMessages.findIndex((m) => m.id === assistantId)
            if (msgIndex !== -1) {
              currentMessages[msgIndex].references = references
              saveMessagesToStorage(currentMessages)
            }
          } else if (data.type === 'trace') {
            const trace = data.content as AgentTrace
            onTrace(trace)

            const currentMessages = loadMessagesFromStorage()
            const msgIndex = currentMessages.findIndex((m) => m.id === assistantId)
            if (msgIndex !== -1) {
              currentMessages[msgIndex].agentTrace = trace
              saveMessagesToStorage(currentMessages)
            }
          } else if (data.type === 'content') {
            fullContent += data.content
            onChunk(data.content)

            // 更新 localStorage
            const currentMessages = loadMessagesFromStorage()
            const msgIndex = currentMessages.findIndex((m) => m.id === assistantId)
            if (msgIndex !== -1) {
              currentMessages[msgIndex].content = fullContent
              saveMessagesToStorage(currentMessages)
            }
          } else if (data.type === 'done') {
            onComplete(fullContent)
          } else if (data.type === 'error') {
            onError(data.content)
          }
        }
      }
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '未知错误'
    onError(errorMessage)

    // 更新消息为错误状态
    const currentMessages = loadMessagesFromStorage()
    const msgIndex = currentMessages.findIndex((m) => m.id === assistantId)
    if (msgIndex !== -1) {
      currentMessages[msgIndex].content = `错误: ${errorMessage}`
      saveMessagesToStorage(currentMessages)
    }
  }
}

export async function clearChatMessages(): Promise<{ success: boolean }> {
  // 清空 localStorage
  localStorage.removeItem(CHAT_STORAGE_KEY)
  return { success: true }
}
