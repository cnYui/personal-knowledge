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

    await sendChatMessageStream('你好', vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), onError)

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

  it('sendChatMessageStream 会解析 tool_use 和 tool_result 事件', async () => {
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            [
              'data: {"type":"tool_use","content":{"id":"tool-1","name":"graph_retrieval_tool","input":{"query":"向量空间"},"title":"检索知识图谱","order":10}}',
              '',
              'data: {"type":"tool_result","content":{"tool_use_id":"tool-1","status":"done","output":{"summary":"命中 2 条证据"},"is_error":false,"order":11}}',
              '',
              'data: {"type":"content","content":"最终回答"}',
              '',
              'data: {"type":"done","content":""}',
              '',
            ].join('\n')
          )
        )
        controller.close()
      },
    })

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(stream, {
          status: 200,
          headers: { 'content-type': 'text/event-stream' },
        })
      )
    )

    const onToolUse = vi.fn()
    const onToolResult = vi.fn()
    const onChunk = vi.fn()
    const onComplete = vi.fn()

    await sendChatMessageStream(
      '你好',
      onChunk,
      vi.fn(),
      vi.fn(),
      vi.fn(),
      vi.fn(),
      vi.fn(),
      onToolUse,
      onToolResult,
      onComplete,
      vi.fn()
    )

    expect(onToolUse).toHaveBeenCalledWith({
      id: 'tool-1',
      name: 'graph_retrieval_tool',
      input: { query: '向量空间' },
      title: '检索知识图谱',
      order: 10,
    })
    expect(onToolResult).toHaveBeenCalledWith({
      tool_use_id: 'tool-1',
      status: 'done',
      output: { summary: '命中 2 条证据' },
      is_error: false,
      order: 11,
    })
    expect(onChunk).toHaveBeenCalledWith('最终回答')
    expect(onComplete).toHaveBeenCalledWith('最终回答')
  })

  it('clearChatMessages 会清空本地聊天记录', async () => {
    localStorage.setItem('pkb-chat-messages', JSON.stringify([{ id: '1', role: 'user', content: 'hi' }]))

    await clearChatMessages()

    expect(localStorage.getItem('pkb-chat-messages')).toBeNull()
  })
})
