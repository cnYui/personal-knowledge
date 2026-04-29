# Chat 分层消息协议剩余实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐聊天正文层 `tool_use/tool_result` 内联工具卡片，并同时修复当前 chat 页的引用误显、思考过程状态未结束、Markdown 误渲染问题。

**Architecture:** 保留现有 `timeline/trace` 思考过程链路，在前端新增 `contentBlocks` 作为正文层；后端在 tool loop 与 stream 转发层补发 `tool_use/tool_result`。另外对引用输出、timeline 收尾和 Markdown 判定做最小必要修正，避免继续把错误行为带进新协议。

**Tech Stack:** React 18、TypeScript、MUI、Vitest、FastAPI、pytest、现有 SSE fetch 解析。

---

## 当前差异

当前代码与规格差异：

1. 没有 `contentBlocks`、`tool_use/tool_result` 类型和 SSE 解析。
2. `ChatMessageList` 只有 Markdown/句级引用渲染，没有工具卡片入口。
3. `ToolLoopEngine` 不发工具 runtime event，`ChatService.rag_stream` 不转发工具 SSE。
4. `probe-retrieval` 与 `probe-retrieval-retry` 只发 `started`，没有配对 `done/error`。
5. `direct_general_answer` / `no_hit` 情况下，probe 阶段写入的引用仍可能进入 `references/citation_section`。
6. `looksLikeMarkdown` 没识别有序列表和强调语法，导致带引用时会错误进入句子模式。

## 文件结构

前端类型与消费：

- Modify: `frontend/src/types/chat.ts`
- Modify: `frontend/src/services/chatApi.ts`
- Modify: `frontend/src/services/chatApi.test.ts`
- Modify: `frontend/src/hooks/useChat.ts`
- Modify: `frontend/src/hooks/useChat.test.tsx`

前端渲染：

- Create: `frontend/src/components/chat/ToolCallBlock.tsx`
- Create: `frontend/src/components/chat/AssistantContentBlocks.tsx`
- Modify: `frontend/src/components/chat/ChatMessageList.tsx`
- Create: `frontend/src/components/chat/AssistantContentBlocks.test.tsx`

后端事件与引用收口：

