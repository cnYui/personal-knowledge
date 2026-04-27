import AddRoundedIcon from '@mui/icons-material/AddRounded'
import CenterFocusStrongRoundedIcon from '@mui/icons-material/CenterFocusStrongRounded'
import RemoveRoundedIcon from '@mui/icons-material/RemoveRounded'
import { alpha, Box, IconButton, Paper, Stack, Tooltip, Typography } from '@mui/material'
import Graph from 'graphology'
import forceAtlas2 from 'graphology-layout-forceatlas2'
import { useEffect, useMemo, useRef, useState } from 'react'
import Sigma from 'sigma'

import { GraphData } from '../../types/graph'

const ENTITY_COLOR = '#da6f4d'
const EPISODE_COLOR = '#707be6'
const ISOLATED_COLOR = '#63a66a'
const MUTED_NODE_COLOR = '#d8d2c8'
const MUTED_EDGE_COLOR = '#d6d2ca'
const DEFAULT_EDGE_COLOR = '#c3beb4'
const HOVER_EDGE_COLOR = '#96a1ff'
const SELECTED_EDGE_COLOR = '#d97757'
const LAYOUT_ITERATIONS = 220

interface SigmaNodeAttributes {
  x: number
  y: number
  size: number
  label: string
  color: string
  type: string
  highlighted?: boolean
  forceLabel?: boolean
  zIndex?: number
}

interface SigmaEdgeAttributes {
  size: number
  label: string | null
  color: string
  type: string
  zIndex?: number
  hidden?: boolean
  forceLabel?: boolean
}

interface KnowledgeGraphVisualizationProps {
  data: GraphData
  selectedNodeId?: string | null
  onNodeClick?: (nodeId: string | null) => void
}

function ringPosition(index: number, count: number, radius: number, offset: number) {
  const angle = (index / Math.max(count, 1)) * Math.PI * 2 + offset
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius,
  }
}

function buildSigmaGraph(data: GraphData) {
  const graph = new Graph<SigmaNodeAttributes, SigmaEdgeAttributes>({ multi: true, type: 'directed' })
  const degreeMap = new Map<string, number>(data.nodes.map((node) => [node.id, 0]))

  data.edges.forEach((edge) => {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) ?? 0) + 1)
    degreeMap.set(edge.target, (degreeMap.get(edge.target) ?? 0) + 1)
  })

  const connectedNodes = data.nodes.filter((node) => (degreeMap.get(node.id) ?? 0) > 0)
  const connectedEntities = connectedNodes.filter((node) => node.type === 'entity')
  const episodes = connectedNodes.filter((node) => node.type === 'episode')
  const isolatedNodes = data.nodes.filter((node) => (degreeMap.get(node.id) ?? 0) === 0)

  const entityRadius = Math.max(8, connectedEntities.length * 0.3)
  const episodeRadius = Math.max(16, episodes.length * 0.34)
  const isolatedRadius = Math.max(23, isolatedNodes.length * 0.42)

  connectedEntities.forEach((node, index) => {
    const degree = degreeMap.get(node.id) ?? 0
    const position = ringPosition(index, connectedEntities.length, entityRadius, -Math.PI / 2)
    graph.addNode(node.id, {
      ...position,
      size: 8 + Math.min(degree, 10) * 0.55,
      label: node.label,
      color: ENTITY_COLOR,
      type: 'circle',
      forceLabel: degree >= 16,
      zIndex: degree,
    })
  })

  episodes.forEach((node, index) => {
    const degree = degreeMap.get(node.id) ?? 0
    const position = ringPosition(index, episodes.length, episodeRadius, Math.PI / 8)
    graph.addNode(node.id, {
      ...position,
      size: 6.2 + Math.min(degree, 8) * 0.35,
      label: node.label,
      color: EPISODE_COLOR,
      type: 'circle',
      forceLabel: degree >= 10,
      zIndex: degree,
    })
  })

  isolatedNodes.forEach((node, index) => {
    const position = ringPosition(index, isolatedNodes.length, isolatedRadius, Math.PI / 4)
    graph.addNode(node.id, {
      ...position,
      size: node.type === 'episode' ? 6 : 7.2,
      label: node.label,
      color: ISOLATED_COLOR,
      type: 'circle',
      forceLabel: false,
      zIndex: 12,
    })
  })

  data.edges.forEach((edge) => {
    if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) {
      return
    }

    graph.addDirectedEdgeWithKey(edge.id, edge.source, edge.target, {
      size: edge.label === 'relates_to' ? 1.7 : 2.2,
      label: edge.label,
      color: DEFAULT_EDGE_COLOR,
      type: 'arrow',
      zIndex: 1,
    })
  })

  if (connectedNodes.length > 1 && data.edges.length > 0) {
    const inferredSettings = forceAtlas2.inferSettings(graph)
    forceAtlas2.assign(graph, {
      iterations: LAYOUT_ITERATIONS,
      settings: {
        ...inferredSettings,
        adjustSizes: true,
        barnesHutOptimize: connectedNodes.length > 150,
        barnesHutTheta: 0.6,
        gravity: 0.12,
        scalingRatio: 18,
        slowDown: 3,
        strongGravityMode: false,
      },
    })
  }

  if (isolatedNodes.length > 0) {
    let maxDistance = 0
    connectedNodes.forEach((node) => {
      const attributes = graph.getNodeAttributes(node.id)
      maxDistance = Math.max(maxDistance, Math.hypot(attributes.x, attributes.y))
    })

    const isolateRadius = Math.max(maxDistance * 1.35, 26)
    isolatedNodes.forEach((node, index) => {
      const position = ringPosition(index, isolatedNodes.length, isolateRadius, Math.PI / 6)
      graph.mergeNodeAttributes(node.id, position)
    })
  }

  return { graph, degreeMap }
}

