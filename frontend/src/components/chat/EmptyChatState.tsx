import { Paper, Typography } from '@mui/material'

export function EmptyChatState() {
  return (
    <Paper sx={{ p: 4, borderRadius: 3, textAlign: 'center' }}>
      <Typography variant="h6" sx={{ mb: 1 }}>
        还没有对话记录
      </Typography>
      <Typography color="text.secondary">输入一个问题，让知识库开始回答。</Typography>
    </Paper>
  )
}
