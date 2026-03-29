import { Paper, Stack, Typography } from '@mui/material'

import { ChatMessage } from '../../types/chat'

export function ChatMessageList({ messages, loading }: { messages: ChatMessage[]; loading: boolean }) {
  return (
    <Stack spacing={2}>
      {messages.map((message) => (
        <Paper
          key={message.id}
          sx={{
            p: 2,
            maxWidth: '80%',
            alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
            bgcolor: message.role === 'user' ? 'primary.main' : '#fff',
            color: message.role === 'user' ? '#fff' : 'text.primary',
            borderRadius: 3,
          }}
        >
          <Typography variant="caption" sx={{ opacity: 0.8 }}>
            {message.role === 'user' ? '你' : 'AI'}
          </Typography>
          <Typography sx={{ whiteSpace: 'pre-wrap' }}>{message.content}</Typography>
        </Paper>
      ))}
      {loading ? <Typography color="text.secondary">AI 正在思考...</Typography> : null}
    </Stack>
  )
}
