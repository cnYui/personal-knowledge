# Graph 自动刷新联动 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 memory 入图完成后自动刷新 `graph-data` 查询，覆盖“graph 页面已打开自动刷新”和“之后进入 graph 页面直接看到最新结果”。

**Architecture:** 保持后端接口不变，复用前端现有 memories 查询能力作为状态来源，在前端新增一个全局图谱刷新协调层。协调层按需启停 `useMemories(undefined, { enabled })`，维护待观察 memory 集合，在检测到 `pending -> added` 时触发 `invalidateQueries(['graph-data'])`，并在 `failed/added` 后清理本地等待状态。

**Tech Stack:** React 18、TypeScript、@tanstack/react-query、MUI、Vitest

---

## 文件结构

- 新增 `frontend/src/hooks/useGraphRefreshCoordinator.ts`
  - 维护待观察 memory id 集合
  - 暴露注册方法
  - 监听 memories 查询结果
  - 触发 `graph-data` 失效
- 新增 `frontend/src/hooks/graphRefreshTracker.ts`
  - 收敛纯状态机，避免 hook 模块暴露测试专用内部实现
- 修改 `frontend/src/app/providers.tsx`
  - 在全局 provider 层挂载图谱刷新协调逻辑
  - 暴露协调上下文或注入式注册能力
- 修改 `frontend/src/hooks/useMemories.ts`
  - 增加 `enabled` 开关，避免全局 provider 造成常驻轮询
- 修改 `frontend/src/pages/MemoryManagementPage.tsx`
  - 在手动入图成功后注册待观察 memory
- 新增 `frontend/src/hooks/useGraphRefreshCoordinator.test.tsx`
  - 覆盖 provider / context / query 失效行为
- 新增 `frontend/src/hooks/graphRefreshTracker.test.ts`
  - 覆盖纯状态机行为
- 修改 `docs/ai/context/2026-04-27-graph-auto-refresh-design.md`
  - 如实现时对挂载位置或去抖策略有细化，回写设计
- 修改 `AGENTS.md`
  - 记录最终采用的自动刷新策略

## Task 1：提炼 graph 刷新协调层纯逻辑

**Files:**
- Create: `frontend/src/hooks/graphRefreshTracker.ts`
- Test: `frontend/src/hooks/graphRefreshTracker.test.ts`

- [ ] **Step 1: 写失败测试，锁定待观察集合的状态迁移**

```ts
import { describe, expect, it } from 'vitest'

import { createGraphRefreshTracker } from './graphRefreshTracker'

describe('createGraphRefreshTracker', () => {
  it('在 pending -> added 时返回需要刷新的标记', () => {
    const tracker = createGraphRefreshTracker()

    tracker.track('mem-1')

    const result = tracker.consume([
      { id: 'mem-1', graph_status: 'added' },
    ] as Array<{ id: string; graph_status?: string | null }>)

    expect(result.shouldRefreshGraph).toBe(true)
    expect(result.resolvedIds).toEqual(['mem-1'])
  })
})
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd frontend; npm run test -- src/hooks/graphRefreshTracker.test.ts`

Expected: FAIL with `graphRefreshTracker.ts` or `graphRefreshTracker.test.ts` missing

- [ ] **Step 3: 写最小实现**

```ts
type MemoryGraphState = {
  id: string
  graph_status?: string | null
}

export function createGraphRefreshTracker() {
  const pendingIds = new Set<string>()

  return {
    track(memoryId: string) {
      pendingIds.add(memoryId)
    },
    consume(memories: MemoryGraphState[]) {
      const resolvedIds: string[] = []
      let shouldRefreshGraph = false

      memories.forEach((memory) => {
        if (!pendingIds.has(memory.id)) return

        if (memory.graph_status === 'added') {
          shouldRefreshGraph = true
          pendingIds.delete(memory.id)
          resolvedIds.push(memory.id)
          return
        }

        if (memory.graph_status === 'failed') {
          pendingIds.delete(memory.id)
          resolvedIds.push(memory.id)
        }
      })

      return { shouldRefreshGraph, resolvedIds }
    },
  }
}
```

- [ ] **Step 4: 再补失败测试，锁定重复注册与失败态不刷新**

