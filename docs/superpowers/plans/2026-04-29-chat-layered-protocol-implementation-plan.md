# Chat Layered Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在个人知识库聊天流中实现分层消息协议：Markdown 正文、内联工具卡片、结构化思考过程各自独立。

**Architecture:** 前端新增 `contentBlocks` 作为 assistant 正文层，`content` 字符串继续作为兼容字段；`timeline/agentTrace` 保持过程观测层。后端继续输出现有 `timeline/trace/content`，并把 runtime tool events 转成 `tool_use/tool_result` SSE 事件。

**Tech Stack:** React 18、TypeScript、MUI、Vitest、FastAPI、pytest、现有 SSE fetch 解析。

---

## 文件结构

前端类型与解析：

- Modify: `frontend/src/types/chat.ts`
- Modify: `frontend/src/services/chatApi.ts`
- Modify: `frontend/src/services/chatApi.test.ts`

前端状态与渲染：

- Modify: `frontend/src/hooks/useChat.ts`
- Create: `frontend/src/components/chat/ToolCallBlock.tsx`
- Create: `frontend/src/components/chat/AssistantContentBlocks.tsx`
- Modify: `frontend/src/components/chat/ChatMessageList.tsx`

后端事件输出：

- Modify: `backend/app/workflow/engine/tool_loop.py`
- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/tests/workflow/engine/test_tool_loop.py`
- Modify: `backend/tests/test_chat_api.py`

验证命令：

- Frontend unit: `cd frontend && npm test -- --run src/services/chatApi.test.ts`
- Frontend build: `cd frontend && npm run build`
- Backend unit: `cd backend && pytest tests/workflow/engine/test_tool_loop.py tests/test_chat_api.py -q`

## 实施约束

1. `content` 仍然只保存 Markdown 文本，不能拼入工具输入、工具结果、thinking 或 reasoning。
2. `ThinkingProcess` 不新增 raw thinking 展示分支，只继续消费 `timeline/trace`。
3. 旧 localStorage 消息只有 `content: string` 时必须继续正常显示。
4. 工具卡片只由 `tool_use/tool_result` 驱动，不能从 `timeline` 反推。
5. 每个任务完成后单独提交，避免和工作区已有无关改动混在一起。

### Task 1: 前端类型与 SSE 解析

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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm test -- --run src/services/chatApi.test.ts`

Expected: FAIL，报错应指向 `sendChatMessageStream` 参数数量或 `onToolUse/onToolResult` 未调用。

- [ ] **Step 3: 扩展聊天类型**

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

然后给 `ChatMessage` 增加字段：

```ts
contentBlocks?: ChatContentBlock[]
```

- [ ] **Step 4: 扩展 `sendChatMessageStream` 回调签名**

在 `frontend/src/services/chatApi.ts` 的 import 中加入：

```ts
ChatToolResultEvent,
ChatToolUseEvent,
```

把函数签名改为：

```ts
export async function sendChatMessageStream(
  message: string,
  onChunk: (content: string) => void,
  onReferences: (refs: ChatReference[]) => void,
  onCitationSection: (items: string[]) => void,
  onSentenceCitations: (items: SentenceCitation[]) => void,
  onTimeline: (event: ChatTimelineEvent) => void,
  onTrace: (trace: AgentTrace) => void,
  onToolUse: (event: ChatToolUseEvent) => void,
  onToolResult: (event: ChatToolResultEvent) => void,
  onComplete: (fullContent: string) => void,
  onError: (error: ApiErrorPayload) => void
): Promise<void> {
```

在 SSE 分支里加：

```ts
          } else if (data.type === 'tool_use') {
            const event = data.content as ChatToolUseEvent
            if (event?.id && event?.name) {
              onToolUse({
                id: String(event.id),
                name: String(event.name),
                input: event.input && typeof event.input === 'object' ? event.input : {},
                title: typeof event.title === 'string' ? event.title : undefined,
                order: typeof event.order === 'number' ? event.order : Date.now(),
              })
            }
          } else if (data.type === 'tool_result') {
            const event = data.content as ChatToolResultEvent
            if (event?.tool_use_id) {
              onToolResult({
                tool_use_id: String(event.tool_use_id),
                status: event.status === 'error' ? 'error' : event.status === 'running' ? 'running' : 'done',
                output: event.output,
                is_error: Boolean(event.is_error),
                order: typeof event.order === 'number' ? event.order : Date.now(),
              })
            }
```

