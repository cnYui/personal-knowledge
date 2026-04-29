import { act } from 'react'
import { Root, createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ChatMessage } from '../../types/chat'
import { ChatMessageList } from './ChatMessageList'

const baseMessages: ChatMessage[] = [
  {
    id: 'user-1',
    role: 'user',
    content: '你好',
  },
]

describe('ChatMessageList', () => {
  let container: HTMLDivElement
  let root: Root
  let scrollIntoView: ReturnType<typeof vi.fn>

  beforeEach(() => {
    ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    scrollIntoView = vi.fn()
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    })
  })

  afterEach(async () => {
    await act(async () => {
      root.unmount()
    })
    document.body.removeChild(container)
    ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = false
  })

  it('新增消息时自动滚动到消息列表底部', async () => {
    await act(async () => {
      root.render(<ChatMessageList messages={baseMessages} />)
    })

    expect(scrollIntoView).not.toHaveBeenCalled()

    await act(async () => {
      root.render(
        <ChatMessageList
          messages={[
            ...baseMessages,
            {
              id: 'assistant-1',
              role: 'assistant',
              content: '你好，有什么可以帮你？',
            },
          ]}
        />
      )
    })

    expect(scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'end',
      inline: 'nearest',
    })
  })

  it('带有序列表和加粗语法的回答会继续走 Markdown 渲染', async () => {
    await act(async () => {
      root.render(
        <ChatMessageList
          messages={[
            ...baseMessages,
            {
              id: 'assistant-2',
              role: 'assistant',
              content: '1. **内部结构**\n2. **运行机制**',
              references: [{ type: 'entity', name: 'Agent', summary: '智能体' }],
              sentenceCitations: [],
            },
          ]}
        />
      )
    })

    expect(container.querySelector('ol')).not.toBeNull()
    expect(container.textContent).toContain('内部结构')
    expect(container.textContent).toContain('运行机制')
  })

  it('没有句子级引用和正文引用标记时不展示参考引用', async () => {
    await act(async () => {
      root.render(
        <ChatMessageList
          messages={[
            ...baseMessages,
            {
              id: 'assistant-3',
              role: 'assistant',
              content: '抱歉，根据提供的知识图谱上下文，我没有找到关于这个问题的相关信息。',
              references: [
                { type: 'relationship', fact: 'ORM 是 Object-Relational Mapping 的缩写' },
                { type: 'relationship', fact: 'Nano Banana 是 AI 生图模型' },
              ],
              citationSection: ['ORM 是 Object-Relational Mapping 的缩写', 'Nano Banana 是 AI 生图模型'],
              sentenceCitations: [],
            },
          ]}
        />
      )
    })

    expect(container.textContent).not.toContain('参考引用')
    expect(container.textContent).not.toContain('ORM 是 Object-Relational Mapping 的缩写')
  })

  it('消息已经结束时不再显示处理中状态', async () => {
    await act(async () => {
      root.render(
        <ChatMessageList
          messages={[
            ...baseMessages,
            {
              id: 'assistant-4',
              role: 'assistant',
              content: '最终回答已完成。',
              timeline: [
                {
                  id: 'probe-retrieval',
                  kind: 'retrieval',
                  title: '预检知识库',
                  detail: '先用原始问题做一轮轻量探测。',
                  status: 'started',
                  order: 1,
                },
                {
                  id: 'final-answer',
                  kind: 'answer',
                  title: '最终回答完成',
                  detail: '最终回答已生成完成。',
                  status: 'done',
                  order: 2,
                },
              ],
              isStreaming: false,
            },
          ]}
        />
      )
    })

    expect(container.textContent).not.toContain('处理中')
  })

  it('参考引用会保留正文里的原始编号顺序', async () => {
    await act(async () => {
      root.render(
        <ChatMessageList
          messages={[
            ...baseMessages,
            {
              id: 'assistant-5',
              role: 'assistant',
              content:
                'Claude Code 是一个包含“Claude Code Runtime”的系统。[1]\n\nClaude Code 会向 Claude 发送提示（prompts）进行处理。[3]\n\n在 Claude Code 的语境中，Session 是由本地 Runtime 维护的一次对话。[5]',
              references: [
                { type: 'relationship', fact: '消息中提到的是当前的 Claude Code Runtime，说明该 Runtime 属于 Claude Code。' },
                { type: 'relationship', fact: 'Session 被定义为一段对话状态。' },
                { type: 'relationship', fact: 'Claude Code sends prompts to Claude for processing.' },
                { type: 'relationship', fact: '在编程软件中，窗口被描述为包含于 Session。' },
                { type: 'relationship', fact: '在 Claude Code 或 Agent SDK 的语境里，Session 是由本地 Runtime 维护的一次对话。' },
              ],
              citationSection: [
                '消息中提到的是当前的 Claude Code Runtime，说明该 Runtime 属于 Claude Code。',
                'Session 被定义为一段对话状态。',
                'Claude Code sends prompts to Claude for processing.',
                '在编程软件中，窗口被描述为包含于 Session。',
                '在 Claude Code 或 Agent SDK 的语境里，Session 是由本地 Runtime 维护的一次对话。',
              ],
              sentenceCitations: [],
            },
          ]}
        />
      )
    })

    const text = container.textContent ?? ''
    const referenceSection = text.slice(text.indexOf('参考引用'))

    expect(referenceSection).toContain('[1] 消息中提到的是当前的 Claude Code Runtime，说明该 Runtime 属于 Claude Code。')
    expect(referenceSection).toContain('[3] Claude Code sends prompts to Claude for processing.')
    expect(referenceSection).toContain('[5] 在 Claude Code 或 Agent SDK 的语境里，Session 是由本地 Runtime 维护的一次对话。')
    expect(referenceSection).not.toContain('[2] Session 被定义为一段对话状态。')
    expect(referenceSection.indexOf('[1]')).toBeLessThan(referenceSection.indexOf('[3]'))
    expect(referenceSection.indexOf('[3]')).toBeLessThan(referenceSection.indexOf('[5]'))
  })
})
