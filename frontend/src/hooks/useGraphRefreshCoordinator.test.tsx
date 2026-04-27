import { describe, expect, it } from 'vitest'

import { createGraphRefreshTracker } from './useGraphRefreshCoordinator'

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

    expect(result.shouldRefreshGraph).toBe(true)
    expect(result.resolvedIds).toEqual(['mem-1'])
  })

  it('重复注册同一 memory 时 failed 不刷新 graph 且 resolvedIds 不重复', () => {
    const tracker = createGraphRefreshTracker()

    tracker.track('mem-1')
    tracker.track('mem-1')

    const result = tracker.consume([
      { id: 'mem-1', graph_status: 'failed' },
    ] satisfies MemoryGraphState[])

    expect(result.shouldRefreshGraph).toBe(false)
    expect(result.resolvedIds).toEqual(['mem-1'])
  })
})
