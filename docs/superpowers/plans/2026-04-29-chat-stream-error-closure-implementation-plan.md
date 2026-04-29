# Chat Stream Error Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `chat` 流式链路在主流程异常和后台 task 异常下都稳定输出结构化 SSE `error`，并让前端结束 loading、保留已有内容、把错误明确落到 assistant 消息里。

**Architecture:** 后端把 `canvas.run()` producer task 的异常显式汇入主 SSE 循环，统一走一个错误 chunk 构造出口，避免只在日志中留下 `Task exception was never retrieved`。前端保持 `chatApi` 作为底层流式消费层不变，重点在 `useChat` 层补齐“收到错误时的消息收尾逻辑”和相应状态测试。

**Tech Stack:** FastAPI、pytest、React 18、TypeScript、Vitest、React Query、现有 SSE `fetch` 消费链路。

---

## 文件结构

后端错误收口：

- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/tests/test_chat_api.py`

前端失败收尾：

- Modify: `frontend/src/hooks/useChat.ts`
- Create: `frontend/src/hooks/useChat.test.tsx`
- Regression Test: `frontend/src/services/chatApi.test.ts`

文档收口：

- Modify: `docs/ai/context/2026-04-29-chat-stream-error-closure.md`

验证命令：

- Backend: `cd backend && pytest tests/test_chat_api.py -q`
- Frontend hook: `cd frontend && npm test -- --run src/hooks/useChat.test.tsx`
- Frontend regression: `cd frontend && npm test -- --run src/services/chatApi.test.ts`
- Frontend build: `cd frontend && npm run build`

## 实施约束

1. 不改 agentic RAG 检索策略，只处理失败路径闭环。
2. 不引入前端超时猜测型兜底作为主路径；结构化 `error` 仍是首选终止信号。
3. 不丢弃已有 `timeline`、部分正文和用户问题。
4. 不把所有异常都粗暴映射成模型上游错误；只有具备上游状态码/网络特征的异常才走模型错误归一化。
5. 失败后 assistant 消息必须退出 `isStreaming`，且下一次发送无需刷新页面。

### Task 1: 先把后端失败契约测出来

**Files:**
- Modify: `backend/tests/test_chat_api.py`
- Test Target: `backend/app/services/chat_service.py`

- [ ] **Step 1: 给测试文件增加一个“后台 task 失败”的 stub canvas**

在 `backend/tests/test_chat_api.py` 里新增 helper：

```py
def build_failing_stream_canvas(*, error: Exception, emit_timeline: bool = True):
    class StubReferenceStore:
        def snapshot(self):
            return {'chunks': [], 'doc_aggs': [], 'graph_evidence': []}

    class StubCanvas:
        def __init__(self) -> None:
            self.execution_path = ['begin', 'agent']
            self.reference_store = StubReferenceStore()
            self._runtime_event_sink = None

        def set_runtime_event_sink(self, sink):
            self._runtime_event_sink = sink

        async def run(self):
            if emit_timeline:
                yield SimpleNamespace(event='node_started', node_id='agent', payload={})
            raise error

    return StubCanvas()
```

- [ ] **Step 2: 写失败测试，证明 producer task 异常现在只会挂日志，不会回 SSE**

在 `backend/tests/test_chat_api.py` 增加测试：

```py
def test_rag_stream_returns_structured_error_when_canvas_task_fails(monkeypatch):
    failure = ModelAPIError(
        error_code='MODEL_API_UPSTREAM_ERROR',
        message='模型服务暂时不可用，请稍后重试。',
        status_code=502,
        details='502 bad gateway',
        provider='cliproxyapi',
        retryable=True,
    )

    def fake_create_chat_canvas(*, query: str, group_id: str = 'default', **kwargs):
        return build_failing_stream_canvas(error=failure)

    monkeypatch.setattr(chat_router.service.canvas_factory, 'create_chat_canvas', fake_create_chat_canvas)

    with client_without_lifespan() as client:
        with client.stream("POST", "/api/chat/stream", json={"message": "电池属于什么垃圾？"}) as response:
            assert response.status_code == 200
            body = ''.join(response.iter_text())

    assert '"type": "timeline"' in body
    assert '"type": "error"' in body
    assert '模型服务暂时不可用，请稍后重试。' in body
    assert '"type": "done"' not in body
