import { Alert, Box, Button, CircularProgress, Paper, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'

import { useAppToast } from '../common/AppToastProvider'
import { UploadMemoryInput } from '../../types/upload'
import { normalizeApiError } from '../../services/apiClient'
import { optimizeText } from '../../services/textApi'
import { ImageUploadPanel } from './ImageUploadPanel'

export function UploadForm({
  onSubmit,
  loading,
}: {
  onSubmit: (payload: UploadMemoryInput) => Promise<void>
  loading: boolean
}) {
  const { showToast } = useAppToast()
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
      const apiError = normalizeApiError(err)
      setError(apiError.message)
      showToast({
        severity: apiError.error_code === 'MODEL_API_KEY_MISSING' ? 'warning' : 'error',
        message: apiError.message,
      })
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
    <Paper
      sx={{
        p: 3,
        borderRadius: 0.9,
        border: '1px solid',
        borderColor: 'divider',
        boxShadow: '0 16px 34px rgba(20, 20, 19, 0.05)',
        background: 'linear-gradient(180deg, #fffdf8 0%, #f6f2e8 100%)',
      }}
    >
      <Stack spacing={2.5}>
        <Box>
          <Typography variant="h6">上传记忆内容</Typography>
          <Typography variant="body2" color="text.secondary">
            输入文本、补充图片，然后将整理后的内容写入你的知识库。
          </Typography>
        </Box>

        {error ? <Alert severity="error">{error}</Alert> : null}

        <Box sx={{ position: 'relative' }}>
          <TextField
            label="文本内容"
            value={content}
            onChange={(event) => setContent(event.target.value)}
            multiline
            minRows={8}
            fullWidth
            InputProps={{
              sx: {
                alignItems: 'stretch',
                '& textarea': {
                  pb: 7,
                },
              },
            }}
          />
          <Button
            variant="outlined"
            onClick={handleOptimize}
            disabled={optimizing || loading || !content.trim()}
            sx={{
              position: 'absolute',
              right: 14,
              bottom: 14,
              borderRadius: 0.75,
              minWidth: 116,
              backgroundColor: 'rgba(250, 249, 245, 0.92)',
            }}
            startIcon={optimizing ? <CircularProgress size={16} /> : null}
          >
            {optimizing ? '优化中...' : '一键优化'}
          </Button>
        </Box>

        <ImageUploadPanel files={images} onChange={setImages} />

        <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button variant="contained" onClick={handleSubmit} disabled={loading} sx={{ minWidth: 132, borderRadius: 0.75 }}>
            {loading ? '上传中...' : '上传记忆'}
          </Button>
        </Box>
      </Stack>
    </Paper>
  )
}
