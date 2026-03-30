import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { fetchPrompt, resetPrompt, updatePrompt } from '../services/promptApi'
import { PromptConfigUpdate } from '../types/prompt'

export function usePrompt(key: string) {
  return useQuery({
    queryKey: ['prompt', key],
    queryFn: () => fetchPrompt(key),
    staleTime: 60000, // 1 minute
  })
}

export function useUpdatePrompt(key: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PromptConfigUpdate) => updatePrompt(key, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt', key] })
    },
  })
}

export function useResetPrompt(key: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => resetPrompt(key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt', key] })
    },
  })
}
