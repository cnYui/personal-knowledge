import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, useEffect } from 'react'
import { createRoot, Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./useMemories', () => ({
  useMemories: vi.fn(),
}))

import { useMemories } from './useMemories'

import {
  createGraphRefreshTracker,
  GraphRefreshCoordinatorProvider,
  handleTrackedMemoryUpdates,
  useGraphRefreshCoordinator,
} from './useGraphRefreshCoordinator'

type MemoryGraphState = {
  id: string
  graph_status?: string | null
}

const useMemoriesMock = vi.mocked(useMemories)

function TrackMemoryOnMount({ memoryId }: { memoryId: string }) {
  const { trackMemory } = useGraphRefreshCoordinator()

  useEffect(() => {
    trackMemory(memoryId)
  }, [memoryId, trackMemory])

  return null
}

function TrackMemories({ memoryIds }: { memoryIds: string[] }) {
  const { trackMemory } = useGraphRefreshCoordinator()

  useEffect(() => {
    memoryIds.forEach((memoryId) => {
      trackMemory(memoryId)
    })
  }, [memoryIds, trackMemory])

  return null
}

describe('GraphRefreshCoordinatorProvider', () => {
  let container: HTMLDivElement
  let root: Root | null = null

  beforeEach(() => {
    globalThis.IS_REACT_ACT_ENVIRONMENT = true
    container = document.createElement('div')
    document.body.appendChild(container)
    useMemoriesMock.mockReset()
  })

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root?.unmount()
      })
      root = null
    }

    container.remove()
    delete globalThis.IS_REACT_ACT_ENVIRONMENT
  })

  it('只在存在 tracked memory 时启用 memories 查询，并在消费完成后停止', async () => {
    const queryClient = new QueryClient()
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')
    const memories: MemoryGraphState[] = [{ id: 'mem-1', graph_status: 'added' }]

    useMemoriesMock.mockImplementation(((...args: unknown[]) => {
      const options = args[1] as { enabled?: boolean } | undefined

      return {
        data: options?.enabled ? memories : [],
      }
    }) as never)

    root = createRoot(container)

    await act(async () => {
      root?.render(
        <QueryClientProvider client={queryClient}>
          <GraphRefreshCoordinatorProvider>
            <TrackMemoryOnMount memoryId="mem-1" />
          </GraphRefreshCoordinatorProvider>
        </QueryClientProvider>,
      )
    })

    await act(async () => {})

    expect(useMemoriesMock.mock.calls[0]).toEqual([undefined, { enabled: false }])
    expect(useMemoriesMock.mock.calls).toContainEqual([undefined, { enabled: true }])
    expect(useMemoriesMock.mock.calls.at(-1)).toEqual([undefined, { enabled: false }])
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['graph-data'] })
  })

  it('invalidateQueries 挂起期间新增 tracked memory 不会丢失，轮询不会提前关闭', async () => {
    const queryClient = new QueryClient()
    let resolveInvalidate: (() => void) | null = null
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries').mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveInvalidate = resolve
        }) as ReturnType<QueryClient['invalidateQueries']>,
    )
    let currentMemories: MemoryGraphState[] = [{ id: 'mem-1', graph_status: 'added' }]

    useMemoriesMock.mockImplementation(((...args: unknown[]) => {
      const options = args[1] as { enabled?: boolean } | undefined

      return {
        data: options?.enabled ? currentMemories : [],
      }
    }) as never)

    root = createRoot(container)

    await act(async () => {
      root?.render(
        <QueryClientProvider client={queryClient}>
          <GraphRefreshCoordinatorProvider>
            <TrackMemories memoryIds={['mem-1']} />
          </GraphRefreshCoordinatorProvider>
        </QueryClientProvider>,
      )
    })

    expect(invalidateQueries).toHaveBeenCalledTimes(1)

    currentMemories = [{ id: 'mem-2', graph_status: 'pending' }]

    await act(async () => {
      root?.render(
        <QueryClientProvider client={queryClient}>
          <GraphRefreshCoordinatorProvider>
            <TrackMemories memoryIds={['mem-1', 'mem-2']} />
          </GraphRefreshCoordinatorProvider>
        </QueryClientProvider>,
      )
    })

    await act(async () => {
      resolveInvalidate?.()
      await Promise.resolve()
    })

    expect(useMemoriesMock.mock.calls.at(-1)).toEqual([undefined, { enabled: true }])

    currentMemories = [{ id: 'mem-2', graph_status: 'added' }]

    await act(async () => {
      root?.render(
        <QueryClientProvider client={queryClient}>
          <GraphRefreshCoordinatorProvider>
            <TrackMemories memoryIds={['mem-1', 'mem-2']} />
          </GraphRefreshCoordinatorProvider>
        </QueryClientProvider>,
      )
    })

    expect(invalidateQueries).toHaveBeenCalledTimes(2)
  })
})