- [ ] **Step 5: 更新已有测试调用参数**

在 `frontend/src/services/chatApi.test.ts` 中，旧调用从：

```ts
await sendChatMessageStream('你好', vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), onError)
```

改为：

```ts
await sendChatMessageStream('你好', vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), onError)
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd frontend && npm test -- --run src/services/chatApi.test.ts`

Expected: PASS。

- [ ] **Step 7: 提交 Task 1**

```bash
git add frontend/src/types/chat.ts frontend/src/services/chatApi.ts frontend/src/services/chatApi.test.ts
git commit -m "feat: parse chat tool sse events"
```

### Task 2: 前端消息状态写入 `contentBlocks`

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`

- [ ] **Step 1: 写失败测试或临时类型检查入口**

当前仓库没有 hook 测试基座。本任务用 TypeScript build 作为失败验证。先在 `useChat.ts` 中引入 Task 1 的新类型，后续实现前运行 build 会因为未使用或签名不匹配失败：

```ts
import { ChatContentBlock, ChatMessage, ChatTimelineEvent, ChatToolResultEvent, ChatToolUseEvent } from '../types/chat'
```

- [ ] **Step 2: 运行 build 确认当前签名需要同步**

Run: `cd frontend && npm run build`

Expected: FAIL，错误应包含 `sendChatMessageStream` 参数数量不匹配，或新类型导入未使用。

- [ ] **Step 3: 增加 block 工具函数**

在 `useSendChatMessage` 内、`updateAssistantDraft` 后添加：

```ts
  const sortContentBlocks = (blocks: ChatContentBlock[]) =>
    [...blocks].sort((a, b) => {
      if (a.order !== b.order) return a.order - b.order
      return `${a.type}:${'id' in a ? a.id : ''}`.localeCompare(`${b.type}:${'id' in b ? b.id : ''}`)
    })

  const appendMarkdownBlock = (blocks: ChatContentBlock[] = [], chunk: string): ChatContentBlock[] => {
    const lastBlock = blocks[blocks.length - 1]
    if (lastBlock?.type === 'markdown') {
      return [
        ...blocks.slice(0, -1),
        {
          ...lastBlock,
          text: `${lastBlock.text}${chunk}`,
        },
      ]
    }
    return [
      ...blocks,
      {
        type: 'markdown',
        id: generateId(),
        text: chunk,
        order: Date.now(),
      },
    ]
  }

  const upsertToolUseBlock = (blocks: ChatContentBlock[] = [], event: ChatToolUseEvent): ChatContentBlock[] => {
    const nextBlocks = blocks.filter((block) => !(block.type === 'tool_use' && block.id === event.id))
    nextBlocks.push({
      type: 'tool_use',
      id: event.id,
      name: event.name,
      input: event.input,
      title: event.title,
      order: event.order,
    })
    return sortContentBlocks(nextBlocks)
  }

  const upsertToolResultBlock = (blocks: ChatContentBlock[] = [], event: ChatToolResultEvent): ChatContentBlock[] => {
    const resultId = `${event.tool_use_id}:result`
    const nextBlocks = blocks.filter((block) => !(block.type === 'tool_result' && block.tool_use_id === event.tool_use_id))
    nextBlocks.push({
      type: 'tool_result',
      id: resultId,
      tool_use_id: event.tool_use_id,
      status: event.status,
      output: event.output,
      is_error: event.is_error,
      order: event.order,
    })
    return sortContentBlocks(nextBlocks)
  }
```

- [ ] **Step 4: 初始化 assistant message**

把 assistant message 初始化从：

```ts
      content: '',
```

改为：

```ts
      content: '',
      contentBlocks: [],
```

- [ ] **Step 5: 同步 `sendChatMessageStream` 调用**

在 `sendChatMessageStream` 的 `onChunk` 回调里，把当前逻辑：

```ts
        (chunk) => {
          pendingBufferRef.current += chunk
          startTypingLoop()
        },
```

保留不变。然后在 `startTypingLoop` 的 `updateAssistantDraft` 中把：

```ts
        content: `${message.content}${nextSlice}`,
```

改为：

```ts
        content: `${message.content}${nextSlice}`,
        contentBlocks: appendMarkdownBlock(message.contentBlocks, nextSlice),
