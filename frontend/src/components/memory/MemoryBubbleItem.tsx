import AccessTimeOutlinedIcon from '@mui/icons-material/AccessTimeOutlined'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty'
import { Box, Chip, Paper, Stack, Typography } from '@mui/material'

import { Memory } from '../../types/memory'
import { formatDate } from '../../utils/format'

function isRateLimitError(graphError?: string | null) {
  if (!graphError) {
    return false
  }

  const normalized = graphError.toLowerCase()
  return normalized.includes('rate limit') || normalized.includes('429') || normalized.includes('too many requests')
}

export function MemoryBubbleItem({
  memory,
  onSelect,
}: {
  memory: Memory
  onSelect: (memory: Memory) => void
}) {
  const title = memory.title?.trim() ? memory.title : '标题生成中...'
  const summary = memory.content.length > 120 ? `${memory.content.slice(0, 120)}...` : memory.content

  // 知识图谱状态标识
  const getGraphStatusChip = () => {
    switch (memory.graph_status) {
      case 'added':
        return <Chip label="已在图谱" size="small" color="success" icon={<CheckCircleIcon />} />
      case 'pending':
        return <Chip label="处理中" size="small" color="warning" icon={<HourglassEmptyIcon />} />
      case 'failed':
        return (
          <Chip
            label={isRateLimitError(memory.graph_error) ? '限流失败' : '失败'}
            size="small"
            color="error"
            icon={<ErrorIcon />}
          />
        )
      default:
        return null
    }
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
      <Paper
        onClick={() => onSelect(memory)}
        elevation={0}
        sx={{
          px: 2,
          py: 1.65,
          borderRadius: 4,
          cursor: 'pointer',
          maxWidth: { xs: '100%', md: '82%' },
          border: '1px solid',
          borderColor: memory.graph_status === 'added' ? 'rgba(120, 140, 93, 0.42)' : 'divider',
          bgcolor: 'background.paper',
          boxShadow: '0 14px 28px rgba(20, 20, 19, 0.05)',
          background: 'linear-gradient(180deg, #fffdf8 0%, #f5f2ea 100%)',
          transition: 'all 0.15s ease',
          '&:hover': {
            borderColor: 'rgba(20, 20, 19, 0.28)',
            bgcolor: 'rgba(255, 253, 248, 1)',
            boxShadow: '0 18px 34px rgba(20, 20, 19, 0.08)',
            transform: 'translateY(-1px)',
          },
        }}
      >
        <Stack spacing={1}>
          <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
            <Typography variant="subtitle1" fontWeight={600} sx={{ color: 'text.primary' }}>
              {title}
            </Typography>
            {getGraphStatusChip()}
          </Stack>
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
