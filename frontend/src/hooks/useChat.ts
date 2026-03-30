import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { clearChatMessages, fetchChatMessages, sendChatMessageStream } from '../services/chatApi'
import { AgentTrace, ChatReference } from '../types/chat'

export function useChatMessages() {
  return useQuery({ 
    queryKey: ['chat-messages'], 
    queryFn: fetchChatMessages, 
    // 移除自动刷新，避免在流式输出时重复显示消息
    refetchInterval: false,
  })
}

export function useSendChatMessage() {
  const queryClient = useQueryClient()
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [references, setReferences] = useState<ChatReference[]>([])
  const [agentTrace, setAgentTrace] = useState<AgentTrace | null>(null)

  const sendMessage = async (message: string) => {
    setIsStreaming(true)
    setStreamingContent('')
    setReferences([])
    setAgentTrace(null)

    return new Promise<void>((resolve, reject) => {
      sendChatMessageStream(
        message,
        (chunk) => {
          // 每次收到新内容
          setStreamingContent((prev) => prev + chunk)
        },
        (refs) => {
          // 收到引用
          setReferences(refs)
        },
        (trace) => {
          setAgentTrace(trace)
        },
        () => {
          // 完成
          setIsStreaming(false)
          setStreamingContent('')
          setReferences([])
          setAgentTrace(null)
          queryClient.invalidateQueries({ queryKey: ['chat-messages'] })
          resolve()
        },
        (error) => {
          // 错误
          setIsStreaming(false)
          setStreamingContent('')
          setReferences([])
          setAgentTrace(null)
          queryClient.invalidateQueries({ queryKey: ['chat-messages'] })
          reject(new Error(error))
        }
      )
    })
  }

  return {
    mutateAsync: sendMessage,
    isPending: isStreaming,
    isError: false,
    streamingContent,
    references,
    agentTrace,
  }
}

export function useClearChatMessages() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: clearChatMessages,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chat-messages'] }),
  })
}