```

在 `onTrace` 回调后、`onComplete` 回调前插入两个新回调：

```ts
        (toolUse) => {
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            contentBlocks: upsertToolUseBlock(draft.contentBlocks, toolUse),
          }))
        },
        (toolResult) => {
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            contentBlocks: upsertToolResultBlock(draft.contentBlocks, toolResult),
          }))
        },
```

- [ ] **Step 6: 完成时补齐无打字缓冲的 block**

在 `onComplete` 的 `updateAssistantDraft` 中把：

```ts
              content: draft.content || fullContent,
```

改为：

```ts
              content: draft.content || fullContent,
              contentBlocks: draft.contentBlocks?.length ? draft.contentBlocks : appendMarkdownBlock([], fullContent),
```

- [ ] **Step 7: 运行前端测试和 build**

Run: `cd frontend && npm test -- --run src/services/chatApi.test.ts`

Expected: PASS。

Run: `cd frontend && npm run build`

Expected: PASS。

- [ ] **Step 8: 提交 Task 2**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "feat: store chat content blocks"
```

### Task 3: 前端内联工具卡片渲染

**Files:**
- Create: `frontend/src/components/chat/ToolCallBlock.tsx`
- Create: `frontend/src/components/chat/AssistantContentBlocks.tsx`
- Modify: `frontend/src/components/chat/ChatMessageList.tsx`

- [ ] **Step 1: 创建工具卡片组件**

创建 `frontend/src/components/chat/ToolCallBlock.tsx`：

```tsx
import BuildRoundedIcon from '@mui/icons-material/BuildRounded'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import ErrorOutlineRoundedIcon from '@mui/icons-material/ErrorOutlineRounded'
import MoreHorizRoundedIcon from '@mui/icons-material/MoreHorizRounded'
import { Box, Chip, Stack, Typography } from '@mui/material'

import { ChatToolResultBlock, ChatToolUseBlock } from '../../types/chat'

function summarizeValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function resultLabel(result?: ChatToolResultBlock) {
  if (!result) return '运行中'
  if (result.status === 'error' || result.is_error) return '失败'
  if (result.status === 'running') return '运行中'
  return '完成'
}

export function ToolCallBlock({ use, result }: { use: ChatToolUseBlock; result?: ChatToolResultBlock }) {
  const isError = result?.status === 'error' || result?.is_error
  const isDone = Boolean(result) && !isError && result.status !== 'running'
  const statusText = resultLabel(result)
  const inputSummary = summarizeValue(use.input)
  const outputSummary = summarizeValue(result?.output)

  return (
    <Box
      sx={{
        border: '1px solid rgba(20, 20, 19, 0.1)',
        borderRadius: 1,
        bgcolor: 'rgba(255, 255, 255, 0.72)',
        px: 1.25,
        py: 1,
        my: 1,
        boxShadow: '0 8px 18px rgba(20, 20, 19, 0.06)',
      }}
    >
      <Stack spacing={0.75}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Box sx={{ color: isError ? 'error.main' : isDone ? 'success.main' : 'text.secondary', display: 'flex' }}>
            {isError ? <ErrorOutlineRoundedIcon fontSize="small" /> : isDone ? <CheckCircleRoundedIcon fontSize="small" /> : <MoreHorizRoundedIcon fontSize="small" />}
          </Box>
          <Typography variant="body2" sx={{ fontWeight: 700, flex: 1, minWidth: 0 }}>
            {use.title || use.name}
          </Typography>
          <Chip size="small" icon={<BuildRoundedIcon />} label={statusText} color={isError ? 'error' : isDone ? 'success' : 'default'} />
        </Stack>
        {inputSummary ? (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', wordBreak: 'break-word' }}>
            输入：{inputSummary}
          </Typography>
        ) : null}
        {outputSummary ? (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', wordBreak: 'break-word' }}>
            结果：{outputSummary}
          </Typography>
        ) : null}
      </Stack>
    </Box>
  )
}
```

- [ ] **Step 2: 创建 block 渲染组件**

创建 `frontend/src/components/chat/AssistantContentBlocks.tsx`：

