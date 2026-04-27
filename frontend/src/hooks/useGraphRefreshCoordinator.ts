import { useQueryClient } from '@tanstack/react-query'
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

import { createGraphRefreshTracker } from './graphRefreshTracker'
import { useMemories } from './useMemories'

type GraphRefreshCoordinatorContextValue = {
  trackMemory: (memoryId: string) => void
}

const GraphRefreshCoordinatorContext = createContext<GraphRefreshCoordinatorContextValue | null>(null)

function consumeTrackedMemoryUpdates({
  trackedIds,
  memories,
}: {
  trackedIds: Set<string>
  memories: Array<{ id: string; graph_status?: string | null }>
}) {
  const tracker = createGraphRefreshTracker(trackedIds)

  return tracker.consume(memories)
}

export function GraphRefreshCoordinatorProvider({ children }: PropsWithChildren) {
  const trackedIdsRef = useRef(new Set<string>())
  const [trackedCount, setTrackedCount] = useState(0)

  const trackMemory = useCallback((memoryId: string) => {
    if (!memoryId.trim()) {
      return
    }

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
