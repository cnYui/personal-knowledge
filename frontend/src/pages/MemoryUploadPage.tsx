import { Alert, Stack } from '@mui/material'
import { useState } from 'react'

import { PageHeader } from '../components/common/PageHeader'
import { UploadForm } from '../components/upload/UploadForm'
import { useUploadMemory } from '../hooks/useUploadMemory'

export function MemoryUploadPage() {
  const mutation = useUploadMemory()
  const [success, setSuccess] = useState('')

  return (
    <Stack spacing={3}>
      <PageHeader title="记忆上传" description="上传文本和图片；标题由后端异步抽取后在记忆管理页面自动更新。" />
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
  )
}
