import { Alert, Box, Button, CircularProgress, Paper, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'

import { usePrompt, useResetPrompt, useUpdatePrompt } from '../../hooks/usePrompt'

interface PromptEditorProps {
  promptKey: string
}

export function PromptEditor({ promptKey }: PromptEditorProps) {
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
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (error) {
      console.error('[PromptEditor] Save failed:', error)
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
        setTimeout(() => setSuccessMessage(''), 3000)
      } catch (error) {
        console.error('[PromptEditor] Reset failed:', error)
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
    <Paper sx={{ p: 3 }}>
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
          <Box
            sx={{
              p: 2,
              bgcolor: 'grey.50',
              borderRadius: 1,
              maxHeight: 300,
              overflow: 'auto',
              whiteSpace: 'pre-wrap',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
            }}
          >
            {prompt.content}
          </Box>
        )}
      </Stack>
    </Paper>
  )
}
