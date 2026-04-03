import { Box, Paper, Typography } from '@mui/material'
import { useCallback, useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  Edge,
  MiniMap,
  Node,
  NodeTypes,
  Panel,
  useEdgesState,
  useNodesState,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { GraphData } from '../../types/graph'
import { EntityNode } from './EntityNode'

const nodeTypes: NodeTypes = {
  entity: EntityNode,
}

interface KnowledgeGraphVisualizationProps {
  data: GraphData
  selectedNodeId?: string | null
  onNodeClick?: (nodeId: string) => void
}

export function KnowledgeGraphVisualization({ data, selectedNodeId, onNodeClick }: KnowledgeGraphVisualizationProps) {
  // Convert graph data to React Flow format
  const initialNodes: Node[] = useMemo(() => {
    const nodeCount = data.nodes.length
    const radius = Math.max(300, nodeCount * 20) // Dynamic radius based on node count
    const centerX = 400
    const centerY = 300

    return data.nodes.map((node, index) => ({
      id: node.id,
      type: 'entity',
      position: {
        x: Math.cos((index / nodeCount) * 2 * Math.PI) * radius + centerX,
        y: Math.sin((index / nodeCount) * 2 * Math.PI) * radius + centerY,
      },
      data: {
        label: node.label,
        summary: node.summary,
        type: node.type,
      },
    }))
  }, [data.nodes])

  const initialEdges: Edge[] = useMemo(() => {
    return data.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      type: 'smoothstep',
      animated: true,
      style: { stroke: '#b0aea5', strokeWidth: 1.6 },
      labelStyle: { fill: '#6f6a61', fontSize: 12 },
      labelBgStyle: { fill: '#fffdf8', fillOpacity: 0.92 },
    }))
  }, [data.edges])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id)
    },
    [onNodeClick]
  )

  return (
    <Box sx={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        attributionPosition="bottom-left"
      >
        <Background color="#e8e6dc" gap={18} />
        <Controls />
        <MiniMap
          nodeColor={(node) => (node.id === selectedNodeId ? '#d97757' : '#e8e6dc')}
          maskColor="rgba(20, 20, 19, 0.08)"
        />
        <Panel position="top-right">
          <Paper
            sx={{
              p: 2,
              bgcolor: 'rgba(255, 253, 248, 0.92)',
              border: '1px solid rgba(176, 174, 165, 0.28)',
              borderRadius: 0.75,
              boxShadow: '0 12px 28px rgba(20, 20, 19, 0.05)',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              节点: {data.stats.total_nodes}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              关系: {data.stats.total_edges}
            </Typography>
          </Paper>
        </Panel>
      </ReactFlow>
    </Box>
  )
}
