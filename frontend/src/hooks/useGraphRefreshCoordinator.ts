import { QueryClient, useQueryClient } from '@tanstack/react-query'
import { createContext, createElement, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef } from 'react'

import { useMemories } from './useMemories'

type MemoryGraphState = {
  id: string
  graph_status?: string | null
}

type GraphRefreshConsumeResult = {
  shouldRefreshGraph: boolean
  resolvedIds: string[]
}

type GraphRefreshCoordinatorContextValue = {
  trackMemory: (memoryId: string) => void
}

const GraphRefreshCoordinatorContext = createContext<GraphRefreshCoordinatorContextValue | null>(null)

export function createGraphRefreshTracker(pendingIds: Set<string> = new Set<string>()) {
  const trackedPendingIds = pendingIds

  return {
    track(memoryId: string) {
      trackedPendingIds.add(memoryId)
    },
    consume(memories: MemoryGraphState[]): GraphRefreshConsumeResult {
      const resolvedIds: string[] = []
      let shouldRefreshGraph = false

      for (const memory of memories) {
        if (!trackedPendingIds.has(memory.id)) {
          continue
        }

        if (memory.graph_status === 'added') {
          shouldRefreshGraph = true
          trackedPendingIds.delete(memory.id)
          resolvedIds.push(memory.id)
          continue
        }

        if (memory.graph_status === 'failed') {
          trackedPendingIds.delete(memory.id)
          resolvedIds.push(memory.id)
        }
      }

      return {
        shouldRefreshGraph,
        resolvedIds,
      }
    },
  }
}

export async function handleTrackedMemoryUpdates({
  queryClient,
  trackedIds,
  memories,
}: {
  queryClient: QueryClient
  trackedIds: Set<string>
  memories: MemoryGraphState[]
}) {
  const tracker = createGraphRefreshTracker(trackedIds)
  const result = tracker.consume(memories)

  if (result.shouldRefreshGraph) {
    await queryClient.invalidateQueries({ queryKey: ['graph-data'] })
  }

  return result
}

export function GraphRefreshCoordinatorProvider({ children }: PropsWithChildren) {
  const queryClient = useQueryClient()
  const trackedIdsRef = useRef(new Set<string>())
  const { data: memories = [] } = useMemories()

  const trackMemory = useCallback((memoryId: string) => {
    trackedIdsRef.current.add(memoryId)
  }, [])

  useEffect(() => {
    if (trackedIdsRef.current.size === 0 || memories.length === 0) {
      return
    }

    void handleTrackedMemoryUpdates({
      queryClient,
      trackedIds: trackedIdsRef.current,
      memories,
    })
  }, [memories, queryClient])

  const value = useMemo<GraphRefreshCoordinatorContextValue>(
    () => ({
      trackMemory,
    }),
    [trackMemory],
  )

  return createElement(GraphRefreshCoordinatorContext.Provider, { value }, children)
}

export function useGraphRefreshCoordinator() {
  const context = useContext(GraphRefreshCoordinatorContext)

  if (!context) {
    throw new Error('useGraphRefreshCoordinator must be used within GraphRefreshCoordinatorProvider')
  }

  return context
}
