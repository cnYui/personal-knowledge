import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  addMemoryToKnowledgeGraph,
  deleteMemory,
  listMemories,
  updateMemory,
} from '../services/memoryApi'

const MEMORY_POLLING_INTERVAL_MS = Number(import.meta.env.VITE_MEMORIES_POLLING_MS ?? 5000)

export function useMemories(keyword?: string) {
  return useQuery({
    queryKey: ['memories', keyword],
    queryFn: () => listMemories({ keyword }),
    refetchInterval: MEMORY_POLLING_INTERVAL_MS,
  })
}

export function useUpdateMemory() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: updateMemory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['memories'] }),
  })
}

export function useAddMemoryToKnowledgeGraph() {
  return useMutation({
    mutationFn: addMemoryToKnowledgeGraph,
  })
}

export function useDeleteMemory() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deleteMemory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['memories'] }),
  })
}
