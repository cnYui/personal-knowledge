import { Alert, Box, Stack } from '@mui/material'
import { useState } from 'react'

import { PromptEditor } from '../components/upload/PromptEditor'
import { UploadForm } from '../components/upload/UploadForm'
import { useUploadMemory } from '../hooks/useUploadMemory'

export function MemoryUploadPage() {
  const mutation = useUploadMemory()
  const [success, setSuccess] = useState('')

  return (
    <Box sx={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', pr: 1 }}>
        <Stack spacing={3}>
          <PromptEditor promptKey="text_optimization" />

          {success ? <Alert severity="success">{success}</Alert> : null}
          {mutation.isError ? <Alert severity="error">上传失败，请稍后重试。</Alert> : null}
          <UploadForm
            loading={mutation.isPending}
            onSubmit={async (payload) => {
              const response = await mutation.mutateAsync(payload)
              setSuccess(`上传成功，共处理 ${response.images_count} 张图片。`)
            }}
          />
        </Stack>
      </Box>
    </Box>
  )
}
