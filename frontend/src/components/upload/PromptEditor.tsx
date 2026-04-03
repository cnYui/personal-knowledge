import { Alert, Box, Button, CircularProgress, Paper, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'

import { useAppToast } from '../common/AppToastProvider'
import { usePrompt, useResetPrompt, useUpdatePrompt } from '../../hooks/usePrompt'
import { normalizeApiError } from '../../services/apiClient'

interface PromptEditorProps {
  promptKey: string
}

export function PromptEditor({ promptKey }: PromptEditorProps) {
  const { showToast } = useAppToast()
  const { data: prompt, isLoading, isError } = usePrompt(promptKey)
  const updateMutation = useUpdatePrompt(promptKey)
  const resetMutation = useResetPrompt(promptKey)

  const [editedContent, setEditedContent] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')

  const handleEdit = () => {
    console.log('[PromptEditor] Starting edit mode')
    if (prompt) {
      console.log('[PromptEditor] Current prompt length:', prompt.content.length)
      setEditedContent(prompt.content)
      setIsEditing(true)
      setSuccessMessage('')
    }
  }

  const handleCancel = () => {
    console.log('[PromptEditor] Canceling edit')
    setIsEditing(false)
    setEditedContent('')
    setSuccessMessage('')
  }

  const handleSave = async () => {
    console.log('[PromptEditor] Saving prompt...')
    console.log('[PromptEditor] New content length:', editedContent.length)
    try {
      await updateMutation.mutateAsync({ content: editedContent })
      console.log('[PromptEditor] Save successful')
      setIsEditing(false)
      setSuccessMessage('提示词已保存')
      showToast({ severity: 'success', message: '提示词已保存，并会在后续请求中立即生效。' })
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (error) {
      console.error('[PromptEditor] Save failed:', error)
      const apiError = normalizeApiError(error)
      showToast({ severity: 'error', message: apiError.message })
    }
  }

  const handleReset = async () => {
    if (window.confirm('确定要恢复默认提示词吗？')) {
      console.log('[PromptEditor] Resetting to default...')
      try {
        await resetMutation.mutateAsync()
        console.log('[PromptEditor] Reset successful')
        setIsEditing(false)
        setEditedContent('')
        setSuccessMessage('已恢复默认提示词')
        showToast({ severity: 'success', message: '提示词已恢复默认值。' })
        setTimeout(() => setSuccessMessage(''), 3000)
      } catch (error) {
        console.error('[PromptEditor] Reset failed:', error)
        const apiError = normalizeApiError(error)
        showToast({ severity: 'error', message: apiError.message })
      }
    }
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (isError || !prompt) {
    return <Alert severity="error">加载提示词失败</Alert>
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
      <Stack spacing={2}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h6">优化提示词配置</Typography>
            {prompt.description && (
              <Typography variant="body2" color="text.secondary">
                {prompt.description}
              </Typography>
            )}
          </Box>
          {!isEditing && (
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button variant="outlined" size="small" onClick={handleEdit}>
                编辑
              </Button>
              <Button
                variant="outlined"
                size="small"
                color="warning"
                onClick={handleReset}
                disabled={resetMutation.isPending}
              >
                恢复默认
              </Button>
            </Box>
          )}
        </Box>

        {successMessage && <Alert severity="success">{successMessage}</Alert>}

        {updateMutation.isError && <Alert severity="error">保存失败，请稍后重试</Alert>}

        {resetMutation.isError && <Alert severity="error">恢复默认失败，请稍后重试</Alert>}

        {isEditing ? (
          <>
            <TextField
              label="提示词内容"
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              multiline
              minRows={12}
              maxRows={20}
              fullWidth
              placeholder="输入提示词内容..."
              InputProps={{
                sx: {
                  '& textarea': {
                    fontFamily: 'inherit',
                    fontSize: '1rem',
                    lineHeight: 1.8,
                    color: 'text.primary',
                  },
                },
              }}
            />
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
              <Button variant="outlined" onClick={handleCancel} disabled={updateMutation.isPending}>
                取消
              </Button>
              <Button
                variant="contained"
                onClick={handleSave}
                disabled={updateMutation.isPending || !editedContent.trim()}
              >
                {updateMutation.isPending ? '保存中...' : '保存'}
              </Button>
            </Box>
          </>
        ) : (
          <TextField
            label="提示词内容"
            value={prompt.content}
            multiline
            minRows={12}
            maxRows={20}
            fullWidth
            InputProps={{
              readOnly: true,
              sx: {
                '& textarea': {
                  fontFamily: 'inherit',
                  fontSize: '1rem',
                  lineHeight: 1.8,
                  color: 'text.primary',
                },
              },
            }}
          />
        )}
      </Stack>
    </Paper>
  )
}
