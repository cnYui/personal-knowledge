import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, useEffect } from 'react'
import { createRoot, Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./useMemories', () => ({
  useMemories: vi.fn(),
}))

import { useMemories } from './useMemories'

import {
  GraphRefreshCoordinatorProvider,
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

  it('空字符串或全空白 memory id 不会启用 memories 查询', async () => {
    const queryClient = new QueryClient()

    useMemoriesMock.mockImplementation(((...args: unknown[]) => {
      const options = args[1] as { enabled?: boolean } | undefined

      return {
        data: options?.enabled ? [{ id: 'mem-1', graph_status: 'added' }] : [],
      }
    }) as never)

    root = createRoot(container)

    await act(async () => {
      root?.render(
        <QueryClientProvider client={queryClient}>
          <GraphRefreshCoordinatorProvider>
            <TrackMemories memoryIds={['', '   ']} />
          </GraphRefreshCoordinatorProvider>
        </QueryClientProvider>,
      )
    })

    await act(async () => {})

    expect(useMemoriesMock.mock.calls).toEqual([[undefined, { enabled: false }]])
  })
})