```tsx
import { Box } from '@mui/material'

import { ChatContentBlock, ChatReference, SentenceCitation } from '../../types/chat'
import { MarkdownContent } from './MarkdownContent'
import { ToolCallBlock } from './ToolCallBlock'

export function AssistantContentBlocks({
  blocks,
}: {
  blocks: ChatContentBlock[]
  references: ChatReference[]
  sentenceCitations?: SentenceCitation[]
}) {
  const toolResults = new Map(
    blocks
      .filter((block) => block.type === 'tool_result')
      .map((block) => [block.tool_use_id, block])
  )

  return (
    <Box>
      {blocks.map((block) => {
        if (block.type === 'markdown') {
          return <MarkdownContent key={block.id} content={block.text} />
        }
        if (block.type === 'tool_use') {
          return <ToolCallBlock key={block.id} use={block} result={toolResults.get(block.id)} />
        }
        if (blocks.some((candidate) => candidate.type === 'tool_use' && candidate.id === block.tool_use_id)) {
          return null
        }
        return (
          <ToolCallBlock
            key={block.id}
            use={{
              type: 'tool_use',
              id: block.tool_use_id,
              name: 'unknown_tool',
              input: {},
              title: '工具调用',
              order: block.order - 1,
            }}
            result={block}
          />
        )
      })}
    </Box>
  )
}
```

- [ ] **Step 3: 接入 `ChatMessageList`**

在 `frontend/src/components/chat/ChatMessageList.tsx` 增加 import：

```ts
import { AssistantContentBlocks } from './AssistantContentBlocks'
```

把 assistant 正文渲染从：

```tsx
            <AssistantContent
              content={message.content}
              references={message.references ?? []}
              sentenceCitations={message.sentenceCitations}
            />
```

改为：

```tsx
            {message.contentBlocks?.length ? (
              <AssistantContentBlocks
                blocks={message.contentBlocks}
                references={message.references ?? []}
                sentenceCitations={message.sentenceCitations}
              />
            ) : (
              <AssistantContent
                content={message.content}
                references={message.references ?? []}
                sentenceCitations={message.sentenceCitations}
              />
            )}
```

- [ ] **Step 4: 运行前端 build**

Run: `cd frontend && npm run build`

Expected: PASS。

- [ ] **Step 5: 提交 Task 3**

```bash
git add frontend/src/components/chat/ToolCallBlock.tsx frontend/src/components/chat/AssistantContentBlocks.tsx frontend/src/components/chat/ChatMessageList.tsx
git commit -m "feat: render inline chat tool cards"
```

### Task 4: 后端 tool loop 发出工具事件

**Files:**
- Modify: `backend/app/workflow/engine/tool_loop.py`
- Modify: `backend/tests/workflow/engine/test_tool_loop.py`

- [ ] **Step 1: 写失败测试，确认 tool loop 发 `tool_use/tool_result`**

在 `backend/tests/workflow/engine/test_tool_loop.py` 增加：

```py
@pytest.mark.anyio
async def test_tool_loop_emits_tool_use_and_tool_result_events():
    class StubClient:
        def __init__(self) -> None:
            self.chat = type(
                'Chat',
                (),
                {
                    'completions': type(
                        'Completions',
                        (),
                        {
                            'calls': [],
                            'create': self.create,
                        },
                    )()
                },
            )()
            self._calls = 0

        def create(self, **kwargs):
            self._calls += 1
            if self._calls == 1:
                return type('Response', (), {'choices': [type('Choice', (), {'message': FakeMessage(tool_calls=[FakeToolCall('tool-1', 'graph_retrieval_tool', '{"query":"Alice"}')])})]})()
            return type('Response', (), {'choices': [type('Choice', (), {'message': FakeMessage(content='Alice 喜欢数学。')})]})()

    async def fake_tool(query: str):
        return {'summary': f'命中 {query}'}

    events: list[dict] = []
    engine = ToolLoopEngine(llm_client=StubClient())

    await engine.run(
        system_prompt='system',
        user_prompt='user',
        tool_schemas=[{'type': 'function', 'function': {'name': 'graph_retrieval_tool'}}],
        tool_registry={'graph_retrieval_tool': fake_tool},
        event_callback=events.append,
    )

    assert {
        'type': 'tool_use',
        'id': 'tool-1',
        'name': 'graph_retrieval_tool',
        'input': {'query': 'Alice'},
        'title': '检索知识图谱',
    }.items() <= events[0].items()
    assert events[1]['type'] == 'timeline'
    assert {
        'type': 'tool_result',
        'tool_use_id': 'tool-1',
        'status': 'done',
        'is_error': False,
    }.items() <= events[2].items()
    assert events[2]['output'] == {'summary': '命中 Alice'}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/workflow/engine/test_tool_loop.py::test_tool_loop_emits_tool_use_and_tool_result_events -q`

