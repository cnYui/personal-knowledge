import { Box } from '@mui/material'

import { ChatInput } from '../components/chat/ChatInput'
import { ChatMessageList } from '../components/chat/ChatMessageList'
import { ErrorState } from '../components/common/ErrorState'
import { LoadingState } from '../components/common/LoadingState'
import { useChatMessages, useSendChatMessage } from '../hooks/useChat'

export function KnowledgeChatPage() {
  const { data = [], isLoading, isError } = useChatMessages()
  const sendMutation = useSendChatMessage()

  if (isLoading) return <LoadingState label="正在加载对话历史..." />
  if (isError) return <ErrorState message="对话历史加载失败" />

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
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
    </Box>
  )
}
