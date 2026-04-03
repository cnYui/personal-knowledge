import { Alert, Box } from '@mui/material'
import { useState } from 'react'

import { ErrorState } from '../components/common/ErrorState'
import { LoadingState } from '../components/common/LoadingState'
import { KnowledgeGraphVisualization } from '../components/graph/KnowledgeGraphVisualization'
import { NodeDetailPanel } from '../components/graph/NodeDetailPanel'
import { useGraphData } from '../hooks/useGraph'
import { GraphNode } from '../types/graph'

export function KnowledgeGraphPage() {
  const { data, isLoading, isError } = useGraphData('default', 50)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  const selectedNode: GraphNode | null =
    selectedNodeId && data ? data.nodes.find((n) => n.id === selectedNodeId) || null : null

  if (isLoading) return <LoadingState label="正在加载知识图谱..." />
  if (isError) return <ErrorState message="知识图谱加载失败" />

  if (!data || data.nodes.length === 0) {
    return (
      <Box>
        <Alert severity="info">知识图谱为空，请先添加一些记忆到知识图谱中。</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', gap: 2, flex: 1, minHeight: 0 }}>
        <Box
          sx={{
            flex: 1,
            height: '100%',
            borderRadius: 0.9,
            overflow: 'hidden',
            bgcolor: 'rgba(255, 253, 248, 0.9)',
            border: '1px solid rgba(176, 174, 165, 0.22)',
            boxShadow: '0 16px 34px rgba(20, 20, 19, 0.05)',
          }}
        >
          <KnowledgeGraphVisualization
            data={data}
            selectedNodeId={selectedNodeId}
            onNodeClick={setSelectedNodeId}
          />
        </Box>
        <Box sx={{ width: 320, height: '100%', overflow: 'auto' }}>
          <NodeDetailPanel node={selectedNode} />
        </Box>
      </Box>
    </Box>
  )
}
