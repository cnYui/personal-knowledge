import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, useEffect, useRef } from 'react'
import { createRoot, Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppToastProvider } from '../components/common/AppToastProvider'
import { loadMessagesFromStorage } from '../services/chatApi'
import { useSendChatMessage } from './useChat'

vi.mock('../services/chatApi', async () => {
  const actual = await vi.importActual('../services/chatApi')
  return {
    ...actual,
    sendChatMessageStream: vi.fn(),
  }
})

function SendOnMount({ message }: { message: string }) {
  const mutation = useSendChatMessage()
  const sentRef = useRef(false)

  useEffect(() => {
    if (sentRef.current) {
      return
    }
    sentRef.current = true
    void mutation.mutateAsync(message).catch(() => {})
  }, [message, mutation])

  return null
}

describe('useSendChatMessage', () => {
  let container: HTMLDivElement
  let root: Root | null = null
  const reactActEnvironment = globalThis as typeof globalThis & {
    IS_REACT_ACT_ENVIRONMENT?: boolean
  }

  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true
    vi.useFakeTimers()
    localStorage.clear()
    container = document.createElement('div')
    document.body.appendChild(container)
  })

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root?.unmount()
      })
      root = null
    }

    container.remove()
    localStorage.clear()
    vi.clearAllMocks()
    vi.useRealTimers()
    delete reactActEnvironment.IS_REACT_ACT_ENVIRONMENT
  })

  it('流式过程中失败时会保留已有正文并结束 assistant loading', async () => {
    const { sendChatMessageStream } = await import('../services/chatApi')
    const sendMock = vi.mocked(sendChatMessageStream)
    const queryClient = new QueryClient()

    sendMock.mockImplementation(
      async (
        _message,
        onChunk,
        _onRefs,
        _onCitation,
        _onSentence,
        onTimeline,
        _onTrace,
        _onToolUse,
        _onToolResult,
        _onComplete,
        onError
      ) => {
        onTimeline({
          id: 'understand-question',
          kind: 'understand',
          title: '理解问题',
          detail: '正在理解你的问题。',
          status: 'started',
          order: 1,
        })
        onChunk('已经生成了一部分回答')

        return new Promise<void>((resolve) => {
          setTimeout(() => {
            onError({
              error_code: 'MODEL_API_UPSTREAM_ERROR',
              message: '模型服务暂时不可用，请稍后重试。',
              retryable: true,
            })
            resolve()
          }, 120)
        })
      }
    )

    root = createRoot(container)

    await act(async () => {
      root?.render(
        <QueryClientProvider client={queryClient}>
          <AppToastProvider>
            <SendOnMount message="测试问题" />
          </AppToastProvider>
        </QueryClientProvider>
      )
    })

    await act(async () => {
      vi.advanceTimersByTime(72)
      await Promise.resolve()
    })

    await act(async () => {
      vi.advanceTimersByTime(120)
      await Promise.resolve()
      await Promise.resolve()
    })

    const messages = loadMessagesFromStorage()
    const assistant = messages[messages.length - 1]

    expect(assistant.role).toBe('assistant')
    expect(assistant.isStreaming).toBe(false)
    expect(assistant.content).toContain('已经生成了')
    expect(assistant.content).toContain('模型服务暂时不可用，请稍后重试。')
    expect(assistant.timeline?.[0]?.title).toBe('理解问题')
  })

  it('没有正文时会把错误文案直接写入 assistant 消息', async () => {
    const { sendChatMessageStream } = await import('../services/chatApi')
    const queryClient = new QueryClient()

    vi.mocked(sendChatMessageStream).mockImplementation(
      async (
        _message,
        _onChunk,
        _onRefs,
        _onCitation,
        _onSentence,
        _onTimeline,
        _onTrace,
        _onToolUse,
        _onToolResult,
        _onComplete,
        onError
      ) => {
        onError({
          error_code: 'UNKNOWN_ERROR',
          message: '请求失败，请稍后重试。',
        })
      }
    )

    root = createRoot(container)

    await act(async () => {
      root?.render(
        <QueryClientProvider client={queryClient}>
          <AppToastProvider>
            <SendOnMount message="测试问题" />
          </AppToastProvider>
        </QueryClientProvider>
      )
      await Promise.resolve()
    })

    await act(async () => {
      vi.runOnlyPendingTimers()
      await Promise.resolve()
      await Promise.resolve()
    })

    const messages = loadMessagesFromStorage()
    const assistant = messages[messages.length - 1]

    expect(assistant.content).toBe('错误: 请求失败，请稍后重试。')
    expect(assistant.isStreaming).toBe(false)
  })

  it('会把 markdown 增量和工具事件写入 contentBlocks', async () => {
    const { sendChatMessageStream } = await import('../services/chatApi')
    const queryClient = new QueryClient()

    vi.mocked(sendChatMessageStream).mockImplementation(
      async (_message, onChunk, _onRefs, _onCitation, _onSentence, _onTimeline, _onTrace, onToolUse, onToolResult, onComplete) => {
        onToolUse({
          id: 'tool-1',
          name: 'graph_retrieval_tool',
          input: { query: '向量空间' },
          title: '检索知识图谱',
          order: 1,
        })
        onToolResult({
          tool_use_id: 'tool-1',
          status: 'done',
          output: { summary: '命中 2 条证据' },
          is_error: false,
          order: 2,
        })
        onChunk('最终回答')
        onComplete('最终回答')
      }
    )

    root = createRoot(container)

    await act(async () => {
      root?.render(
        <QueryClientProvider client={queryClient}>
          <AppToastProvider>
            <SendOnMount message="测试问题" />
          </AppToastProvider>
        </QueryClientProvider>
      )
      await Promise.resolve()
    })

    const messages = loadMessagesFromStorage()
    const assistant = messages[messages.length - 1]

    expect(assistant.content).toBe('最终回答')
    expect(assistant.contentBlocks).toEqual([
      expect.objectContaining({ type: 'tool_use', id: 'tool-1' }),
      expect.objectContaining({ type: 'tool_result', tool_use_id: 'tool-1' }),
      expect.objectContaining({ type: 'markdown', text: '最终回答' }),
    ])
  })

  it('流式完成时会收尾仍处于 started 的时间线步骤', async () => {
    const { sendChatMessageStream } = await import('../services/chatApi')
    const queryClient = new QueryClient()

    vi.mocked(sendChatMessageStream).mockImplementation(
      async (_message, onChunk, _onRefs, _onCitation, _onSentence, onTimeline, _onTrace, _onToolUse, _onToolResult, onComplete) => {
        onTimeline({
          id: 'probe-retrieval',
          kind: 'retrieval',
          title: '预检知识库',
          detail: '先用原始问题做一轮轻量探测。',
          status: 'started',
          order: 1,
        })
        onChunk('最终回答')
        onComplete('最终回答')
      }
    )

    root = createRoot(container)

    await act(async () => {
      root?.render(
        <QueryClientProvider client={queryClient}>
          <AppToastProvider>
            <SendOnMount message="测试问题" />
          </AppToastProvider>
        </QueryClientProvider>
      )
      await Promise.resolve()
    })

    await act(async () => {
      vi.runOnlyPendingTimers()
      await Promise.resolve()
      await Promise.resolve()
    })

    const messages = loadMessagesFromStorage()
    const assistant = messages[messages.length - 1]
    const probeEvent = assistant.timeline?.find((event) => event.id === 'probe-retrieval')

    expect(assistant.isStreaming).toBe(false)
    expect(probeEvent?.status).toBe('done')
  })
})