- Modify: `backend/app/workflow/engine/tool_loop.py`
- Modify: `backend/app/workflow/nodes/agent_node.py`
- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/tests/workflow/engine/test_tool_loop.py`
- Modify: `backend/tests/test_chat_api.py`

上下文：

- Modify: `docs/superpowers/specs/2026-04-29-chat-layered-protocol-design.md`
- Modify: `docs/ai/context/2026-04-29-chat-layered-protocol.md`
- Modify: `AGENTS.md`

验证命令：

- Frontend unit: `cd frontend && npm run test -- src/services/chatApi.test.ts src/hooks/useChat.test.tsx src/components/chat/AssistantContentBlocks.test.tsx`
- Frontend build: `cd frontend && npm run build`
- Backend unit: `cd backend && pytest tests/workflow/engine/test_tool_loop.py tests/test_chat_api.py -q`

## 实施约束

1. `content` 只保存 Markdown 正文，不得混入工具输入输出。
2. 工具卡片只由 `tool_use/tool_result` 事件驱动，不能从 `timeline` 反推。
3. `ThinkingProcess` 不新增 raw thinking 展示分支。
4. `direct_general_answer` 或无图谱证据时，不展示参考引用。
5. 所有会显示“处理中”的 timeline 事件都必须有明确结束态，不能靠前端猜测。
6. Markdown 判定修正后，只有纯文本答案才允许走句子模式；有列表、强调、标题、代码块等 Markdown 语法时必须走 `MarkdownContent`。

### Task 1: 前端补齐正文层事件类型与 SSE 解析

**Files:**
- Modify: `frontend/src/types/chat.ts`
- Modify: `frontend/src/services/chatApi.ts`
- Modify: `frontend/src/services/chatApi.test.ts`

- [ ] **Step 1: 写失败测试，覆盖 `tool_use/tool_result` SSE 解析**

在 `frontend/src/services/chatApi.test.ts` 增加测试：

```ts
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

  await sendChatMessageStream(
    '你好',
    vi.fn(),
    vi.fn(),
    vi.fn(),
    vi.fn(),
    vi.fn(),
    vi.fn(),
    onToolUse,
    onToolResult,
    vi.fn(),
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
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm run test -- src/services/chatApi.test.ts`

Expected: FAIL，`sendChatMessageStream` 还没有 `onToolUse/onToolResult` 参数或回调未触发。

- [ ] **Step 3: 扩展类型**

在 `frontend/src/types/chat.ts` 增加：

```ts
export interface ChatMarkdownBlock {
  type: 'markdown'
  id: string
  text: string
  order: number
}

export interface ChatToolUseBlock {
  type: 'tool_use'
  id: string
  name: string
  input: Record<string, unknown>
  title?: string
  order: number
}

export interface ChatToolResultBlock {
  type: 'tool_result'
  id: string
  tool_use_id: string
  status: 'running' | 'done' | 'error'
  output?: unknown
  is_error?: boolean
  order: number
}

export type ChatContentBlock = ChatMarkdownBlock | ChatToolUseBlock | ChatToolResultBlock
export type ChatToolUseEvent = Omit<ChatToolUseBlock, 'type'>
export type ChatToolResultEvent = Omit<ChatToolResultBlock, 'type' | 'id'>
```

并给 `ChatMessage` 增加：

```ts
contentBlocks?: ChatContentBlock[]
```

- [ ] **Step 4: 扩展 `sendChatMessageStream`**

在 `frontend/src/services/chatApi.ts`：

1. 引入 `ChatToolUseEvent`、`ChatToolResultEvent`。
2. 把函数签名扩展为 `onToolUse`、`onToolResult` 回调在 `onTrace` 和 `onComplete` 之间。
3. 在 SSE 解析分支增加 `tool_use`、`tool_result` 处理。
4. 未知事件继续忽略。

- [ ] **Step 5: 同步旧测试调用参数**

把 `frontend/src/services/chatApi.test.ts` 现有 `sendChatMessageStream` 调用补齐两个 `vi.fn()` 占位。

- [ ] **Step 6: 运行测试确认通过**

Run: `cd frontend && npm run test -- src/services/chatApi.test.ts`

Expected: PASS。

### Task 2: 前端把正文层事件写入 `contentBlocks`

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`
- Modify: `frontend/src/hooks/useChat.test.tsx`

- [ ] **Step 1: 扩展 hook 测试，覆盖 block 写入**

在 `frontend/src/hooks/useChat.test.tsx` 增加测试：

```tsx
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm run test -- src/hooks/useChat.test.tsx`

Expected: FAIL，`contentBlocks` 为空或 `sendChatMessageStream` 参数数量不匹配。

- [ ] **Step 3: 在 `useChat.ts` 增加 block helper**

增加：

```ts
const sortContentBlocks = (blocks: ChatContentBlock[]) => ...
const appendMarkdownBlock = (blocks: ChatContentBlock[] | undefined, chunk: string) => ...
const upsertToolUseBlock = (blocks: ChatContentBlock[] | undefined, event: ChatToolUseEvent) => ...
const upsertToolResultBlock = (blocks: ChatContentBlock[] | undefined, event: ChatToolResultEvent) => ...
```

要求：

1. Markdown 连续增量只合并到最后一个 `markdown` block。
2. `tool_result` 允许先到，后续和 `tool_use` 通过 `tool_use_id` 合并。
3. `contentBlocks` 按 `order` 排序。

- [ ] **Step 4: 初始化 assistant message 的 `contentBlocks`**

把 assistant draft 初始值改为：

```ts
content: '',
contentBlocks: [],
```

- [ ] **Step 5: 同步流式回调**

1. 在 `startTypingLoop` 的 `updateAssistantDraft` 中同步写入 `appendMarkdownBlock(...)`。
2. 在 `sendChatMessageStream` 调用中接入 `onToolUse`、`onToolResult`。
3. 在 `onComplete` 中，如果没有打字缓冲且还没有 Markdown block，用 `fullContent` 补一个 Markdown block。

- [ ] **Step 6: 运行测试确认通过**

Run: `cd frontend && npm run test -- src/hooks/useChat.test.tsx`

Expected: PASS。

### Task 3: 前端渲染工具卡片，并修复 Markdown 误判

**Files:**
- Create: `frontend/src/components/chat/ToolCallBlock.tsx`
- Create: `frontend/src/components/chat/AssistantContentBlocks.tsx`
- Create: `frontend/src/components/chat/AssistantContentBlocks.test.tsx`
- Modify: `frontend/src/components/chat/ChatMessageList.tsx`

- [ ] **Step 1: 写失败测试，覆盖工具卡片与 Markdown 列表**

创建 `frontend/src/components/chat/AssistantContentBlocks.test.tsx`：

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ChatContentBlock } from '../../types/chat'
import { AssistantContentBlocks } from './AssistantContentBlocks'

