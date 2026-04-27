import AccessTimeOutlinedIcon from '@mui/icons-material/AccessTimeOutlined'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty'
import { Box, Chip, Paper, Stack, Typography } from '@mui/material'

import { unifiedCardHoverSx, unifiedCardMutedBackground, unifiedCardSx } from '../../styles/cardStyles'
import { Memory } from '../../types/memory'
import { formatDate } from '../../utils/format'

function isRateLimitError(graphError?: string | null) {
  if (!graphError) {
    return false
  }

  const normalized = graphError.toLowerCase()
  return normalized.includes('rate limit') || normalized.includes('429') || normalized.includes('too many requests')
}

function parseRetryMeta(graphError?: string | null) {
  if (!graphError || !graphError.startsWith('__retry__:')) {
    return null
  }

  const payload = graphError.slice('__retry__:'.length)
  const params = new URLSearchParams(payload.replace(/;/g, '&'))
  const attempt = Number(params.get('attempt'))
  const max = Number(params.get('max'))

  if (!attempt || !max) {
    return null
  }

  return { attempt, max }
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
  const retryMeta = parseRetryMeta(memory.graph_error)

  // 知识图谱状态标识
  const getGraphStatusChip = () => {
    switch (memory.graph_status) {
      case 'added':
        return <Chip label="已在图谱" size="small" color="success" icon={<CheckCircleIcon />} />
      case 'pending':
        return (
          <Chip
            label={retryMeta ? `重试中 ${retryMeta.attempt}/${retryMeta.max}` : '处理中'}
            size="small"
            color="warning"
            icon={<HourglassEmptyIcon />}
          />
        )
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
        sx={[
          unifiedCardSx,
          unifiedCardHoverSx,
          {
            px: 2,
            py: 1.65,
            cursor: 'pointer',
            width: '100%',
            maxWidth: { xs: '100%', md: '82%' },
            border: '1px solid',
            borderColor: memory.graph_status === 'added' ? 'rgba(120, 140, 93, 0.42)' : 'divider',
            bgcolor: unifiedCardMutedBackground,
            '&:hover': {
              borderColor: 'rgba(20, 20, 19, 0.28)',
              bgcolor: unifiedCardMutedBackground,
            },
          },
        ]}
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