Expected: FAIL，`events[0]['type']` 仍为 `timeline` 或缺少 `tool_use`。

- [ ] **Step 3: 在工具执行前后发 runtime event**

在 `backend/app/workflow/engine/tool_loop.py` 的每次工具调用循环中，解析 `arguments` 后、发 timeline 前插入：

```py
                if event_callback is not None:
                    event_callback(
                        {
                            'type': 'tool_use',
                            'id': str(tool_call.id),
                            'name': str(tool_name),
                            'input': arguments,
                            'title': '检索知识图谱' if tool_name == 'graph_retrieval_tool' else str(tool_name),
                        }
                    )
```

在工具成功 `result = await self._call_tool(tool_impl, arguments)` 后插入：

```py
                    if event_callback is not None:
                        event_callback(
                            {
                                'type': 'tool_result',
                                'tool_use_id': str(tool_call.id),
                                'status': 'done',
                                'output': result,
                                'is_error': False,
                            }
                        )
```

在 `except Exception as exc` 分支中、追加 tool history 前插入：

```py
                    if event_callback is not None:
                        event_callback(
                            {
                                'type': 'tool_result',
                                'tool_use_id': str(tool_call.id),
                                'status': 'error',
                                'output': {'error': str(exc)},
                                'is_error': True,
                            }
                        )
```

- [ ] **Step 4: 运行 tool loop 测试**

Run: `cd backend && pytest tests/workflow/engine/test_tool_loop.py -q`

Expected: PASS。

- [ ] **Step 5: 提交 Task 4**

```bash
git add backend/app/workflow/engine/tool_loop.py backend/tests/workflow/engine/test_tool_loop.py
git commit -m "feat: emit tool runtime events"
```

### Task 5: 后端 SSE 转发 `tool_use/tool_result`

**Files:**
- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/tests/test_chat_api.py`

- [ ] **Step 1: 写失败测试，确认 `/api/chat/stream` 返回工具事件**

在 `backend/tests/test_chat_api.py` 中增加或扩展 `test_rag_stream_uses_agent_stream_path_and_returns_sse_payload`，让 stub canvas 发 runtime tool event。若 `build_stub_canvas` 支持 runtime events，就传入：

```py
runtime_events=[
    {
        'type': 'tool_use',
        'id': 'tool-1',
        'name': 'graph_retrieval_tool',
        'input': {'query': '向量空间'},
        'title': '检索知识图谱',
    },
    {
        'type': 'tool_result',
        'tool_use_id': 'tool-1',
        'status': 'done',
        'output': {'summary': '命中 2 条证据'},
        'is_error': False,
    },
]
```

并增加断言：

```py
    assert '"type": "tool_use"' in body
    assert '"id": "tool-1"' in body
    assert '"type": "tool_result"' in body
    assert '"tool_use_id": "tool-1"' in body
```

如果 `build_stub_canvas` 尚不支持 runtime events，就在该 helper 内增加 `runtime_events: list[dict] | None = None` 参数，并在 `run()` 开始时调用 sink：

```py
        for runtime_event in runtime_events or []:
            if self._runtime_event_sink:
                self._runtime_event_sink(runtime_event)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_chat_api.py::test_rag_stream_uses_agent_stream_path_and_returns_sse_payload -q`

Expected: FAIL，body 中没有 `tool_use` 或 `tool_result`。

- [ ] **Step 3: 增加工具事件 chunk 构造**

在 `backend/app/services/chat_service.py` 中增加方法：

```py
    def _tool_event_chunk(self, event: dict[str, Any], order: int) -> str | None:
        event_type = event.get('type')
        if event_type == 'tool_use':
            payload = {
                'type': 'tool_use',
                'content': {
                    'id': str(event.get('id') or f'tool-{order}'),
                    'name': str(event.get('name') or 'unknown_tool'),
                    'input': event.get('input') if isinstance(event.get('input'), dict) else {},
                    'title': str(event.get('title') or event.get('name') or '工具调用'),
                    'order': order,
                },
            }
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        if event_type == 'tool_result':
            payload = {
                'type': 'tool_result',
                'content': {
                    'tool_use_id': str(event.get('tool_use_id') or ''),
                    'status': 'error' if event.get('status') == 'error' or event.get('is_error') else 'done',
                    'output': event.get('output'),
                    'is_error': bool(event.get('is_error')),
                    'order': order,
                },
            }
            if not payload['content']['tool_use_id']:
                return None
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        return None
```

- [ ] **Step 4: 在 runtime 分支转发工具事件**

在 `rag_stream` 的 `if source == 'runtime':` 分支中，把当前逻辑：

```py
                    chunk = self._timeline_chunk_from_runtime_event(payload, timeline_order)
                    if chunk:
                        yield chunk
                        timeline_order += 1
                        timeline_emitted = True
                    continue