function buildNodeReducer(
  graph: Graph<SigmaNodeAttributes, SigmaEdgeAttributes>,
  degreeMap: Map<string, number>,
  selectedNodeId: string | null,
  hoveredNodeId: string | null
) {
  const activeNodeId = selectedNodeId ?? hoveredNodeId
  const neighborhood = activeNodeId ? new Set([activeNodeId, ...graph.neighbors(activeNodeId)]) : null

  return (nodeId: string, attributes: SigmaNodeAttributes) => {
    const degree = degreeMap.get(nodeId) ?? 0
    const isSelected = selectedNodeId === nodeId
    const isHovered = hoveredNodeId === nodeId
    const isInNeighborhood = neighborhood?.has(nodeId) ?? false

    if (!activeNodeId) {
      return {
        ...attributes,
        color: attributes.color,
        size: attributes.size,
        highlighted: false,
        forceLabel: attributes.forceLabel,
        zIndex: attributes.zIndex ?? 0,
      }
    }

    if (isSelected) {
      return {
        ...attributes,
        color: SELECTED_EDGE_COLOR,
        size: attributes.size + 2.4,
        highlighted: true,
        forceLabel: true,
        zIndex: 100,
      }
    }

    if (isHovered) {
      return {
        ...attributes,
        color: HOVER_EDGE_COLOR,
        size: attributes.size + 1.6,
        highlighted: true,
        forceLabel: true,
        zIndex: 90,
      }
    }

    if (isInNeighborhood) {
      return {
        ...attributes,
        color: attributes.color,
        size: attributes.size + Math.min(degree * 0.08, 0.8),
        highlighted: false,
        forceLabel: degree >= 4,
        zIndex: 70,
      }
    }

    return {
      ...attributes,
      color: MUTED_NODE_COLOR,
      size: Math.max(attributes.size - 1.2, 4.5),
      highlighted: false,
      forceLabel: false,
      zIndex: 1,
    }
  }
}

function buildEdgeReducer(
  graph: Graph<SigmaNodeAttributes, SigmaEdgeAttributes>,
  selectedNodeId: string | null,
  hoveredNodeId: string | null
) {
  const activeNodeId = selectedNodeId ?? hoveredNodeId

  return (edgeId: string, attributes: SigmaEdgeAttributes) => {
    if (!activeNodeId) {
      return {
        ...attributes,
        color: attributes.color,
        size: attributes.size,
        label: null,
        hidden: false,
        zIndex: attributes.zIndex ?? 0,
      }
    }

    const [source, target] = graph.extremities(edgeId)
    const touchesActiveNode = source === activeNodeId || target === activeNodeId
    const touchesHoveredNode = hoveredNodeId ? source === hoveredNodeId || target === hoveredNodeId : false
    const isSelectedContext = Boolean(selectedNodeId)

    if (touchesActiveNode) {
      return {
        ...attributes,
        color: selectedNodeId ? SELECTED_EDGE_COLOR : HOVER_EDGE_COLOR,
        size: attributes.size + 1,
        label: attributes.label,
        hidden: false,
        forceLabel: true,
        zIndex: 80,
      }
    }

    if (touchesHoveredNode) {
      return {
        ...attributes,
        color: HOVER_EDGE_COLOR,
        size: attributes.size + 0.6,
        label: attributes.label,
        hidden: false,
        zIndex: 60,
      }
    }

    return {
      ...attributes,
      color: MUTED_EDGE_COLOR,
      size: Math.max(attributes.size - 0.4, 1),
      label: null,
      hidden: isSelectedContext,
      zIndex: 1,
    }
  }
}