```

- [ ] **Step 3: 运行测试确认当前行为失败**

Run: `cd backend && pytest tests/test_chat_api.py::test_rag_stream_returns_structured_error_when_canvas_task_fails -q`

Expected: FAIL。常见失败表现是响应体没有 `type: error`，或测试过程中直接出现未被消费的后台 task 异常。

- [ ] **Step 4: 补一个“部分输出后失败也不能丢 timeline”的测试**

继续在 `backend/tests/test_chat_api.py` 增加：

```py
def test_rag_stream_keeps_existing_timeline_when_error_happens_after_stream_start(monkeypatch):
    failure = RuntimeError('stream crashed after timeline')

    def fake_create_chat_canvas(*, query: str, group_id: str = 'default', **kwargs):
        return build_failing_stream_canvas(error=failure, emit_timeline=True)

    monkeypatch.setattr(chat_router.service.canvas_factory, 'create_chat_canvas', fake_create_chat_canvas)

    with client_without_lifespan() as client:
        with client.stream("POST", "/api/chat/stream", json={"message": "你好"}) as response:
            body = ''.join(response.iter_text())

    assert '"title": "理解问题"' in body
    assert '"type": "error"' in body
```

- [ ] **Step 5: 运行新增两条后端流式测试**

Run: `cd backend && pytest tests/test_chat_api.py::test_rag_stream_returns_structured_error_when_canvas_task_fails tests/test_chat_api.py::test_rag_stream_keeps_existing_timeline_when_error_happens_after_stream_start -q`

Expected: FAIL，至少第一条失败。

- [ ] **Step 6: 提交 Task 1**

```bash
git add backend/tests/test_chat_api.py
git commit -m "test: capture chat stream producer task failure"
```

### Task 2: 后端把后台 task 异常收口到唯一 SSE error 出口

**Files:**
- Modify: `backend/app/services/chat_service.py`
- Test: `backend/tests/test_chat_api.py`

- [ ] **Step 1: 在 `ChatService` 中加统一错误 chunk 构造函数**

在 `backend/app/services/chat_service.py` 的 `ChatService` 类中新增：

```py
    def _error_payload_from_exception(self, error: Exception) -> dict[str, Any]:
        if isinstance(error, ModelAPIError):
            return {
                'type': 'error',
                'content': error.message,
                **error.to_dict(),
            }

        status_code = getattr(error, 'status_code', None) or getattr(error, 'http_status', None)
        if status_code is not None:
            normalized = ModelAPIError(
                error_code='MODEL_API_UPSTREAM_ERROR' if int(status_code) >= 500 else 'UNKNOWN_ERROR',
                message='模型服务暂时不可用，请稍后重试。' if int(status_code) >= 500 else str(error),
                status_code=int(status_code),
                details=str(error),
                provider='',
                retryable=int(status_code) >= 500,
            )
            return {
                'type': 'error',
                'content': normalized.message,
                **normalized.to_dict(),
            }

        return {
            'type': 'error',
            'content': str(error),
            'error_code': 'UNKNOWN_ERROR',
            'message': str(error),
            'details': '',
            'provider': '',
            'retryable': False,
        }

    def _error_chunk(self, error: Exception) -> str:
        return f"data: {json.dumps(self._error_payload_from_exception(error), ensure_ascii=False)}\\n\\n"
```

- [ ] **Step 2: 让 producer task 自己捕获异常并把失败放回队列**

把 `rag_stream` 里的 producer 改成：

```py
            async def produce_canvas_events() -> None:
                try:
                    async for event in canvas.run():
                        await queue.put(('canvas', event))
                except Exception as error:
                    await queue.put(('stream_error', error))
                finally:
                    await queue.put(('done', None))
```

这样主循环永远能看到 `stream_error`，不会只剩服务端日志。

- [ ] **Step 3: 主 SSE 循环识别 `stream_error` 并立即结束**

在 `while True` 循环顶部把：

```py
                if source == 'done':
                    break
```

改成：

```py
                if source == 'stream_error':
                    yield self._error_chunk(payload)
                    break

                if source == 'done':
                    break
```

保证一旦 producer task 抛错，本次流只输出一条 `error` 并结束。

- [ ] **Step 4: 让主循环退出后安全等待 producer task**

把：

```py
            await producer_task
```

保留，但前提是 producer 已经在 `finally` 中完成 `done` 入队，不会导致主协程无界等待。如果这里还有异常，继续走外层 `except`，统一用 `_error_chunk()` 输出。

- [ ] **Step 5: 把外层异常出口也收敛到新 helper**

将末尾：

```py
        except Exception as e:
            logger.error(f"Error in streaming RAG: {e}", exc_info=True)
            if isinstance(e, ModelAPIError):
                error_chunk = {
                    "type": "error",
                    "content": e.message,
                    **e.to_dict(),
                }
            else:
                error_chunk = {
                    "type": "error",
                    "content": str(e),
                    "error_code": "UNKNOWN_ERROR",
                    "message": str(e),
                    "details": "",
                    "provider": "",
                    "retryable": False,
                }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
