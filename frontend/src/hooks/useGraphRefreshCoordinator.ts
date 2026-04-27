import { QueryClient, useQueryClient } from '@tanstack/react-query'
import {
  createContext,
  createElement,
  MutableRefObject,
  PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import { useMemories } from './useMemories'

type MemoryGraphState = {
  id: string
  graph_status?: string | null
}

type GraphRefreshConsumeResult = {
  shouldRefreshGraph: boolean
  resolvedIds: string[]
  remainingTrackedCount: number
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
        remainingTrackedCount: trackedPendingIds.size,
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

export function createTrackMemoryHandler<TMemory extends { id: string }>(
  trackMemory: (memoryId: string) => void,
  addToGraph: (memory: TMemory) => Promise<void>,
) {
  return async (memory: TMemory) => {
    await addToGraph(memory)
    trackMemory(memory.id)
  }
}

function consumeTrackedMemoryUpdates({
  trackedIds,
  memories,
}: {
  trackedIds: Set<string>
  memories: MemoryGraphState[]
}) {
  const tracker = createGraphRefreshTracker(trackedIds)

  return tracker.consume(memories)
}

export function GraphRefreshCoordinatorProvider({ children }: PropsWithChildren) {
  const trackedIdsRef = useRef(new Set<string>())
  const [trackedCount, setTrackedCount] = useState(0)

  const trackMemory = useCallback((memoryId: string) => {
    if (trackedIdsRef.current.has(memoryId)) {
      return
    }

    trackedIdsRef.current.add(memoryId)
    setTrackedCount(trackedIdsRef.current.size)
  }, [])

  const value = useMemo<GraphRefreshCoordinatorContextValue>(
    () => ({
      trackMemory,
    }),
    [trackMemory],
  )

  return createElement(
    GraphRefreshCoordinatorContext.Provider,
    { value },
    children,
    createElement(GraphRefreshCoordinatorEffect, {
      trackedCount,
      trackedIdsRef,
      onTrackedCountChange: setTrackedCount,
    }),
  )
}

export function useGraphRefreshCoordinator() {
  const context = useContext(GraphRefreshCoordinatorContext)

  if (!context) {
    throw new Error('useGraphRefreshCoordinator must be used within GraphRefreshCoordinatorProvider')
  }

  return context
}

function GraphRefreshCoordinatorEffect({
  trackedCount,
  trackedIdsRef,
  onTrackedCountChange,
}: {
  trackedCount: number
  trackedIdsRef: MutableRefObject<Set<string>>
  onTrackedCountChange: (count: number) => void
}) {
  const queryClient = useQueryClient()
  const hasTrackedMemories = trackedCount > 0
  const { data: memories = [] } = useMemories(undefined, { enabled: hasTrackedMemories })

  useEffect(() => {
    if (!hasTrackedMemories || memories.length === 0) {
      return
    }

    const result = consumeTrackedMemoryUpdates({
      trackedIds: trackedIdsRef.current,
      memories,
    })

    onTrackedCountChange(trackedIdsRef.current.size)

    if (result.shouldRefreshGraph) {
      void queryClient.invalidateQueries({ queryKey: ['graph-data'] })
    }
  }, [hasTrackedMemories, memories, onTrackedCountChange, queryClient, trackedIdsRef])

  return null
}
