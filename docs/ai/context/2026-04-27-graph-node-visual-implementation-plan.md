# Graph 节点视觉规则实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Graph 页面中的 sigma 节点按连接数做对数放大，并按缩放等级与连接数分位数渐进显示标签，提升大图可读性。

**Architecture:** 保持现有 `sigma + graphology` 渲染链路不变，只调整前端图构建与 reducer 逻辑。节点大小在建图阶段按 `degree` 计算，标签显示在 reducer 阶段结合相机缩放比例、分位数阈值、悬停与选中状态动态决定。

**Tech Stack:** React 18、TypeScript、sigma、graphology、graphology-layout-forceatlas2、Vitest

---

## 文件结构

- 修改 `frontend/src/components/graph/KnowledgeGraphVisualization.tsx`
  - 收敛节点大小计算
  - 增加 `degree` 分位数阈值计算
  - 增加基于相机缩放的标签显示规则
  - 将相机状态变化接入 renderer 刷新
- 可能修改 `frontend/src/types/graph.ts`
  - 仅当需要扩展前端内部类型时处理，默认不改接口出参
- 新增 `frontend/src/components/graph/KnowledgeGraphVisualization.test.tsx`
  - 覆盖权重映射与阈值计算的纯函数行为
- 修改 `docs/ai/context/2026-04-27-graph-node-visual-rules.md`
  - 如实现时需要把默认值微调为更稳的具体数字，回写文档
- 修改 `AGENTS.md`
  - 如最终阈值或公式与当前记忆有微调，回写最新结论

## Task 1：提炼可测试的视觉规则纯函数

**Files:**
- Modify: `frontend/src/components/graph/KnowledgeGraphVisualization.tsx`
- Test: `frontend/src/components/graph/KnowledgeGraphVisualization.test.tsx`

- [ ] **Step 1: 写失败测试，锁定节点大小公式**

```ts
import { describe, expect, it } from 'vitest'

import { computeNodeSize } from './KnowledgeGraphVisualization'

describe('computeNodeSize', () => {
  it('对 degree 使用对数放大并限制最大值', () => {
    expect(computeNodeSize(0)).toBe(5)
    expect(computeNodeSize(1)).toBe(8)
    expect(computeNodeSize(3)).toBe(11)
    expect(computeNodeSize(255)).toBe(18)
  })
})
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd frontend; npm run test -- KnowledgeGraphVisualization.test.tsx`

Expected: FAIL with `computeNodeSize is not exported` or test file missing

- [ ] **Step 3: 在图组件中提炼最小实现**

```ts
const BASE_NODE_SIZE = 5
const NODE_SIZE_SCALE = 3
const MAX_NODE_SIZE = 18

export function computeNodeSize(degree: number) {
  return Math.min(MAX_NODE_SIZE, BASE_NODE_SIZE + Math.log2(Math.max(degree, 0) + 1) * NODE_SIZE_SCALE)
}
```

- [ ] **Step 4: 再补失败测试，锁定分位数阈值行为**

```ts
import { describe, expect, it } from 'vitest'

import { computeDegreeThresholds } from './KnowledgeGraphVisualization'

describe('computeDegreeThresholds', () => {
  it('按前 10% / 25% / 50% 计算 degree 阈值', () => {
    const thresholds = computeDegreeThresholds([20, 12, 9, 8, 6, 5, 4, 2, 1, 1])

    expect(thresholds.top10).toBe(20)
    expect(thresholds.top25).toBe(9)
    expect(thresholds.top50).toBe(6)
  })
})
```

- [ ] **Step 5: 运行测试，确认失败**

Run: `cd frontend; npm run test -- KnowledgeGraphVisualization.test.tsx`

Expected: FAIL with `computeDegreeThresholds is not exported`

- [ ] **Step 6: 写最小实现，补上小样本保护**

```ts
interface DegreeThresholds {
  top10: number
  top25: number
  top50: number
}

function pickThreshold(sortedDegrees: number[], ratio: number) {
  if (sortedDegrees.length === 0) return 0
  const index = Math.min(sortedDegrees.length - 1, Math.max(0, Math.ceil(sortedDegrees.length * ratio) - 1))
  return sortedDegrees[index]
}

export function computeDegreeThresholds(degrees: number[]): DegreeThresholds {
  const sorted = [...degrees].sort((a, b) => b - a)

  return {
    top10: pickThreshold(sorted, 0.1),
    top25: pickThreshold(sorted, 0.25),
    top50: pickThreshold(sorted, 0.5),
  }
}
```

- [ ] **Step 7: 运行测试，确认通过**