```

改为：

```py
        except Exception as error:
            logger.error("Error in streaming RAG: %s", error, exc_info=True)
            yield self._error_chunk(error)
```

- [ ] **Step 6: 运行后端测试确认 producer task 失败已闭环**

Run: `cd backend && pytest tests/test_chat_api.py::test_rag_stream_returns_structured_error_when_canvas_task_fails tests/test_chat_api.py::test_rag_stream_keeps_existing_timeline_when_error_happens_after_stream_start tests/test_chat_api.py::test_rag_stream_returns_structured_model_error_payload -q`

Expected: PASS。

- [ ] **Step 7: 运行完整 chat API 测试回归**

Run: `cd backend && pytest tests/test_chat_api.py -q`

Expected: PASS。

- [ ] **Step 8: 提交 Task 2**

```bash
git add backend/app/services/chat_service.py backend/tests/test_chat_api.py
git commit -m "fix: close chat stream errors through sse"
```

### Task 3: 前端把错误稳定落到 assistant 消息并退出流式状态

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`
- Create: `frontend/src/hooks/useChat.test.tsx`
- Regression Test: `frontend/src/services/chatApi.test.ts`

- [ ] **Step 1: 新建 hook 测试文件，搭一个最小 QueryClient + Toast wrapper**

创建 `frontend/src/hooks/useChat.test.tsx`：

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, useEffect } from 'react'
import { createRoot, Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppToastProvider } from '../components/common/AppToastProvider'
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

  useEffect(() => {
    void mutation.mutateAsync(message).catch(() => {})
  }, [message, mutation])

  return null
}
```

- [ ] **Step 2: 写失败测试，覆盖“部分正文后 error 仍要保留已有内容并退出 loading”**

继续在 `frontend/src/hooks/useChat.test.tsx` 中加入：

```tsx
it('流式过程中失败时会保留已有正文并结束 assistant loading', async () => {
  vi.useFakeTimers()
  const { sendChatMessageStream, loadMessagesFromStorage } = await import('../services/chatApi')
  const sendMock = vi.mocked(sendChatMessageStream)
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  const queryClient = new QueryClient()

  sendMock.mockImplementation(async (_message, onChunk, _onRefs, _onCitation, _onSentence, onTimeline, _onTrace, _onComplete, onError) => {
    onTimeline({
      id: 'understand-question',
      kind: 'understand',
      title: '理解问题',
      detail: '正在理解你的问题。',
      status: 'started',
      order: 1,
    })
    onChunk('已经生成了一部分回答')
    vi.advanceTimersByTime(100)
    onError({
      error_code: 'MODEL_API_UPSTREAM_ERROR',
      message: '模型服务暂时不可用，请稍后重试。',
      retryable: true,
    })
  })

  await act(async () => {
    root.render(
      <QueryClientProvider client={queryClient}>
        <AppToastProvider>
          <SendOnMount message="测试问题" />
        </AppToastProvider>
      </QueryClientProvider>
    )
  })

  const messages = loadMessagesFromStorage()
  const assistant = messages[messages.length - 1]

  expect(assistant.role).toBe('assistant')
  expect(assistant.isStreaming).toBe(false)
  expect(assistant.content).toContain('已经生成了一部分回答')
  expect(assistant.content).toContain('错误: 模型服务暂时不可用，请稍后重试。')
  expect(assistant.timeline?.[0]?.title).toBe('理解问题')

  await act(async () => {
    root.unmount()
  })
  container.remove()
})
```

- [ ] **Step 3: 写失败测试，覆盖“纯错误且无正文时 assistant 直接显示错误文案”**

在同一文件继续加入：

```tsx
it('没有正文时会把错误文案直接写入 assistant 消息', async () => {
  const { sendChatMessageStream, loadMessagesFromStorage } = await import('../services/chatApi')
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  const queryClient = new QueryClient()

  vi.mocked(sendChatMessageStream).mockImplementation(async (_message, _onChunk, _onRefs, _onCitation, _onSentence, _onTimeline, _onTrace, _onComplete, onError) => {
    onError({
      error_code: 'UNKNOWN_ERROR',
      message: '请求失败，请稍后重试。',
    })
  })

  await act(async () => {
    root.render(
      <QueryClientProvider client={queryClient}>
        <AppToastProvider>
          <SendOnMount message="测试问题" />
        </AppToastProvider>
      </QueryClientProvider>
    )
  })

  const messages = loadMessagesFromStorage()
  const assistant = messages[messages.length - 1]

  expect(assistant.content).toBe('错误: 请求失败，请稍后重试。')
  expect(assistant.isStreaming).toBe(false)

  await act(async () => {
    root.unmount()
  })
  container.remove()
})
```

- [ ] **Step 4: 运行 hook 测试确认当前失败**

Run: `cd frontend && npm test -- --run src/hooks/useChat.test.tsx`

Expected: FAIL。当前实现里一旦已有正文，`content: draft.content || \`错误: ${error.message}\`` 不会追加失败收尾提示，测试会失败。

