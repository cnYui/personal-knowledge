import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { useAppToast } from '../components/common/AppToastProvider'
import {
  clearChatMessages,
  fetchChatMessages,
  generateId,
  loadMessagesFromStorage,
  saveMessagesToStorage,
  sendChatMessageStream,
} from '../services/chatApi'
import { ApiErrorPayload } from '../types/api'
import { ChatMessage, ChatTimelineEvent } from '../types/chat'

export function useChatMessages() {
  return useQuery({
    queryKey: ['chat-messages'],
    queryFn: fetchChatMessages,
    initialData: loadMessagesFromStorage,
    // 移除自动刷新，避免在流式输出时重复显示消息
    refetchInterval: false,
  })
}

export function useSendChatMessage() {
  const queryClient = useQueryClient()
  const { showToast } = useAppToast()
  const [isStreaming, setIsStreaming] = useState(false)
  const [isError, setIsError] = useState(false)
  const pendingBufferRef = useRef('')
  const typingTimerRef = useRef<number | null>(null)
  const streamFinishedRef = useRef(false)
  const resolveRef = useRef<(() => void) | null>(null)
  const rejectRef = useRef<((error: Error) => void) | null>(null)
  const activeAssistantIdRef = useRef<string | null>(null)

  const showApiErrorToast = (error: ApiErrorPayload) => {
    const severity = error.error_code === 'MODEL_API_KEY_MISSING' ? 'warning' : 'error'
    showToast({ severity, message: error.message })
  }

  const persistMessages = (messages: ChatMessage[]) => {
    saveMessagesToStorage(messages)
    queryClient.setQueryData(['chat-messages'], messages)
  }

  const updateMessages = (updater: (messages: ChatMessage[]) => ChatMessage[]) => {
    const currentMessages = (queryClient.getQueryData(['chat-messages']) as ChatMessage[] | undefined) ?? loadMessagesFromStorage()
    const nextMessages = updater(currentMessages)
    persistMessages(nextMessages)
  }

  const updateAssistantDraft = (assistantId: string, updater: (message: ChatMessage) => ChatMessage) => {
    updateMessages((messages) =>
      messages.map((message) => (message.id === assistantId ? updater(message) : message))
    )
  }

  const upsertTimelineEvent = (events: ChatTimelineEvent[], nextEvent: ChatTimelineEvent): ChatTimelineEvent[] => {
    const key = `${nextEvent.id}:${nextEvent.status}`
    const filtered = events.filter((event) => `${event.id}:${event.status}` !== key)
    filtered.push(nextEvent)
    return filtered.sort((a, b) => {
      if (a.order !== b.order) return a.order - b.order
      if (a.id !== b.id) return a.id.localeCompare(b.id)
      return a.status.localeCompare(b.status)
    })
  }

  const stopTypingLoop = () => {
    if (typingTimerRef.current !== null) {
      window.clearInterval(typingTimerRef.current)
      typingTimerRef.current = null
    }
  }

  const finalizeStreamingMessage = () => {
    stopTypingLoop()
    const assistantId = activeAssistantIdRef.current
    if (assistantId) {
      updateAssistantDraft(assistantId, (message) => ({
        ...message,
        isStreaming: false,
      }))
    }
    activeAssistantIdRef.current = null
    pendingBufferRef.current = ''
    streamFinishedRef.current = false
    setIsStreaming(false)
    setIsError(false)
    const resolve = resolveRef.current
    resolveRef.current = null
    rejectRef.current = null
    resolve?.()
  }

  const startTypingLoop = () => {
    if (typingTimerRef.current !== null) {
      return
    }

    typingTimerRef.current = window.setInterval(() => {
      const assistantId = activeAssistantIdRef.current
      if (!assistantId) {
        stopTypingLoop()
        return
      }

      if (!pendingBufferRef.current) {
        if (streamFinishedRef.current) {
          finalizeStreamingMessage()
        }
        return
      }

      const buffer = pendingBufferRef.current
      const takeCount = buffer.length > 40 ? 5 : buffer.length > 12 ? 3 : 1
      const nextSlice = buffer.slice(0, takeCount)
      pendingBufferRef.current = buffer.slice(takeCount)

      updateAssistantDraft(assistantId, (message) => ({
        ...message,
        content: `${message.content}${nextSlice}`,
      }))
    }, 24)
  }

  useEffect(() => {
    return () => {
      stopTypingLoop()
    }
  }, [])

  const sendMessage = async (message: string) => {
    setIsStreaming(true)
    setIsError(false)
    pendingBufferRef.current = ''
    streamFinishedRef.current = false

    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    }
    const assistantId = generateId()
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      references: [],
      citationSection: [],
      sentenceCitations: [],
      agentTrace: null,
      timeline: [],
      isStreaming: true,
    }
    activeAssistantIdRef.current = assistantId
    updateMessages((messages) => [...messages, userMessage, assistantMessage])

    return new Promise<void>((resolve, reject) => {
      resolveRef.current = resolve
      rejectRef.current = reject
      sendChatMessageStream(
        message,
        (chunk) => {
          pendingBufferRef.current += chunk
          startTypingLoop()
        },
        (refs) => {
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            references: refs,
          }))
        },
        (citationSection) => {
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            citationSection,
          }))
        },
        (sentenceCitations) => {
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            sentenceCitations,
          }))
        },
        (timelineEvent) => {
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            timeline: upsertTimelineEvent(draft.timeline ?? [], timelineEvent),
          }))
        },
        (trace) => {
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            agentTrace: trace,
          }))
        },
        (fullContent) => {
          if (fullContent && !pendingBufferRef.current) {
            updateAssistantDraft(assistantId, (draft) => ({
              ...draft,
              content: draft.content || fullContent,
            }))
          }
          streamFinishedRef.current = true
          if (!pendingBufferRef.current) {
            finalizeStreamingMessage()
          }
        },
        (error) => {
          stopTypingLoop()
          setIsStreaming(false)
          setIsError(true)
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            isStreaming: false,
            content: draft.content || `错误: ${error.message}`,
          }))
          showApiErrorToast(error)
          activeAssistantIdRef.current = null
          pendingBufferRef.current = ''
          streamFinishedRef.current = false
          resolveRef.current = null
          const rejectFn = rejectRef.current
          rejectRef.current = null
          rejectFn?.(new Error(error.message))
        }
      )
    })
  }

  return {
    mutateAsync: sendMessage,
    isPending: isStreaming,
    isError,
  }
}

export function useClearChatMessages() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: clearChatMessages,
    onSuccess: () => queryClient.setQueryData(['chat-messages'], []),
  })
}
