import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline'
import HubOutlinedIcon from '@mui/icons-material/HubOutlined'
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty'
import { Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from '@mui/material'
import { useEffect, useMemo, useState } from 'react'

import { Memory } from '../../types/memory'
import { formatDate } from '../../utils/format'

type RetryMeta = {
  attempt: number
  max: number
  retryAt: Date
}

function parseRetryMeta(graphError?: string | null): RetryMeta | null {
  if (!graphError || !graphError.startsWith('__retry__:')) {
    return null
  }

  const payload = graphError.slice('__retry__:'.length)
  const params = new URLSearchParams(payload.replace(/;/g, '&'))

  const attempt = Number(params.get('attempt'))
  const max = Number(params.get('max'))
  const retryAtRaw = params.get('retry_at')
  const retryAt = retryAtRaw ? new Date(retryAtRaw) : null

  if (!attempt || !max || !retryAt || Number.isNaN(retryAt.getTime())) {
    return null
  }

  return { attempt, max, retryAt }
}

function getRetrySecondsLeft(retryMeta: RetryMeta, nowMs: number): number {
  const seconds = Math.ceil((retryMeta.retryAt.getTime() - nowMs) / 1000)
  return Math.max(0, seconds)
}

function formatGraphErrorMessage(graphError?: string | null) {
  if (!graphError) {
    return ''
  }

  const normalized = graphError.toLowerCase()
  if (normalized.includes('rate limit') || normalized.includes('429') || normalized.includes('too many requests')) {
    return 'Rate limit exceeded（上游模型限流，请稍后重试）'
  }

  return graphError
}

export function MemoryDetailDialog({
  memory,
  open,
  addingToGraph,
  onClose,
  onEdit,
  onDelete,
  onAddToGraph,
}: {
  memory: Memory | null
  open: boolean
  addingToGraph: boolean
  onClose: () => void
  onEdit: (memory: Memory) => void
  onDelete: (memory: Memory) => void
  onAddToGraph: (memory: Memory) => Promise<void>
}) {
  if (!memory) return null

  const retryMeta = useMemo(() => parseRetryMeta(memory.graph_error), [memory.graph_error])
  const [nowMs, setNowMs] = useState(Date.now())

  useEffect(() => {
    setNowMs(Date.now())
    if (!open || !retryMeta || memory.graph_status !== 'pending') {
      return
    }

    const timer = window.setInterval(() => {
      setNowMs(Date.now())
    }, 1000)

    return () => {
      window.clearInterval(timer)
    }
  }, [open, retryMeta, memory.graph_status])

  const retrySecondsLeft = retryMeta ? getRetrySecondsLeft(retryMeta, nowMs) : null

  // 根据 graph_status 确定按钮状态和文本
  const getGraphButtonConfig = () => {
    switch (memory.graph_status) {
      case 'added':
        return {
          disabled: addingToGraph,
          text: '重新提交到知识图谱',
          icon: <HubOutlinedIcon />,
          color: 'primary' as const,
        }
      case 'pending':
        return {
          disabled: true,
          text: retryMeta ? `重试中（${retryMeta.attempt}/${retryMeta.max}）` : '处理中...',
          icon: <HourglassEmptyIcon />,
          color: 'warning' as const,
        }
      case 'failed':
        return {
          disabled: false,
          text: '重试添加',
          icon: <ErrorOutlineIcon />,
          color: 'error' as const,
        }
      default:
        return {
          disabled: addingToGraph,
          text: '加入知识图谱',
          icon: <HubOutlinedIcon />,
          color: 'primary' as const,
        }
    }
  }

  const buttonConfig = getGraphButtonConfig()

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>
        <Stack direction="row" spacing={1} alignItems="center">
          <span>{memory.title}</span>
          {memory.graph_status === 'added' && (
            <Chip label="已在知识图谱" size="small" color="success" icon={<CheckCircleOutlineIcon />} />
          )}
          {memory.graph_status === 'pending' && (
            <Chip
              label={retryMeta ? `重试中 ${retryMeta.attempt}/${retryMeta.max}` : '处理中'}
              size="small"
              color="warning"
              icon={<HourglassEmptyIcon />}
            />
          )}
          {memory.graph_status === 'failed' && (
            <Chip
              label={formatGraphErrorMessage(memory.graph_error).includes('Rate limit exceeded') ? '限流失败' : '添加失败'}
              size="small"
              color="error"
              icon={<ErrorOutlineIcon />}
            />
          )}
        </Stack>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
            {memory.content}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            创建时间：{formatDate(memory.created_at)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            更新时间：{formatDate(memory.updated_at)}
          </Typography>
          {memory.graph_status === 'added' && memory.graph_added_at && (
            <Typography variant="caption" color="success.main">
              ✓ 已添加到知识图谱：{formatDate(memory.graph_added_at)}
            </Typography>
          )}
          {memory.graph_status === 'pending' && retryMeta && retrySecondsLeft !== null && (
            <Typography variant="caption" color="warning.main">
              ⟳ 自动重试中：第 {retryMeta.attempt}/{retryMeta.max} 次，下次重试剩余{' '}
              {retrySecondsLeft > 0 ? `${retrySecondsLeft} 秒` : '即将开始'}
            </Typography>
          )}
          {memory.graph_status === 'failed' && memory.graph_error && (
            <Typography variant="caption" color="error.main">
              ✗ 添加失败：{formatGraphErrorMessage(memory.graph_error)}
            </Typography>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button color="error" startIcon={<DeleteOutlineIcon />} onClick={() => onDelete(memory)}>
          删除
        </Button>
        <Button startIcon={<EditOutlinedIcon />} onClick={() => onEdit(memory)}>
          编辑
        </Button>
        <Button
          variant="contained"
          color={buttonConfig.color}
          startIcon={buttonConfig.icon}
          disabled={buttonConfig.disabled}
          onClick={async () => {
            await onAddToGraph(memory)
          }}
        >
          {buttonConfig.text}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
