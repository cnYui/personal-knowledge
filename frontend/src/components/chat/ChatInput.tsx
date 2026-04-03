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
    <Paper
      sx={{
        p: 1.25,
        borderRadius: 4,
        border: '1px solid rgba(176, 174, 165, 0.28)',
        backgroundColor: 'rgba(255, 253, 248, 0.92)',
        boxShadow: '0 16px 36px rgba(20, 20, 19, 0.06)',
      }}
    >
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
        <IconButton
          color="primary"
          onClick={handleSend}
          disabled={disabled}
          sx={{
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
            '&:hover': {
              bgcolor: '#20201e',
            },
            '&.Mui-disabled': {
              bgcolor: 'rgba(20, 20, 19, 0.16)',
              color: 'rgba(250, 249, 245, 0.76)',
            },
          }}
        >
          <SendIcon />
        </IconButton>
      </Stack>
    </Paper>
  )
}
