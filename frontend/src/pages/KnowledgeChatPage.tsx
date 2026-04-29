import DeleteSweepIcon from '@mui/icons-material/DeleteSweep'
import { Box, Button } from '@mui/material'
import { useState } from 'react'

import { ChatInput } from '../components/chat/ChatInput'
import { ChatMessageList } from '../components/chat/ChatMessageList'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { useAppToast } from '../components/common/AppToastProvider'
import { ErrorState } from '../components/common/ErrorState'
import { LoadingState } from '../components/common/LoadingState'
import { useChatMessages, useClearChatMessages, useSendChatMessage } from '../hooks/useChat'

export function KnowledgeChatPage() {
  const { showToast } = useAppToast()
  const [clearDialogOpen, setClearDialogOpen] = useState(false)
  const { data = [], isLoading, isError } = useChatMessages()
  const sendMutation = useSendChatMessage()
  const clearMutation = useClearChatMessages()

  if (isLoading) return <LoadingState label="正在加载对话历史..." />
  if (isError) return <ErrorState message="对话历史加载失败" />

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          color="error"
          variant="outlined"
          startIcon={<DeleteSweepIcon />}
          disabled={data.length === 0 || sendMutation.isPending || clearMutation.isPending}
          onClick={() => setClearDialogOpen(true)}
        >
          清空对话
        </Button>
      </Box>

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          overflow: 'auto',
          pr: 1,
        }}
      >
        <ChatMessageList
          messages={data}
        />
      </Box>

      <Box
        sx={{
          flexShrink: 0,
          width: { xs: '100%', md: 720 },
          alignSelf: 'center',
        }}
      >
        <ChatInput onSend={(message) => sendMutation.mutateAsync(message)} disabled={sendMutation.isPending} />
      </Box>

      <ConfirmDialog
        open={clearDialogOpen}
        title="清空对话"
        description="删除后将清空当前页面的全部聊天内容，确认继续吗？"
        onClose={() => {
          setClearDialogOpen(false)
        }}
        onConfirm={async () => {
          try {
            await clearMutation.mutateAsync()
            setClearDialogOpen(false)
            showToast({ severity: 'success', message: '聊天记录已清空' })
          } catch {
            showToast({ severity: 'error', message: '清空失败，请稍后重试' })
          }
        }}
      />
    </Box>
  )
}
