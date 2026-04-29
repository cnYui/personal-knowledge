import BuildRoundedIcon from '@mui/icons-material/BuildRounded'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import ErrorOutlineRoundedIcon from '@mui/icons-material/ErrorOutlineRounded'
import MoreHorizRoundedIcon from '@mui/icons-material/MoreHorizRounded'
import { Box, Chip, Stack, Typography } from '@mui/material'

import { ChatToolResultBlock, ChatToolUseBlock } from '../../types/chat'

function summarizeValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)

  if (typeof value === 'object' && value !== null) {
    const summary = (value as { summary?: unknown }).summary
    if (typeof summary === 'string') {
      return summary
    }
  }

  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function resolveStatusLabel(result?: ChatToolResultBlock) {
  if (!result || result.status === 'running') return '运行中'
  if (result.status === 'error' || result.is_error) return '失败'
  return '完成'
}

export function ToolCallBlock({
  toolUse,
  toolResult,
}: {
  toolUse: ChatToolUseBlock
  toolResult?: ChatToolResultBlock
}) {
  const isError = toolResult?.status === 'error' || toolResult?.is_error
  const isDone = toolResult?.status === 'done' && !isError
  const inputSummary = summarizeValue(toolUse.input)
  const outputSummary = summarizeValue(toolResult?.output)

  return (
    <Box
      sx={{
        my: 1.1,
        borderRadius: 1.2,
        border: '1px solid rgba(20, 20, 19, 0.08)',
        bgcolor: 'rgba(255, 253, 248, 0.88)',
        boxShadow: '0 10px 22px rgba(20, 20, 19, 0.05)',
        px: 1.4,
        py: 1.2,
      }}
    >
      <Stack spacing={0.9}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Box
            sx={{
              display: 'flex',
              color: isError ? 'error.main' : isDone ? 'success.main' : 'secondary.main',
            }}
          >
            {isError ? (
              <ErrorOutlineRoundedIcon fontSize="small" />
            ) : isDone ? (
              <CheckCircleRoundedIcon fontSize="small" />
            ) : (
              <MoreHorizRoundedIcon fontSize="small" />
            )}
          </Box>
          <Typography variant="body2" sx={{ fontWeight: 700, flex: 1, minWidth: 0 }}>
            {toolUse.title || toolUse.name}
          </Typography>
          <Chip
            size="small"
            icon={<BuildRoundedIcon />}
            label={resolveStatusLabel(toolResult)}
            color={isError ? 'error' : isDone ? 'success' : 'default'}
            sx={{ height: 24 }}
          />
        </Stack>

        {inputSummary ? (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', wordBreak: 'break-word' }}>
            输入：{inputSummary}
          </Typography>
        ) : null}

        {outputSummary ? (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            结果：{outputSummary}
          </Typography>
        ) : null}
      </Stack>
    </Box>
  )
}