export function KnowledgeGraphVisualization({ data, selectedNodeId = null, onNodeClick }: KnowledgeGraphVisualizationProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const rendererRef = useRef<Sigma<SigmaNodeAttributes, SigmaEdgeAttributes> | null>(null)
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null)

  const { graph, degreeMap } = useMemo(() => buildSigmaGraph(data), [data])

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return
    }

    const renderer = new Sigma(graph, container, {
      renderEdgeLabels: true,
      allowInvalidContainer: true,
      labelFont: 'system-ui, sans-serif',
      labelColor: { color: '#23201b' },
      defaultEdgeColor: DEFAULT_EDGE_COLOR,
      defaultNodeColor: ENTITY_COLOR,
      edgeLabelColor: { color: '#7a756b' },
      edgeLabelSize: 12,
      edgeLabelFont: 'system-ui, sans-serif',
      labelRenderedSizeThreshold: 18,
      stagePadding: 32,
      minCameraRatio: 0.18,
      maxCameraRatio: 4,
      zIndex: true,
      hideEdgesOnMove: true,
      nodeReducer: buildNodeReducer(graph, degreeMap, selectedNodeId, hoveredNodeId),
      edgeReducer: buildEdgeReducer(graph, selectedNodeId, hoveredNodeId),
    })

    rendererRef.current = renderer

    renderer.on('clickNode', ({ node }) => {
      onNodeClick?.(node)
    })
    renderer.on('clickStage', () => {
      onNodeClick?.(null)
    })
    renderer.on('enterNode', ({ node }) => {
      container.style.cursor = 'pointer'
      setHoveredNodeId(node)
    })
    renderer.on('leaveNode', () => {
      container.style.cursor = 'grab'
      setHoveredNodeId(null)
    })

    container.style.cursor = 'grab'
    renderer.getCamera().animatedReset({ duration: 300 })

    return () => {
      renderer.kill()
      rendererRef.current = null
    }
  }, [degreeMap, graph, onNodeClick])

  useEffect(() => {
    const renderer = rendererRef.current
    if (!renderer) {
      return
    }

    renderer.setSettings({
      nodeReducer: buildNodeReducer(graph, degreeMap, selectedNodeId, hoveredNodeId),
      edgeReducer: buildEdgeReducer(graph, selectedNodeId, hoveredNodeId),
    })
    renderer.refresh()
  }, [degreeMap, graph, hoveredNodeId, selectedNodeId])

  const handleZoomIn = () => {
    void rendererRef.current?.getCamera().animatedZoom({ duration: 180, factor: 1.5 })
  }

  const handleZoomOut = () => {
    void rendererRef.current?.getCamera().animatedUnzoom({ duration: 180, factor: 1.5 })
  }

  const handleResetView = () => {
    void rendererRef.current?.getCamera().animatedReset({ duration: 220 })
  }

  const entityCount = data.nodes.filter((node) => node.type === 'entity').length
  const episodeCount = data.nodes.filter((node) => node.type === 'episode').length
  const isolatedCount = data.nodes.filter((node) => (degreeMap.get(node.id) ?? 0) === 0).length

  return (
    <Box
      sx={{
        position: 'relative',
        width: '100%',
        height: '100%',
        background:
          'radial-gradient(circle at top left, rgba(255,255,255,0.96) 0%, rgba(249, 245, 238, 0.96) 38%, rgba(245, 238, 228, 0.92) 100%)',
      }}
    >
      <Box ref={containerRef} sx={{ width: '100%', height: '100%' }} />

      <Paper
        sx={{
          position: 'absolute',
          top: 16,
          left: 16,
          px: 2,
          py: 1.5,
          minWidth: 220,
          borderRadius: 1,
          bgcolor: alpha('#fffdf8', 0.9),
          border: '1px solid rgba(176, 174, 165, 0.24)',
          boxShadow: '0 12px 26px rgba(20, 20, 19, 0.08)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <Typography variant="overline" sx={{ color: '#8f887e', letterSpacing: '0.12em' }}>
          Knowledge Graph
        </Typography>
        <Typography variant="body2" sx={{ color: '#2c2720', fontWeight: 600 }}>
          节点 {data.stats.total_nodes} / 关系 {data.stats.total_edges}
        </Typography>
        <Stack direction="row" spacing={1.5} sx={{ mt: 1.25, flexWrap: 'wrap' }}>
          <Stack direction="row" spacing={0.75} alignItems="center">
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: ENTITY_COLOR }} />
            <Typography variant="caption" sx={{ color: '#716b63' }}>
              实体 {entityCount}
            </Typography>
          </Stack>
          <Stack direction="row" spacing={0.75} alignItems="center">
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: EPISODE_COLOR }} />
            <Typography variant="caption" sx={{ color: '#716b63' }}>
              情节 {episodeCount}
            </Typography>
          </Stack>
          <Stack direction="row" spacing={0.75} alignItems="center">
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: ISOLATED_COLOR }} />
            <Typography variant="caption" sx={{ color: '#716b63' }}>
              孤立 {isolatedCount}
            </Typography>
          </Stack>
        </Stack>
      </Paper>

      <Paper
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          p: 0.75,
          borderRadius: 1,
          bgcolor: alpha('#fffdf8', 0.9),
          border: '1px solid rgba(176, 174, 165, 0.24)',
          boxShadow: '0 10px 22px rgba(20, 20, 19, 0.08)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <Stack spacing={0.75}>
          <Tooltip title="放大">
            <IconButton size="small" onClick={handleZoomIn} sx={{ color: '#584f45' }}>
              <AddRoundedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="缩小">
            <IconButton size="small" onClick={handleZoomOut} sx={{ color: '#584f45' }}>
              <RemoveRoundedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="重置视图">
            <IconButton size="small" onClick={handleResetView} sx={{ color: '#584f45' }}>
              <CenterFocusStrongRoundedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      </Paper>
    </Box>
  )
}
