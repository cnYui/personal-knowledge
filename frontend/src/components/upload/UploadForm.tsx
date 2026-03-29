import { Alert, Button, Stack, TextField } from '@mui/material'
import { useState } from 'react'

import { UploadMemoryInput } from '../../types/upload'
import { ImageUploadPanel } from './ImageUploadPanel'

export function UploadForm({
  onSubmit,
  loading,
}: {
  onSubmit: (payload: UploadMemoryInput) => Promise<void>
  loading: boolean
}) {
  const [content, setContent] = useState('')
  const [images, setImages] = useState<File[]>([])
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!content.trim()) {
      setError('请先填写记忆内容')
      return
    }
    setError('')
    await onSubmit({
      content: content.trim(),
      images,
    })
    setContent('')
    setImages([])
  }

  return (
    <Stack spacing={2}>
      {error ? <Alert severity="error">{error}</Alert> : null}
      <TextField label="文本内容" value={content} onChange={(event) => setContent(event.target.value)} multiline minRows={8} fullWidth />
      <ImageUploadPanel files={images} onChange={setImages} />
      <Button variant="contained" onClick={handleSubmit} disabled={loading}>
        {loading ? '上传中...' : '上传记忆'}
      </Button>
    </Stack>
  )
}
