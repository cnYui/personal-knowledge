import { Box, Divider, Paper, Typography } from '@mui/material'

import { unifiedCardSx } from '../../styles/cardStyles'
import { GraphNode } from '../../types/graph'

interface NodeDetailPanelProps {
  node: GraphNode | null
}

export function NodeDetailPanel({ node }: NodeDetailPanelProps) {
  if (!node) {
    return (
      <Paper
        sx={{
          ...unifiedCardSx,
          p: 3,
          height: '100%',
        }}
      >
        <Typography color="text.secondary" textAlign="center">
          点击节点查看详情
        </Typography>
      </Paper>
    )
  }

  return (
    <Paper
      sx={{
        ...unifiedCardSx,
        p: 3,
        height: '100%',
        overflow: 'auto',
      }}
    >
      <Typography variant="h6" fontWeight={600} gutterBottom>
        {node.label}
      </Typography>

      <Divider sx={{ my: 2 }} />

      <Box sx={{ mb: 2 }}>
        <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
          类型
        </Typography>
        <Typography variant="body2">{node.type === 'entity' ? '实体' : '情节'}</Typography>
      </Box>

      {node.summary && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
            描述
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {node.summary}
          </Typography>
        </Box>
      )}

      <Box>
        <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
          节点 ID
        </Typography>
        <Typography variant="caption" sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
          {node.id}
        </Typography>
      </Box>
    </Paper>
  )
}