Run: `cd frontend; npm run test -- KnowledgeGraphVisualization.test.tsx`

Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add frontend/src/components/graph/KnowledgeGraphVisualization.tsx frontend/src/components/graph/KnowledgeGraphVisualization.test.tsx
git commit -m "test: cover graph node visual rules helpers"
```

## Task 2：把 degree 权重映射接入 sigma 建图

**Files:**
- Modify: `frontend/src/components/graph/KnowledgeGraphVisualization.tsx`
- Test: `frontend/src/components/graph/KnowledgeGraphVisualization.test.tsx`

- [ ] **Step 1: 写失败测试，锁定低频节点与高频节点的尺寸差异**

```ts
import { describe, expect, it } from 'vitest'

import { buildNodeVisualMeta } from './KnowledgeGraphVisualization'

describe('buildNodeVisualMeta', () => {
  it('为每个节点计算 degree 和对应尺寸', () => {
    const result = buildNodeVisualMeta(
      [{ id: 'a' }, { id: 'b' }, { id: 'c' }] as Array<{ id: string }>,
      [
        { source: 'a', target: 'b' },
        { source: 'a', target: 'c' },
      ] as Array<{ source: string; target: string }>
    )

    expect(result.degreeMap.get('a')).toBe(2)
    expect(result.degreeMap.get('b')).toBe(1)
    expect(result.sizeMap.get('a')).toBeGreaterThan(result.sizeMap.get('b')!)
  })
})
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd frontend; npm run test -- KnowledgeGraphVisualization.test.tsx`

Expected: FAIL with `buildNodeVisualMeta is not exported`

- [ ] **Step 3: 写最小实现，并替换 `buildSigmaGraph` 中的硬编码 size**

```ts
export function buildNodeVisualMeta(
  nodes: Array<{ id: string }>,
  edges: Array<{ source: string; target: string }>
) {
  const degreeMap = new Map<string, number>(nodes.map((node) => [node.id, 0]))

  edges.forEach((edge) => {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) ?? 0) + 1)
    degreeMap.set(edge.target, (degreeMap.get(edge.target) ?? 0) + 1)
  })

  const sizeMap = new Map<string, number>()
  degreeMap.forEach((degree, nodeId) => {
    sizeMap.set(nodeId, computeNodeSize(degree))
  })

  return { degreeMap, sizeMap }
}
```

- [ ] **Step 4: 在 `buildSigmaGraph` 中改为使用 `sizeMap`**

```ts
const { degreeMap, sizeMap } = buildNodeVisualMeta(data.nodes, data.edges)

graph.addNode(node.id, {
  ...position,
  size: sizeMap.get(node.id) ?? BASE_NODE_SIZE,
  label: node.label,
  color: ENTITY_COLOR,
  type: 'circle',
  zIndex: degree,
})
```

- [ ] **Step 5: 运行测试**

Run: `cd frontend; npm run test -- KnowledgeGraphVisualization.test.tsx`

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/graph/KnowledgeGraphVisualization.tsx frontend/src/components/graph/KnowledgeGraphVisualization.test.tsx
git commit -m "feat: scale graph nodes by degree"
```

## Task 3：实现按缩放与分位数渐进显示标签

**Files:**
- Modify: `frontend/src/components/graph/KnowledgeGraphVisualization.tsx`
- Test: `frontend/src/components/graph/KnowledgeGraphVisualization.test.tsx`

- [ ] **Step 1: 写失败测试，锁定标签显示判定**

```ts
import { describe, expect, it } from 'vitest'

import { shouldShowNodeLabel } from './KnowledgeGraphVisualization'

describe('shouldShowNodeLabel', () => {
  it('远景只显示 top10 节点标签', () => {
    expect(
      shouldShowNodeLabel({
        degree: 20,
        zoomRatio: 0.8,
        thresholds: { top10: 20, top25: 9, top50: 6 },
        isHovered: false,
        isSelected: false,
        isNeighbor: false,
      })
    ).toBe(true)

    expect(
      shouldShowNodeLabel({
        degree: 9,
        zoomRatio: 0.8,
        thresholds: { top10: 20, top25: 9, top50: 6 },
        isHovered: false,
        isSelected: false,
        isNeighbor: false,
      })
    ).toBe(false)
  })

  it('近景放宽到 top50，hover 与 selected 始终显示', () => {
    expect(
      shouldShowNodeLabel({
        degree: 6,
        zoomRatio: 1.6,
        thresholds: { top10: 20, top25: 9, top50: 6 },
        isHovered: false,
        isSelected: false,
        isNeighbor: false,
      })
    ).toBe(true)

    expect(
      shouldShowNodeLabel({
        degree: 1,
        zoomRatio: 1.6,
        thresholds: { top10: 20, top25: 9, top50: 6 },
        isHovered: true,
        isSelected: false,
        isNeighbor: false,
      })
    ).toBe(true)
  })
})
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd frontend; npm run test -- KnowledgeGraphVisualization.test.tsx`

