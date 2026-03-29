import AccessTimeOutlinedIcon from '@mui/icons-material/AccessTimeOutlined'
import { Box, Paper, Stack, Typography } from '@mui/material'

import { Memory } from '../../types/memory'
import { formatDate } from '../../utils/format'

export function MemoryBubbleItem({
  memory,
  onSelect,
}: {
  memory: Memory
  onSelect: (memory: Memory) => void
}) {
  const title = memory.title?.trim() ? memory.title : '标题生成中...'
  const summary = memory.content.length > 120 ? `${memory.content.slice(0, 120)}...` : memory.content

  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
      <Paper
        onClick={() => onSelect(memory)}
        elevation={0}
        sx={{
          px: 2,
          py: 1.5,
          borderRadius: 3,
          cursor: 'pointer',
          maxWidth: { xs: '100%', md: '82%' },
          border: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
          transition: 'all 0.15s ease',
          '&:hover': {
            borderColor: 'primary.main',
            bgcolor: 'action.hover',
          },
        }}
      >
        <Stack spacing={1}>
          <Typography variant="subtitle1" fontWeight={600}>
            {title}
          </Typography>
          {memory.title_status === 'pending' ? (
            <Typography variant="caption" color="warning.main">
              标题抽取中
            </Typography>
          ) : null}
          <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
            {summary}
          </Typography>

          <Stack direction="row" spacing={0.5} alignItems="center" color="text.secondary">
            <AccessTimeOutlinedIcon fontSize="inherit" />
            <Typography variant="caption">{formatDate(memory.updated_at || memory.created_at)}</Typography>
          </Stack>
        </Stack>
      </Paper>
    </Box>
  )
}