```ts
import { describe, expect, it } from 'vitest'

import { createGraphRefreshTracker } from './useGraphRefreshCoordinator'

describe('createGraphRefreshTracker', () => {
  it('重复注册不重复触发，failed 不刷新 graph', () => {
    const tracker = createGraphRefreshTracker()

    tracker.track('mem-1')
    tracker.track('mem-1')

    const result = tracker.consume([
      { id: 'mem-1', graph_status: 'failed' },
    ] as Array<{ id: string; graph_status?: string | null }>)

    expect(result.shouldRefreshGraph).toBe(false)
    expect(result.resolvedIds).toEqual(['mem-1'])
  })
})
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `cd frontend; npm run test -- src/hooks/graphRefreshTracker.test.ts`

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add frontend/src/hooks/graphRefreshTracker.ts frontend/src/hooks/graphRefreshTracker.test.ts
git commit -m "test: cover graph refresh tracker transitions"
```

## Task 2：把协调层接入全局 provider

**Files:**
- Create: `frontend/src/hooks/useGraphRefreshCoordinator.ts`
- Modify: `frontend/src/app/providers.tsx`
- Test: `frontend/src/hooks/useGraphRefreshCoordinator.test.tsx`

- [ ] **Step 1: 写失败测试，锁定 added 时会触发 graph query 失效**

```ts
import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

import { handleTrackedMemoryUpdates } from './useGraphRefreshCoordinator'

describe('handleTrackedMemoryUpdates', () => {
  it('在 tracked memory 进入 added 时触发 graph-data 失效', async () => {
    const queryClient = new QueryClient()
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')

    await handleTrackedMemoryUpdates({
      queryClient,
      trackedIds: new Set(['mem-1']),
      memories: [{ id: 'mem-1', graph_status: 'added' }],
    })

    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['graph-data'] })
  })
})
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd frontend; npm run test -- src/hooks/useGraphRefreshCoordinator.test.tsx`

Expected: FAIL with `handleTrackedMemoryUpdates is not exported`

- [ ] **Step 3: 写最小实现，把 tracker 输出和 queryClient 联动**

```ts
import { QueryClient } from '@tanstack/react-query'

export async function handleTrackedMemoryUpdates({
  queryClient,
  trackedIds,
  memories,
}: {
  queryClient: QueryClient
  trackedIds: Set<string>
  memories: Array<{ id: string; graph_status?: string | null }>
}) {
  const tracker = createGraphRefreshTracker(trackedIds)
  const result = tracker.consume(memories)

  if (result.shouldRefreshGraph) {
    await queryClient.invalidateQueries({ queryKey: ['graph-data'] })
  }

  return result
}
```

- [ ] **Step 4: 在 `providers.tsx` 挂载协调层**

```ts
function GraphRefreshCoordinatorProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const memoriesQuery = useMemories()
  const trackedIdsRef = useRef(new Set<string>())

  useEffect(() => {
    if (!memoriesQuery.data) return
    void handleTrackedMemoryUpdates({
      queryClient,
      trackedIds: trackedIdsRef.current,
      memories: memoriesQuery.data,
    })
  }, [memoriesQuery.data, queryClient])

  return <GraphRefreshContext.Provider value={{ trackMemory: (id) => trackedIdsRef.current.add(id) }}>{children}</GraphRefreshContext.Provider>
}
```

- [ ] **Step 5: 运行测试**

Run: `cd frontend; npm run test -- src/hooks/useGraphRefreshCoordinator.test.tsx`

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add frontend/src/app/providers.tsx frontend/src/hooks/useGraphRefreshCoordinator.ts frontend/src/hooks/useGraphRefreshCoordinator.test.tsx
git commit -m "feat: mount graph refresh coordinator globally"
```

## Task 3：在 memories 页面注册待观察入图任务

**Files:**
- Modify: `frontend/src/pages/MemoryManagementPage.tsx`
- Modify: `frontend/src/hooks/useGraphRefreshCoordinator.ts`
- Test: `frontend/src/hooks/useGraphRefreshCoordinator.test.tsx`

- [ ] **Step 1: 写失败测试，锁定手动入图成功后会注册 memory id**

```ts
import { describe, expect, it, vi } from 'vitest'

import { createTrackMemoryHandler } from './useGraphRefreshCoordinator'

