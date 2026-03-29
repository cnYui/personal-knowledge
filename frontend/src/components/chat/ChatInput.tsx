import SendIcon from '@mui/icons-material/Send'
import { IconButton, Paper, Stack, TextField } from '@mui/material'
import { useState } from 'react'

export function ChatInput({ onSend, disabled }: { onSend: (message: string) => void; disabled: boolean }) {
  const [message, setMessage] = useState('')

  const handleSend = () => {
    const trimmed = message.trim()
    if (!trimmed) return
    onSend(trimmed)
    setMessage('')
  }

  return (
    <Paper sx={{ p: 2, borderRadius: 3 }}>
      <Stack direction="row" spacing={1} alignItems="center">
        <TextField
          fullWidth
          multiline
          maxRows={4}
          placeholder="输入你的问题..."
          value={message}
          disabled={disabled}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              handleSend()
            }
          }}
        />
        <IconButton color="primary" onClick={handleSend} disabled={disabled}>
          <SendIcon />
        </IconButton>
      </Stack>
    </Paper>
  )
}
