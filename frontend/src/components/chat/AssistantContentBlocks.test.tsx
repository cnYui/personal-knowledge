import { act } from 'react'
import { Root, createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { ChatContentBlock } from '../../types/chat'
import { AssistantContentBlocks } from './AssistantContentBlocks'

describe('AssistantContentBlocks', () => {
  let container: HTMLDivElement
  let root: Root

  beforeEach(() => {
    ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
  })

  afterEach(async () => {
    await act(async () => {
      root.unmount()
    })
    document.body.removeChild(container)
    ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = false
  })

  it('会把 tool_use 和 tool_result 渲染成一张工具卡片', async () => {
    const blocks: ChatContentBlock[] = [
      {
        type: 'tool_use',
        id: 'tool-1',
        name: 'graph_retrieval_tool',
        input: { query: '向量空间' },
        title: '检索知识图谱',
        order: 1,
      },
      {
        type: 'tool_result',
        id: 'tool-1:result',
        tool_use_id: 'tool-1',
        status: 'done',
        output: { summary: '命中 2 条证据' },
        is_error: false,
        order: 2,
      },
    ]

    await act(async () => {
      root.render(<AssistantContentBlocks blocks={blocks} />)
    })

    expect(container.textContent).toContain('检索知识图谱')
    expect(container.textContent).toContain('命中 2 条证据')
  })
})