```

改为：

```py
                    tool_chunk = self._tool_event_chunk(payload, timeline_order)
                    if tool_chunk:
                        yield tool_chunk
                        timeline_order += 1
                        continue

                    chunk = self._timeline_chunk_from_runtime_event(payload, timeline_order)
                    if chunk:
                        yield chunk
                        timeline_order += 1
                        timeline_emitted = True
                    continue
```

- [ ] **Step 5: 运行后端测试**

Run: `cd backend && pytest tests/test_chat_api.py::test_rag_stream_uses_agent_stream_path_and_returns_sse_payload tests/workflow/engine/test_tool_loop.py -q`

Expected: PASS。

- [ ] **Step 6: 提交 Task 5**

```bash
git add backend/app/services/chat_service.py backend/tests/test_chat_api.py
git commit -m "feat: stream chat tool events"
```

### Task 6: 全量验证与上下文收口

**Files:**
- Modify: `docs/ai/context/2026-04-29-chat-layered-protocol.md`

- [ ] **Step 1: 运行前端验证**

Run: `cd frontend && npm test -- --run src/services/chatApi.test.ts`

Expected: PASS。

Run: `cd frontend && npm run build`

Expected: PASS。

- [ ] **Step 2: 运行后端验证**

Run: `cd backend && pytest tests/workflow/engine/test_tool_loop.py tests/test_chat_api.py -q`

Expected: PASS。

- [ ] **Step 3: 手动联调固定端口**

按项目端口约定启动或复用服务：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

验证：

```bash
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173
```

Expected: 后端健康检查 HTTP 200，前端 HTTP 200。

- [ ] **Step 4: 浏览器验收**

在 `http://127.0.0.1:5173` 发起一次会触发图谱检索的问题，例如：

```text
向量空间有什么用途？
```

Expected:

1. 思考过程区域显示 `timeline/trace` 步骤。
2. 工具调用以卡片形式出现在 assistant 正文中。
3. 最终回答仍按 Markdown 渲染。
4. 页面不显示 raw thinking 或 raw reasoning 文本。

- [ ] **Step 5: 更新上下文文档**

在 `docs/ai/context/2026-04-29-chat-layered-protocol.md` 增加实现结果：

```md
## 实现结果

实现后，聊天 SSE 正文层由 `content/tool_use/tool_result` 组成，过程观测层由 `timeline/trace` 组成。前端保留旧 `content` 字符串兼容 localStorage，同时使用 `contentBlocks` 渲染 Markdown 与内联工具卡片。

验证命令：

- `cd frontend && npm test -- --run src/services/chatApi.test.ts`
- `cd frontend && npm run build`
- `cd backend && pytest tests/workflow/engine/test_tool_loop.py tests/test_chat_api.py -q`
```

- [ ] **Step 6: 提交 Task 6**

```bash
git add docs/ai/context/2026-04-29-chat-layered-protocol.md
git commit -m "docs: record chat layered protocol implementation"
```

## 自检清单

1. Spec 覆盖：Task 1 和 Task 2 覆盖 SSE 前端消费与 `contentBlocks`；Task 3 覆盖工具卡片和 Markdown 回退；Task 4 和 Task 5 覆盖后端工具事件；Task 6 覆盖验证与上下文。
2. raw thinking/reasoning：计划没有任何前端展示 raw thinking/reasoning 的步骤。
3. 旧消息兼容：Task 3 保留 `contentBlocks` 不存在时走 `AssistantContent`。
4. 工具卡片来源：只从 `tool_use/tool_result` 事件生成，不从 `timeline` 生成。
5. 测试覆盖：前端解析、前端构建、后端 tool loop、后端 SSE 都有独立验证命令。
