import '@testing-library/jest-dom/vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, beforeEach } from 'vitest'

const { useChatMessages, useSendChatMessage, useClearChatMessages } = vi.hoisted(() => ({
  useChatMessages: vi.fn(),
  useSendChatMessage: vi.fn(),
  useClearChatMessages: vi.fn(),
}))
const { useAppToast } = vi.hoisted(() => ({
  useAppToast: vi.fn(),
}))

vi.mock('../hooks/useChat', () => ({
  useChatMessages,
  useSendChatMessage,
  useClearChatMessages,
}))
vi.mock('../components/common/AppToastProvider', () => ({
  useAppToast,
}))

import { KnowledgeChatPage } from './KnowledgeChatPage'

describe('KnowledgeChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useSendChatMessage.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
    })
    useClearChatMessages.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({ success: true }),
      isPending: false,
      isError: false,
    })
    useAppToast.mockReturnValue({
      showToast: vi.fn(),
    })
  })

  it('清空对话前会先二次确认，取消时不删除，确认后才清空全部聊天记录', async () => {
    const user = userEvent.setup()
    const clearMutation = vi.fn().mockResolvedValue({ success: true })

    useChatMessages.mockReturnValue({
      data: [
        { id: 'user-1', role: 'user', content: '你好', created_at: '2026-04-29T00:00:00.000Z' },
        { id: 'assistant-1', role: 'assistant', content: '你好', created_at: '2026-04-29T00:00:01.000Z' },
      ],
      isLoading: false,
      isError: false,
    })
    useClearChatMessages.mockReturnValue({
      mutateAsync: clearMutation,
      isPending: false,
      isError: false,
    })

    render(<KnowledgeChatPage />)

    await user.click(screen.getByRole('button', { name: '清空对话' }))

    expect(screen.getByText('删除后将清空当前页面的全部聊天内容，确认继续吗？')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '取消' }))

    expect(clearMutation).not.toHaveBeenCalled()
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '清空对话' }))
    await user.click(screen.getByRole('button', { name: '确认' }))

    expect(clearMutation).toHaveBeenCalledTimes(1)
  })
})