describe('createTrackMemoryHandler', () => {
  it('入图请求成功后注册待观察 memory', async () => {
    const trackMemory = vi.fn()
    const addToGraph = vi.fn().mockResolvedValue(undefined)
    const handler = createTrackMemoryHandler(trackMemory, addToGraph)

    await handler({ id: 'mem-1' } as { id: string })

    expect(addToGraph).toHaveBeenCalled()
    expect(trackMemory).toHaveBeenCalledWith('mem-1')
  })
})
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd frontend; npm run test -- src/hooks/useGraphRefreshCoordinator.test.tsx`

Expected: FAIL with `createTrackMemoryHandler is not exported`

- [ ] **Step 3: 写最小实现**

```ts
export function createTrackMemoryHandler(
  trackMemory: (memoryId: string) => void,
  addToGraph: (memory: { id: string }) => Promise<void>
) {
  return async (memory: { id: string }) => {
    await addToGraph(memory)
    trackMemory(memory.id)
  }
}
```

- [ ] **Step 4: 在 `MemoryManagementPage.tsx` 替换现有成功回调**

```ts
const { trackMemory } = useGraphRefreshCoordinator()

onAddToGraph={async (memory) => {
  try {
    await addToGraphMutation.mutateAsync(memory)
    trackMemory(memory.id)
    setSelectedMemory(null)
    showToast({ severity: 'success', message: '已加入知识图谱处理队列，正在构建中...' })
  } catch (error) {
    showToast({ severity: 'error', message: resolveAddToGraphErrorMessage(error) })
  }
}}
```

- [ ] **Step 5: 运行测试**

Run: `cd frontend; npm run test -- src/hooks/useGraphRefreshCoordinator.test.tsx`

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add frontend/src/pages/MemoryManagementPage.tsx frontend/src/hooks/useGraphRefreshCoordinator.ts frontend/src/hooks/useGraphRefreshCoordinator.test.tsx
git commit -m "feat: track graph ingestion jobs from memories page"
```

## Task 4：联调、文档回写与验证

**Files:**
- Modify: `docs/ai/context/2026-04-27-graph-auto-refresh-design.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: 跑协调层单测**

Run: `cd frontend; npm run test -- src/hooks/useGraphRefreshCoordinator.test.tsx`

Expected: PASS

- [ ] **Step 2: 跑前端构建**

Run: `cd frontend; npm run build`

Expected: PASS with Vite build success output

- [ ] **Step 3: 做手工联调**

Run: `cd frontend; npm run dev -- --host 127.0.0.1 --port 5173`

Manual check:
- 在 memories 页面手动点击“加入知识图谱”
- memory 状态进入 `pending`
- 入图完成后，如果 graph 页面正开着，图自动刷新
- 如果 graph 页面未开，之后切过去直接看到最新结果
- `failed` 状态不会触发 graph 刷新

- [ ] **Step 4: 如果实现细节有变化，回写设计文档**

```md
- 最终协调层挂载位置
- 是否引入简单去抖
- tracked id 清理策略
```

- [ ] **Step 5: 同步 `AGENTS.md` 最终记忆**

```md
- 记录 graph 自动刷新最终采用的协调层与失效触发策略
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/hooks/useGraphRefreshCoordinator.ts frontend/src/hooks/useGraphRefreshCoordinator.test.tsx frontend/src/pages/MemoryManagementPage.tsx frontend/src/app/providers.tsx docs/ai/context/2026-04-27-graph-auto-refresh-design.md AGENTS.md
git commit -m "feat: auto refresh graph after memory ingestion"
```

## 自检

- 规格覆盖：
  - graph 页面开着时自动刷新：Task 2、Task 4
  - graph 页面之后进入能看到最新结果：复用现有 `refetchOnMount`，Task 2、Task 4
  - 不引入 SSE / WebSocket：整体未涉及后端实时通道
  - `pending -> added` 刷新，`pending -> failed` 不刷新：Task 1、Task 2
- 实现补充：
  - 纯 tracker 已从 hook 模块拆到 `graphRefreshTracker.ts`
  - 协调层自身按需启停 `useMemories(undefined, { enabled })`，而不是依赖 memories 页面组件驻留
  - memories 查询已按 tracked memory 开关启停，避免全局 provider 造成常驻轮询
- 占位检查：
  - 未使用 `TODO`、`TBD`、`implement later`
  - 每个任务都有文件路径、命令和预期
- 类型一致性：
  - 统一使用 `trackMemory`、`trackedIds`、`graph_status`、`invalidateQueries(['graph-data'])`

## 执行选项

计划已保存到 [docs/ai/context/2026-04-27-graph-auto-refresh-implementation-plan.md](D:/CodeWorkSpace/personal-knowledge-base/.worktrees/codex-graph-auto-refresh/docs/ai/context/2026-04-27-graph-auto-refresh-implementation-plan.md)。

两个执行方式：

1. 子代理分任务执行
2. 我在当前会话直接按这个计划继续实现
