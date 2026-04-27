import { QueryClient } from '@tanstack/react-query'

type MemoryGraphState = {
  id: string
  graph_status?: string | null
}

type GraphRefreshConsumeResult = {
  shouldRefreshGraph: boolean
  resolvedIds: string[]
  remainingTrackedCount: number
}

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
