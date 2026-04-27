import { describe, expect, it } from 'vitest'

import {
  buildNodeVisualMeta,
  computeDegreeThresholds,
  computeNodeSize,
  shouldShowNodeLabel,
} from './graphVisualRules'

describe('computeNodeSize', () => {
  it('对 degree 使用对数放大并限制最大值', () => {
    expect(computeNodeSize(0)).toBe(5)
    expect(computeNodeSize(1)).toBe(8)
    expect(computeNodeSize(3)).toBe(11)
    expect(computeNodeSize(255)).toBe(18)
  })
})

describe('computeDegreeThresholds', () => {
  it('按前 10% / 25% / 50% 计算 degree 阈值', () => {
    const thresholds = computeDegreeThresholds([20, 12, 9, 8, 6, 5, 4, 2, 1, 1])

    expect(thresholds.top10).toBe(20)
    expect(thresholds.top25).toBe(9)
    expect(thresholds.top50).toBe(6)
  })
})

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
