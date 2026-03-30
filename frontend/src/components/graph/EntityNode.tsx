import { Box, Typography } from '@mui/material'
import { memo } from 'react'
import { Handle, NodeProps, Position } from 'reactflow'

interface EntityNodeData {
  label: string
  summary?: string | null
  type: string
}

export const EntityNode = memo(({ data, selected }: NodeProps<EntityNodeData>) => {
  return (
    <Box
      sx={{
        padding: 2,
        borderRadius: 2,
        border: selected ? '2px solid #1976d2' : '2px solid #e0e0e0',
        backgroundColor: '#fff',
        minWidth: 120,
        maxWidth: 200,
        boxShadow: selected ? '0 4px 12px rgba(25, 118, 210, 0.3)' : '0 2px 8px rgba(0, 0, 0, 0.1)',
        transition: 'all 0.2s',
        '&:hover': {
          boxShadow: '0 4px 12px rgba(25, 118, 210, 0.2)',
          borderColor: '#1976d2',
        },
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#1976d2' }} />
      <Typography
        variant="body2"
        fontWeight={600}
        sx={{
          color: '#111827',
          textAlign: 'center',
          wordBreak: 'break-word',
        }}
      >
        {data.label}
      </Typography>
      {data.summary && (
        <Typography
          variant="caption"
          sx={{
            color: '#6b7280',
            mt: 0.5,
            textAlign: 'center',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {data.summary}
        </Typography>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: '#1976d2' }} />
    </Box>
  )
})

EntityNode.displayName = 'EntityNode'