- [ ] **Step 5: 在 `useChat.ts` 中抽出 assistant 错误收尾 helper**

在 `frontend/src/hooks/useChat.ts` 的 `updateAssistantDraft` 下方新增：

```ts
  const finalizeAssistantErrorContent = (content: string, error: ApiErrorPayload) => {
    const normalized = `错误: ${error.message}`
    const trimmed = content.trim()
    if (!trimmed) {
      return normalized
    }
    if (trimmed.includes(error.message)) {
      return content
    }
    return `${content}\n\n${normalized}`
  }
```

- [ ] **Step 6: 用新 helper 改写 error 分支**

把 `onError` 中的：

```ts
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            isStreaming: false,
            content: draft.content || `错误: ${error.message}`,
          }))
```

改成：

```ts
          updateAssistantDraft(assistantId, (draft) => ({
            ...draft,
            isStreaming: false,
            content: finalizeAssistantErrorContent(draft.content, error),
          }))
```

这样“无正文时直接显示错误文案，有正文时追加错误收尾”两个路径都能满足。

- [ ] **Step 7: 跑 hook 测试与已有 `chatApi` 回归**

Run: `cd frontend && npm test -- --run src/hooks/useChat.test.tsx`

Expected: PASS。

Run: `cd frontend && npm test -- --run src/services/chatApi.test.ts`

Expected: PASS。

- [ ] **Step 8: 跑前端 build**

Run: `cd frontend && npm run build`

Expected: PASS。

- [ ] **Step 9: 提交 Task 3**

```bash
git add frontend/src/hooks/useChat.ts frontend/src/hooks/useChat.test.tsx
git commit -m "fix: finalize chat assistant state on stream error"
```

### Task 4: 全量验证并补实现上下文

**Files:**
- Modify: `docs/ai/context/2026-04-29-chat-stream-error-closure.md`

- [ ] **Step 1: 跑后端完整回归**

Run: `cd backend && pytest tests/test_chat_api.py -q`

Expected: PASS。

- [ ] **Step 2: 跑前端完整回归**

Run: `cd frontend && npm test -- --run src/hooks/useChat.test.tsx src/services/chatApi.test.ts`

Expected: PASS。

Run: `cd frontend && npm run build`

Expected: PASS。

- [ ] **Step 3: 补文档里的“实现结果”段落**

在 `docs/ai/context/2026-04-29-chat-stream-error-closure.md` 末尾追加：

```md
## 实现结果

实现后，`chat` 流式链路的后台 producer task 异常会显式汇入主 SSE 循环，并统一输出结构化 `error` 事件；前端收到 `error` 后会结束 assistant 流式状态，保留已有 `timeline` 与正文内容，并把错误文案写入消息本体。

## 验证命令

- `cd backend && pytest tests/test_chat_api.py -q`
- `cd frontend && npm test -- --run src/hooks/useChat.test.tsx src/services/chatApi.test.ts`
- `cd frontend && npm run build`
```

- [ ] **Step 4: 提交 Task 4**

```bash
git add docs/ai/context/2026-04-29-chat-stream-error-closure.md
git commit -m "docs: record chat stream error closure implementation"
```

## 自检清单

1. Spec coverage:
   - 后端唯一 `error` 出口：Task 1 + Task 2
   - 后台 task 异常不能只打日志：Task 1 + Task 2
   - 前端退出 loading：Task 3
   - 已有 timeline/正文保留：Task 1 + Task 3
   - 无正文/有正文两类错误落地：Task 3
2. Placeholder scan:
   - 计划中没有 `TBD/TODO/后续补` 这类占位语。
   - 每个改动步骤都给了明确代码片段和验证命令。
3. Type consistency:
   - 后端统一使用现有 `ApiErrorPayload` 字段：`error_code/message/details/provider/retryable`
   - 前端消息状态仍围绕现有 `ChatMessage.content` 和 `isStreaming` 收口，没有引入额外状态模型。
