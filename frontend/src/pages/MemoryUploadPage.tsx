import { Alert, Box, Stack, Typography } from '@mui/material'
import { useState } from 'react'

import { useAppToast } from '../components/common/AppToastProvider'
import { PromptEditor } from '../components/upload/PromptEditor'
import { UploadForm } from '../components/upload/UploadForm'
import { useUploadMemory } from '../hooks/useUploadMemory'
import { normalizeApiError } from '../services/http'

export function MemoryUploadPage() {
  const mutation = useUploadMemory()
  const { showToast } = useAppToast()
  const [success, setSuccess] = useState('')

  return (
    <Box sx={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', pr: 1 }}>
        <Stack spacing={3.5}>
          {success ? <Alert severity="success">{success}</Alert> : null}
          {mutation.isError ? <Alert severity="error">上传失败，请稍后重试。</Alert> : null}
          <UploadForm
            loading={mutation.isPending}
            onSubmit={async (payload) => {
              try {
                const response = await mutation.mutateAsync(payload)
                setSuccess(`上传成功，共处理 ${response.images_count} 张图片。`)
                showToast({ severity: 'success', message: '记忆上传成功，知识库构建任务已开始处理。' })
              } catch (error) {
                const apiError = normalizeApiError(error)
                showToast({
                  severity: apiError.error_code === 'MODEL_API_KEY_MISSING' ? 'warning' : 'error',
                  message: apiError.message,
                })
                throw error
              }
            }}
          />

          <PromptEditor promptKey="text_optimization" />
        </Stack>
      </Box>
    </Box>
  )
}