describe('AssistantContentBlocks', () => {
  it('会把 tool_use 和 tool_result 渲染成一张工具卡片', () => {
    const blocks: ChatContentBlock[] = [
      { type: 'tool_use', id: 'tool-1', name: 'graph_retrieval_tool', input: { query: '向量空间' }, title: '检索知识图谱', order: 1 },
      { type: 'tool_result', id: 'tool-1:result', tool_use_id: 'tool-1', status: 'done', output: { summary: '命中 2 条证据' }, is_error: false, order: 2 },
    ]

    render(<AssistantContentBlocks blocks={blocks} references={[]} />)

    expect(screen.getByText('检索知识图谱')).toBeInTheDocument()
    expect(screen.getByText(/命中 2 条证据/)).toBeInTheDocument()
  })
})
```

并在 `ChatMessageList.tsx` 增加用例或扩展现有组件测试，覆盖：

```ts
content: '1. **内部结构**\n2. **运行机制**'
references: [{ type: 'entity', name: 'Agent' }]
sentenceCitations: []
```

Expected: 应走 `MarkdownContent`，页面上不出现字面量 `**内部结构**`。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm run test -- src/components/chat/AssistantContentBlocks.test.tsx`

Expected: FAIL，组件不存在或渲染结果不符。

- [ ] **Step 3: 创建工具卡片组件**

创建 `ToolCallBlock.tsx`，展示：

1. 工具标题或工具名。
2. 运行中/完成/失败状态。
3. 输入摘要。
4. 结果摘要或错误摘要。

- [ ] **Step 4: 创建正文 block 渲染组件**

创建 `AssistantContentBlocks.tsx`：

1. `markdown` block 用 `MarkdownContent`。
2. `tool_use` 查找配对的 `tool_result`，合并为一张卡片。
3. 独立 `tool_result` 渲染为降级工具卡片。

- [ ] **Step 5: 修复 Markdown 判定**

在 `ChatMessageList.tsx`：

1. 扩展 `looksLikeMarkdown`，至少识别有序列表 `^\d+\.`、强调 `**text**`、标题 `# `。
2. 只有纯文本答案才允许句子模式。
3. 若 `message.contentBlocks?.length` 存在，优先走 `AssistantContentBlocks`。

- [ ] **Step 6: 运行前端测试和构建**

Run: `cd frontend && npm run test -- src/components/chat/AssistantContentBlocks.test.tsx src/hooks/useChat.test.tsx src/services/chatApi.test.ts`

Expected: PASS。

Run: `cd frontend && npm run build`

Expected: PASS。

### Task 4: 后端发出 `tool_use/tool_result`，并修复 timeline 收尾

**Files:**
- Modify: `backend/app/workflow/engine/tool_loop.py`
- Modify: `backend/app/workflow/nodes/agent_node.py`
- Modify: `backend/tests/workflow/engine/test_tool_loop.py`
- Modify: `backend/tests/test_chat_api.py`

- [ ] **Step 1: 写失败测试，覆盖工具 runtime event**

在 `backend/tests/workflow/engine/test_tool_loop.py` 增加用例，断言 `event_callback` 收到：

1. `tool_use`
2. `timeline started`
3. `tool_result done`
4. `timeline done`

- [ ] **Step 2: 写失败测试，覆盖 probe timeline 必须结束**

在 `backend/tests/test_chat_api.py` 增加断言：当触发 `probe-retrieval` 或 `probe-retrieval-retry` 时，SSE body 中同一 `id` 必须既有 `started` 也有 `done` 或 `error`，不能只停在 `started`。

- [ ] **Step 3: 在 `tool_loop.py` 发 runtime tool event**

在每次工具调用中补发：

1. 工具开始前 `tool_use`
2. 成功后 `tool_result done`
3. 异常后 `tool_result error`

- [ ] **Step 4: 在 `agent_node.py` 补 probe 的完成态**

对 `probe-retrieval`、`probe-retrieval-retry`：

1. 发出 `started` 后，探测完成必须发 `done`。
2. 若探测异常，发 `error`。
3. `detail` 要包含最终判定：`sufficient`、`insufficient`、`no_hit`。

