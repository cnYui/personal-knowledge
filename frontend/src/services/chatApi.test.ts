import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearChatMessages, sendChatMessageStream } from './chatApi'

describe('chatApi', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('sendChatMessageStream 继续使用统一 URL，并把 HTTP 错误转成 ApiErrorPayload', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ message: 'missing key', error_code: 'MODEL_API_KEY_MISSING' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        })
      )
    )

    const onError = vi.fn()

    await sendChatMessageStream('你好', vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), onError)

    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/chat/stream',
      expect.objectContaining({
        method: 'POST',
      })
    )
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        error_code: 'MODEL_API_KEY_MISSING',
        message: 'missing key',
      })
    )
  })

  it('clearChatMessages 会清空本地聊天记录', async () => {
    localStorage.setItem('pkb-chat-messages', JSON.stringify([{ id: '1', role: 'user', content: 'hi' }]))

    await clearChatMessages()

    expect(localStorage.getItem('pkb-chat-messages')).toBeNull()
  })
})
