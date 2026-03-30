import { Alert, Button, Stack, TextField, Box, CircularProgress } from '@mui/material'
import { useState } from 'react'

import { UploadMemoryInput } from '../../types/upload'
import { optimizeText } from '../../services/textApi'
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
  const [optimizing, setOptimizing] = useState(false)

  const handleOptimize = async () => {
    console.log('[UploadForm] Starting text optimization...')
    if (!content.trim()) {
      console.warn('[UploadForm] No content to optimize')
      setError('请先填写文本内容')
      return
    }
    console.log('[UploadForm] Content length:', content.length)
    setError('')
    setOptimizing(true)
    try {
      const optimized = await optimizeText(content.trim())
      console.log('[UploadForm] Optimization complete, updating content')
      setContent(optimized)
    } catch (err) {
      console.error('[UploadForm] Optimization error:', err)
      setError('文本优化失败，请稍后重试')
    } finally {
      setOptimizing(false)
    }
  }

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
      <Box sx={{ position: 'relative' }}>
        <TextField label="文本内容" value={content} onChange={(event) => setContent(event.target.value)} multiline minRows={8} fullWidth />
        <Button
          variant="outlined"
          onClick={handleOptimize}
          disabled={optimizing || loading || !content.trim()}
          sx={{ position: 'absolute', top: 8, right: 8 }}
          startIcon={optimizing ? <CircularProgress size={16} /> : null}
        >
          {optimizing ? '优化中...' : '一键优化'}
        </Button>
      </Box>
      <ImageUploadPanel files={images} onChange={setImages} />
      <Button variant="contained" onClick={handleSubmit} disabled={loading}>
        {loading ? '上传中...' : '上传记忆'}
      </Button>
    </Stack>
  )
}
