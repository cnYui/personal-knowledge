import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { clearChatMessages, fetchChatMessages, sendChatMessage } from '../services/chatApi'

export function useChatMessages() {
  return useQuery({ queryKey: ['chat-messages'], queryFn: fetchChatMessages })
}

export function useSendChatMessage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: sendChatMessage,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chat-messages'] }),
  })
}

export function useClearChatMessages() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: clearChatMessages,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chat-messages'] }),
  })
}