Expected: FAIL with `shouldShowNodeLabel is not exported`

- [ ] **Step 3: 写最小实现**

```ts
const ZOOM_THRESHOLD_TOP10 = 0.9
const ZOOM_THRESHOLD_TOP25 = 1.4

export function shouldShowNodeLabel({
  degree,
  zoomRatio,
  thresholds,
  isHovered,
  isSelected,
  isNeighbor,
}: {
  degree: number
  zoomRatio: number
  thresholds: DegreeThresholds
  isHovered: boolean
  isSelected: boolean
  isNeighbor: boolean
}) {
  if (isHovered || isSelected) return true
  if (degree <= 1) return false

  const threshold =
    zoomRatio < ZOOM_THRESHOLD_TOP10
      ? thresholds.top10
      : zoomRatio < ZOOM_THRESHOLD_TOP25
        ? thresholds.top25
        : thresholds.top50

  if (isNeighbor && degree >= thresholds.top50) return true
  return degree >= threshold
}
```

- [ ] **Step 4: 把标签判断接入 `nodeReducer`**

```ts
const shouldShowLabel = shouldShowNodeLabel({
  degree,
  zoomRatio,
  thresholds,
  isHovered,
  isSelected,
  isNeighbor: isInNeighborhood,
})

return {
  ...attributes,
  forceLabel: shouldShowLabel,
}
```

- [ ] **Step 5: 引入相机缩放状态并在缩放变化时刷新 renderer**

```ts
const [zoomRatio, setZoomRatio] = useState(1)

renderer.getCamera().on('updated', () => {
  setZoomRatio(renderer.getCamera().ratio)
})
```

- [ ] **Step 6: 保证 reducer 使用最新 `zoomRatio` 与 `thresholds`**

```ts
renderer.setSettings({
  nodeReducer: buildNodeReducer(graph, degreeMap, thresholds, selectedNodeId, hoveredNodeId, zoomRatio),
  edgeReducer: buildEdgeReducer(graph, selectedNodeId, hoveredNodeId),
})
```

- [ ] **Step 7: 运行测试**

Run: `cd frontend; npm run test -- KnowledgeGraphVisualization.test.tsx`

Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add frontend/src/components/graph/KnowledgeGraphVisualization.tsx frontend/src/components/graph/KnowledgeGraphVisualization.test.tsx
git commit -m "feat: reveal graph labels progressively by zoom"
```

## Task 4：联调、构建验证与文档回写

**Files:**
- Modify: `docs/ai/context/2026-04-27-graph-node-visual-rules.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: 跑前端单测**

Run: `cd frontend; npm run test -- KnowledgeGraphVisualization.test.tsx`

Expected: PASS

- [ ] **Step 2: 跑前端构建**

Run: `cd frontend; npm run build`

Expected: PASS with Vite build success output

- [ ] **Step 3: 本地联调 graph 页面**

Run: `cd frontend; npm run dev -- --host 127.0.0.1 --port 5173`

Manual check:
- 默认缩放下，只显示高连接节点标签
- 放大后，中频标签逐步出现
- `degree <= 1` 节点默认不常显标签
- 高频节点尺寸明显大于低频节点
- hover / selected 节点标签始终可见

- [ ] **Step 4: 如果默认参数需要微调，回写规则文档**

```md
- 将最终采用的 `baseSize / sizeScale / maxSize`
- 将最终采用的 `zoom` 档位
- 将邻居节点标签放宽条件记录到文档
```

- [ ] **Step 5: 如有阈值调整，同步更新 `AGENTS.md` 决策记忆**

```md
- 记录 graph 节点大小映射与标签分层的最终默认值
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/graph/KnowledgeGraphVisualization.tsx frontend/src/components/graph/KnowledgeGraphVisualization.test.tsx docs/ai/context/2026-04-27-graph-node-visual-rules.md AGENTS.md
git commit -m "feat: refine graph node visual density"
```

## 自检

- 规格覆盖：
  - `degree` 对数映射：Task 1、Task 2
  - 标签分位数阈值：Task 1、Task 3
  - 缩放渐进显示：Task 3
  - `hover / selected / degree <= 1` 规则：Task 3
  - 文档与记忆回写：Task 4
- 占位检查：
  - 未使用 `TODO`、`TBD`、`implement later`
  - 所有任务包含明确文件路径、命令和期望结果
- 类型一致性：
  - 统一使用 `degree`、`zoomRatio`、`thresholds`、`forceLabel` 命名

## 执行选项

计划已保存到 [docs/ai/context/2026-04-27-graph-node-visual-implementation-plan.md](D:/CodeWorkSpace/personal-knowledge-base/docs/ai/context/2026-04-27-graph-node-visual-implementation-plan.md)。

两个执行方式：

1. 子代理分任务执行
2. 我在当前会话直接按这个计划继续实现
