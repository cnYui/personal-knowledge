type MemoryGraphState = {
  id: string
  graph_status?: string | null
}

type GraphRefreshConsumeResult = {
  shouldRefreshGraph: boolean
  resolvedIds: string[]
}

export function createGraphRefreshTracker() {
  const pendingIds = new Set<string>()

  return {
    track(memoryId: string) {
      pendingIds.add(memoryId)
    },
    consume(memories: MemoryGraphState[]): GraphRefreshConsumeResult {
      const resolvedIds: string[] = []
      let shouldRefreshGraph = false

      for (const memory of memories) {
        if (!pendingIds.has(memory.id)) {
          continue
        }

        if (memory.graph_status === 'added') {
          shouldRefreshGraph = true
          pendingIds.delete(memory.id)
          resolvedIds.push(memory.id)
          continue
        }

        if (memory.graph_status === 'failed') {
          pendingIds.delete(memory.id)
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
