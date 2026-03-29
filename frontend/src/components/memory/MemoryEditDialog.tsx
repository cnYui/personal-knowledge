import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField } from '@mui/material'
import { useEffect, useState } from 'react'

import { Memory, MemoryPayload } from '../../types/memory'

export function MemoryEditDialog({
  memory,
  open,
  loading,
  onClose,
  onSubmit,
}: {
  memory: Memory | null
  open: boolean
  loading: boolean
  onClose: () => void
  onSubmit: (payload: MemoryPayload) => void
}) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')

  useEffect(() => {
    if (!memory) return
    setTitle(memory.title)
    setContent(memory.content)
  }, [memory])

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>编辑记忆</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField label="标题" value={title} onChange={(event) => setTitle(event.target.value)} fullWidth />
          <TextField label="内容" value={content} onChange={(event) => setContent(event.target.value)} multiline minRows={6} fullWidth />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>取消</Button>
        <Button
          variant="contained"
          disabled={loading || !title.trim() || !content.trim()}
          onClick={() =>
            onSubmit({
              title: title.trim(),
              content: content.trim(),
            })
          }
        >
          保存
        </Button>
      </DialogActions>
    </Dialog>
  )
}
