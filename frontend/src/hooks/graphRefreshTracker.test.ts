import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

import { createGraphRefreshTracker, handleTrackedMemoryUpdates } from './graphRefreshTracker'

type MemoryGraphState = {
  id: string
  graph_status?: string | null
}

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