- [ ] **Step 5: 运行后端测试**

Run: `cd backend && pytest tests/workflow/engine/test_tool_loop.py tests/test_chat_api.py -q`

Expected: PASS。

### Task 5: 后端收敛引用输出，避免无命中时展示参考引用

**Files:**
- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/tests/test_chat_api.py`

- [ ] **Step 1: 写失败测试，覆盖无命中时不展示引用**

在 `backend/tests/test_chat_api.py` 增加或扩展用例：

1. `final_action = 'direct_general_answer'`
2. `reference_store` 中可能存在 probe 阶段写入的 `graph_evidence`

断言最终 SSE body 中：

```py
assert '"type": "references"' in body
assert '"content": []' in body
```

并对 `citation_section`、`sentence_citations` 断言为空数组。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_chat_api.py::test_rag_stream_hides_references_when_no_grounded_evidence -q`

Expected: FAIL，当前仍会输出 probe 阶段引用。

- [ ] **Step 3: 在 `chat_service.py` 增加引用输出门禁**

增加一个统一判定，例如：

```py
def _should_expose_citations(self, *, agent_trace: dict[str, Any] | None, references: list[ChatReference], citation_result: CitationResult) -> bool:
    final_action = str((agent_trace or {}).get('final_action') or '')
    if final_action == 'direct_general_answer':
        return False
    if not references:
        return False
    if not citation_result.citations and not citation_result.sentence_citations:
        return False
    return True
```

然后在 `send_message` / `rag_query` / `rag_stream` 组装结果时统一处理：

1. 不允许暴露引用时，返回 `references=[]`
2. `citation_section=[]`
3. `sentence_citations=[]`

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_chat_api.py -q`

Expected: PASS。

### Task 6: SSE 转发工具事件并更新上下文

**Files:**
- Modify: `backend/app/services/chat_service.py`
- Modify: `docs/ai/context/2026-04-29-chat-layered-protocol.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: 写失败测试，确认 `/api/chat/stream` 返回工具事件**

扩展 `backend/tests/test_chat_api.py` 的 stream 用例，让 stub canvas 通过 `runtime_event_sink` 发：

```py
{
    'type': 'tool_use',
    'id': 'tool-1',
    'name': 'graph_retrieval_tool',
    'input': {'query': '向量空间'},
    'title': '检索知识图谱',
}
```

以及对应 `tool_result`，断言 body 包含这两类 SSE。

- [ ] **Step 2: 在 `chat_service.py` 增加 `_tool_event_chunk`**

把 runtime `tool_use/tool_result` 转成 SSE 正文层事件。

- [ ] **Step 3: 在 `rag_stream` 的 runtime 分支接入工具事件**

顺序要求：

1. 优先尝试 `_tool_event_chunk`
2. 否则再走 `_timeline_chunk_from_runtime_event`

- [ ] **Step 4: 更新上下文文档**

在 `docs/ai/context/2026-04-29-chat-layered-protocol.md` 写明：

1. 原始内联卡片方案未落地的差异
2. 三个新增问题的根因与收口方式
3. 剩余实现范围

并在 `AGENTS.md` 增加一条当前决策记忆：

```md
- 2026-04-29：Chat 分层协议剩余实现除 `tool_use/tool_result` 内联卡片外，还必须同时修复三项行为：无命中时隐藏参考引用、probe 类 timeline 必须发完成态、带有序列表/强调语法的回答必须继续走 Markdown 渲染，不能误降级到句子模式
```

- [ ] **Step 5: 全量验证**

Run: `cd frontend && npm run test -- src/services/chatApi.test.ts src/hooks/useChat.test.tsx src/components/chat/AssistantContentBlocks.test.tsx`

Expected: PASS。

Run: `cd frontend && npm run build`

Expected: PASS。

Run: `cd backend && pytest tests/workflow/engine/test_tool_loop.py tests/test_chat_api.py -q`

Expected: PASS。

## 自检

1. Spec 覆盖：内联卡片、引用门禁、timeline 收尾、Markdown 修复都在任务中有对应实现。
2. 当前代码差异：计划基于当前真实实现写，不依赖已经过期的旧函数签名。
3. 测试覆盖：前端解析、前端状态、前端渲染、后端 tool loop、后端 SSE、无命中引用隐藏均有独立验证。
4. raw thinking：没有新增任何 raw thinking/reasoning 展示分支。
