import { Alert, Button, Stack } from '@mui/material'

import { ChatInput } from '../components/chat/ChatInput'
import { ChatMessageList } from '../components/chat/ChatMessageList'
import { EmptyChatState } from '../components/chat/EmptyChatState'
import { PageHeader } from '../components/common/PageHeader'
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
    <Stack spacing={3}>
      <PageHeader
        title="知识库对话"
        description="直接提问，让 AI 基于你的学习记忆进行回答。"
        actions={
          <Button variant="outlined" onClick={() => clearMutation.mutate()} disabled={clearMutation.isPending}>
            清空对话
          </Button>
        }
      />
      {sendMutation.isError || clearMutation.isError ? <Alert severity="error">请求失败，请稍后重试。</Alert> : null}
      {data.length === 0 ? <EmptyChatState /> : <ChatMessageList messages={data} loading={sendMutation.isPending} />}
      <ChatInput onSend={(message) => sendMutation.mutate(message)} disabled={sendMutation.isPending} />
    </Stack>
  )
}
