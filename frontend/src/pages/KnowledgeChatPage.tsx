import { Box, Button } from '@mui/material'

import { ChatInput } from '../components/chat/ChatInput'
import { ChatMessageList } from '../components/chat/ChatMessageList'
import { ErrorState } from '../components/common/ErrorState'
import { LoadingState } from '../components/common/LoadingState'
import { useChatMessages, useClearChatMessages, useSendChatMessage } from '../hooks/useChat'

export function KnowledgeChatPage() {
  const { data = [], isLoading, isError } = useChatMessages()
  const sendMutation = useSendChatMessage()
  const clearMutation = useClearChatMessages()

  if (isLoading) return <LoadingState label="正在加载对话历史..." />
  if (isError) return <ErrorState message="对话历史加载失败" />

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="outlined"
          onClick={() => clearMutation.mutate()}
          disabled={clearMutation.isPending}
          sx={{ borderRadius: 999 }}
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

      <Box sx={{ flexShrink: 0 }}>
        <ChatInput onSend={(message) => sendMutation.mutateAsync(message)} disabled={sendMutation.isPending} />
      </Box>
    </Box>
  )
}
