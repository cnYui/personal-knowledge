const BASE_NODE_SIZE = 5
const NODE_SIZE_SCALE = 3
const MAX_NODE_SIZE = 18
const ZOOM_THRESHOLD_TOP10 = 0.9
const ZOOM_THRESHOLD_TOP25 = 1.4

export interface DegreeThresholds {
  top10: number
  top25: number
  top50: number
}

export interface LabelVisibilityInput {
  degree: number
  zoomRatio: number
  thresholds: DegreeThresholds
  isHovered: boolean
  isSelected: boolean
  isNeighbor: boolean
}

export function computeNodeSize(degree: number) {
  return Math.min(MAX_NODE_SIZE, BASE_NODE_SIZE + Math.log2(Math.max(degree, 0) + 1) * NODE_SIZE_SCALE)
}

function pickThreshold(sortedDegrees: number[], ratio: number) {
  if (sortedDegrees.length === 0) {
    return 0
  }

  const index = Math.min(sortedDegrees.length - 1, Math.max(0, Math.ceil(sortedDegrees.length * ratio) - 1))
  return sortedDegrees[index]
}

export function computeDegreeThresholds(degrees: number[]): DegreeThresholds {
  const sortedDegrees = [...degrees].sort((left, right) => right - left)

  return {
    top10: pickThreshold(sortedDegrees, 0.1),
    top25: pickThreshold(sortedDegrees, 0.25),
    top50: pickThreshold(sortedDegrees, 0.5),
  }
}

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

export function shouldShowNodeLabel({
  degree,
  zoomRatio,
  thresholds,
  isHovered,
  isSelected,
  isNeighbor,
}: LabelVisibilityInput) {
  if (isHovered || isSelected) {
    return true
  }

  if (degree <= 1) {
    return false
  }

  const threshold =
    zoomRatio < ZOOM_THRESHOLD_TOP10
      ? thresholds.top10
      : zoomRatio < ZOOM_THRESHOLD_TOP25
        ? thresholds.top25
        : thresholds.top50

  if (isNeighbor && degree >= thresholds.top50) {
    return true
  }

  return degree >= threshold
}