describe('createGraphRefreshTracker', () => {
  it('pending 进入 added 时返回刷新标记并清理对应 memory', () => {
    const tracker = createGraphRefreshTracker()

    tracker.track('mem-1')

    const result = tracker.consume([
      { id: 'mem-1', graph_status: 'added' },
    ] satisfies MemoryGraphState[])
    const afterResolvedResult = tracker.consume([
      { id: 'mem-1', graph_status: 'added' },
    ] satisfies MemoryGraphState[])

    expect(result.shouldRefreshGraph).toBe(true)
    expect(result.resolvedIds).toEqual(['mem-1'])
    expect(afterResolvedResult.shouldRefreshGraph).toBe(false)
    expect(afterResolvedResult.resolvedIds).toEqual([])
  })

  it('重复注册同一 memory 时 failed 不刷新 graph 且 resolvedIds 不重复', () => {
    const tracker = createGraphRefreshTracker()

    tracker.track('mem-1')
    tracker.track('mem-1')

    const result = tracker.consume([
      { id: 'mem-1', graph_status: 'failed' },
    ] satisfies MemoryGraphState[])
    const afterResolvedResult = tracker.consume([
      { id: 'mem-1', graph_status: 'failed' },
    ] satisfies MemoryGraphState[])

    expect(result.shouldRefreshGraph).toBe(false)
    expect(result.resolvedIds).toEqual(['mem-1'])
    expect(afterResolvedResult.shouldRefreshGraph).toBe(false)
    expect(afterResolvedResult.resolvedIds).toEqual([])
  })

  it('pending 状态不会触发刷新且继续保留待处理 memory', () => {
    const tracker = createGraphRefreshTracker()

    tracker.track('mem-1')

    const pendingResult = tracker.consume([
      { id: 'mem-1', graph_status: 'pending' },
    ] satisfies MemoryGraphState[])
    const resolvedResult = tracker.consume([
      { id: 'mem-1', graph_status: 'added' },
    ] satisfies MemoryGraphState[])

    expect(pendingResult.shouldRefreshGraph).toBe(false)
    expect(pendingResult.resolvedIds).toEqual([])
    expect(resolvedResult.shouldRefreshGraph).toBe(true)
    expect(resolvedResult.resolvedIds).toEqual(['mem-1'])
  })

  it('同批 mixed 状态只消费终态 memory 并保留 pending', () => {
    const tracker = createGraphRefreshTracker()

    tracker.track('mem-1')
    tracker.track('mem-2')
    tracker.track('mem-3')

    const mixedResult = tracker.consume([
      { id: 'mem-1', graph_status: 'added' },
      { id: 'mem-2', graph_status: 'pending' },
      { id: 'mem-3', graph_status: 'failed' },
    ] satisfies MemoryGraphState[])
    const pendingFollowUpResult = tracker.consume([
      { id: 'mem-2', graph_status: 'added' },
    ] satisfies MemoryGraphState[])

    expect(mixedResult.shouldRefreshGraph).toBe(true)
    expect(mixedResult.resolvedIds).toEqual(['mem-1', 'mem-3'])
    expect(pendingFollowUpResult.shouldRefreshGraph).toBe(true)
    expect(pendingFollowUpResult.resolvedIds).toEqual(['mem-2'])
  })
})

describe('handleTrackedMemoryUpdates', () => {
  it('tracked memory 进入 added 时触发 graph-data 失效', async () => {
    const queryClient = new QueryClient()
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')

    await handleTrackedMemoryUpdates({
      queryClient,
      trackedIds: new Set(['mem-1']),
      memories: [{ id: 'mem-1', graph_status: 'added' }],
    })

    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['graph-data'] })
  })

  it('pending 不触发 graph-data 刷新', async () => {
    const queryClient = new QueryClient()
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')

    const result = await handleTrackedMemoryUpdates({
      queryClient,
      trackedIds: new Set(['mem-1']),
      memories: [{ id: 'mem-1', graph_status: 'pending' }],
    })

    expect(result.shouldRefreshGraph).toBe(false)
    expect(invalidateQueries).not.toHaveBeenCalled()
  })

  it('没有 tracked memory 时不会触发 graph-data 刷新逻辑', async () => {
    const queryClient = new QueryClient()
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')

    const result = await handleTrackedMemoryUpdates({
      queryClient,
      trackedIds: new Set(),
      memories: [{ id: 'mem-1', graph_status: 'added' }],
    })

    expect(result.shouldRefreshGraph).toBe(false)
    expect(result.resolvedIds).toEqual([])
    expect(invalidateQueries).not.toHaveBeenCalled()
  })
})
