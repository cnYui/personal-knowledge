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
import {
  ChatContentBlock,
  ChatMessage,
  ChatTimelineEvent,
  ChatToolResultEvent,
  ChatToolUseEvent,
} from '../types/chat'

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

  const sortContentBlocks = (blocks: ChatContentBlock[]) =>
    [...blocks].sort((a, b) => {
      if (a.order !== b.order) return a.order - b.order
      const aKey = 'id' in a ? a.id : ''
      const bKey = 'id' in b ? b.id : ''
      return `${a.type}:${aKey}`.localeCompare(`${b.type}:${bKey}`)
    })

  const appendMarkdownBlock = (
    blocks: ChatContentBlock[] | undefined,
    chunk: string
  ): ChatContentBlock[] => {
    const currentBlocks = blocks ?? []
    const lastBlock = currentBlocks[currentBlocks.length - 1]

    if (lastBlock?.type === 'markdown') {
      return [
        ...currentBlocks.slice(0, -1),
        {
          ...lastBlock,
          text: `${lastBlock.text}${chunk}`,
        },
      ]
    }

    return [
      ...currentBlocks,
      {
        type: 'markdown',
        id: generateId(),
        text: chunk,
        order: Date.now(),
      },
    ]
  }

  const ensureMarkdownContentBlocks = (
    blocks: ChatContentBlock[] | undefined,
    fullContent: string
  ): ChatContentBlock[] => {
    const currentBlocks = blocks ?? []
    if (!fullContent) {
      return currentBlocks
    }
    if (currentBlocks.some((block) => block.type === 'markdown')) {
      return currentBlocks
    }
    return appendMarkdownBlock(currentBlocks, fullContent)
  }

  const upsertToolUseBlock = (
    blocks: ChatContentBlock[] | undefined,
    event: ChatToolUseEvent
  ): ChatContentBlock[] => {
    const nextBlocks = (blocks ?? []).filter(
      (block) => !(block.type === 'tool_use' && block.id === event.id)
    )
    nextBlocks.push({
      type: 'tool_use',
      id: event.id,
      name: event.name,
      input: event.input,
      title: event.title,
      order: event.order,
    })
    return sortContentBlocks(nextBlocks)
  }

  const upsertToolResultBlock = (
    blocks: ChatContentBlock[] | undefined,
    event: ChatToolResultEvent
  ): ChatContentBlock[] => {
    const nextBlocks = (blocks ?? []).filter(
      (block) => !(block.type === 'tool_result' && block.tool_use_id === event.tool_use_id)
    )
    nextBlocks.push({
      type: 'tool_result',
      id: `${event.tool_use_id}:result`,
      tool_use_id: event.tool_use_id,
      status: event.status,
      output: event.output,
      is_error: event.is_error,
      order: event.order,
    })
    return sortContentBlocks(nextBlocks)
  }

  const finalizeAssistantErrorContent = (content: string, error: ApiErrorPayload) => {
    const normalized = `错误: ${error.message}`
    const trimmed = content.trim()
    if (!trimmed) {
      return normalized
    }
    if (trimmed.includes(error.message)) {
      return content
    }
    return `${content}\n\n${normalized}`
  }

  const upsertTimelineEvent = (events: ChatTimelineEvent[], nextEvent: ChatTimelineEvent): ChatTimelineEvent[] => {
    const filtered = events.filter((event) => event.id !== nextEvent.id)
    filtered.push(nextEvent)
    return filtered.sort((a, b) => {
      if (a.order !== b.order) return a.order - b.order
      if (a.id !== b.id) return a.id.localeCompare(b.id)
      return a.status.localeCompare(b.status)
    })
  }

  const finalizeTimelineEvents = (
    events: ChatTimelineEvent[] | undefined,
    finalStatus: 'done' | 'error'
  ): ChatTimelineEvent[] => {
    if (!events?.length) {
      return []
    }

    return events.map((event) =>
      event.status === 'started'
        ? {
            ...event,
            status: finalStatus,
          }
        : event
    )
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
        timeline: finalizeTimelineEvents(message.timeline, 'done'),
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
        contentBlocks: appendMarkdownBlock(message.contentBlocks, nextSlice),
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
      contentBlocks: [],
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
        (toolUse) => {
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            contentBlocks: upsertToolUseBlock(draft.contentBlocks, toolUse),
          }))
        },
        (toolResult) => {
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            contentBlocks: upsertToolResultBlock(draft.contentBlocks, toolResult),
          }))
        },
        (fullContent) => {
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            content: fullContent || draft.content,
            contentBlocks: ensureMarkdownContentBlocks(draft.contentBlocks, fullContent),
          }))
          streamFinishedRef.current = true
          finalizeStreamingMessage()
        },
        (error) => {
          stopTypingLoop()
          setIsStreaming(false)
          setIsError(true)
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            isStreaming: false,
            content: finalizeAssistantErrorContent(draft.content, error),
            timeline: finalizeTimelineEvents(draft.timeline, 'error'),
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
