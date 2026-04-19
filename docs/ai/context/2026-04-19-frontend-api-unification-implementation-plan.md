# 前端 API 统一收敛实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把前端普通 API 调用收敛到单一 HTTP client，同时保持 hooks 和页面层接口不变，并保留 `chatApi.ts` 的流式特例能力。

**Architecture:** 以 `frontend/src/services/http.ts` 作为唯一底层请求基座，统一 `baseURL`、错误归一化、JSON/FormData/查询参数处理；各领域 `*Api.ts` 只保留业务语义。`chatApi.ts` 继续使用 `fetch` 读取流，但改为复用统一 URL 与错误规范。

**Tech Stack:** React 18、TypeScript、Vite 6、Axios 1、TanStack Query 5、Vitest、jsdom

---

## 文件结构与职责

- `frontend/package.json`
  - 添加 `test` 脚本和前端服务层测试依赖。
- `frontend/package-lock.json`
  - 锁定新增测试依赖版本。
- `frontend/vite.config.ts`
  - 合并 Vitest 配置，确保 `src/**/*.test.ts` 可以直接运行。
- `frontend/src/services/http.ts`
  - 成为唯一底层请求基座，负责 `baseURL`、URL 规范、错误归一化、JSON/FormData/查询参数请求。
- `frontend/src/services/apiClient.ts`
  - 删除；旧导出全部迁移到 `http.ts` 或直接被领域 API 替换。
- `frontend/src/services/http.test.ts`
  - 锁定共享 HTTP client 的 URL 规范、错误归一化和请求 helper 行为。
- `frontend/src/services/domainApi.test.ts`
  - 锁定 `dailyReviewApi.ts`、`settingsApi.ts`、`graphApi.ts`、`promptApi.ts` 对统一 helper 的调用方式。
- `frontend/src/services/chatApi.test.ts`
  - 锁定流式接口继续走 `fetch`，但复用统一 URL 和错误规范。
- `frontend/src/services/dailyReviewApi.ts`
  - 改为只通过共享 GET helper 拉取每日回顾。
- `frontend/src/services/settingsApi.ts`
  - 改为只通过共享 GET/PUT helper 访问模型设置。
- `frontend/src/services/graphApi.ts`
  - 改为只通过共享 GET helper 访问图谱数据，并保留查询参数语义。
- `frontend/src/services/promptApi.ts`
  - 改为只通过共享 GET/PUT/POST helper 管理提示词。
- `frontend/src/services/memoryGateway.ts`
  - 保持 mock/temporal 网关边界，但 temporal 实现切到统一 helper。
- `frontend/src/services/textApi.ts`
  - 改为只通过共享 POST helper 访问文本优化接口。
- `frontend/src/services/uploadApi.ts`
  - 改为只通过共享 FormData helper 访问上传接口。
- `frontend/src/services/chatApi.ts`
  - 保留流式逻辑，但改为从 `http.ts` 引用 `buildApiUrl`、`createApiError`、`normalizeApiError`。
- `frontend/src/components/upload/PromptEditor.tsx`
  - 错误处理导入路径改到 `http.ts`。
- `frontend/src/components/upload/UploadForm.tsx`
  - 错误处理导入路径改到 `http.ts`。
- `frontend/src/pages/MemoryManagementPage.tsx`
  - 错误处理导入路径改到 `http.ts`。
- `frontend/src/pages/MemoryUploadPage.tsx`
  - 错误处理导入路径改到 `http.ts`。
- `frontend/src/pages/SettingsPage.tsx`
  - 错误处理导入路径改到 `http.ts`。

### Task 1: 建立前端服务层测试基建

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: 为前端补上测试入口**

在 `frontend/package.json` 中加入前端测试脚本和依赖：

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "devDependencies": {
    "@types/react": "^18.3.20",
    "@types/react-dom": "^18.3.6",
    "@vitejs/plugin-react": "^4.4.1",
    "jsdom": "^26.0.0",
    "typescript": "^5.8.2",
    "vite": "^6.2.0",
    "vitest": "^3.1.0"
  }
}
```

- [ ] **Step 2: 安装并锁定测试依赖**

Run: `npm --prefix frontend install`

Expected: `frontend/package-lock.json` 出现 `vitest`、`jsdom` 相关条目，命令退出码为 0。

- [ ] **Step 3: 把 Vitest 配进现有 Vite 配置**

把 `frontend/vite.config.ts` 改成同时承载构建配置和测试配置：

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    clearMocks: true,
    restoreMocks: true,
  },
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.indexOf('node_modules') === -1) {
            return
          }

          if (id.indexOf('reactflow') !== -1) {
            return 'graph-vendor'
          }

          if (id.indexOf('react-markdown') !== -1 || id.indexOf('remark-gfm') !== -1) {
            return 'markdown-vendor'
          }

          if (id.indexOf('@tanstack/react-query') !== -1 || id.indexOf('axios') !== -1) {
            return 'data-vendor'
          }

          if (id.indexOf('react-router-dom') !== -1) {
            return 'router-vendor'
          }

          if (
            id.indexOf('react') !== -1 ||
            id.indexOf('react-dom') !== -1 ||
            id.indexOf('@mui/') !== -1 ||
            id.indexOf('@emotion/') !== -1
          ) {
            return 'ui-vendor'
          }
        },
      },
    },
  },
})
```

- [ ] **Step 4: 运行空测试入口，确认基建可执行**

Run: `npm --prefix frontend exec vitest run --passWithNoTests`

Expected: 输出 `No test files found` 或 `0 passed`，退出码为 0。

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts
git commit -m "chore(frontend): add vitest service test harness"
```

### Task 2: 收口共享 HTTP client 并锁定公共行为

**Files:**
- Modify: `frontend/src/services/http.ts`
- Create: `frontend/src/services/http.test.ts`
- Test: `frontend/src/services/http.test.ts`

- [ ] **Step 1: 先写共享 client 的失败用例**

创建 `frontend/src/services/http.test.ts`：

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiRequestError } from '../types/api'
import { buildApiUrl, createApiError, getJson, http, normalizeApiError, postJson } from './http'

describe('http service', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('buildApiUrl 会统一补齐前导斜杠', () => {
    expect(buildApiUrl('api/ping')).toBe('http://127.0.0.1:8000/api/ping')
    expect(buildApiUrl('/api/ping')).toBe('http://127.0.0.1:8000/api/ping')
  })

  it('getJson 通过共享 axios client 返回 data', async () => {
    vi.spyOn(http, 'request').mockResolvedValue({ data: { ok: true } } as never)

    await expect(getJson<{ ok: boolean }>('/api/ping')).resolves.toEqual({ ok: true })
  })

  it('postJson 失败时抛出归一化后的 ApiRequestError', async () => {
    vi.spyOn(http, 'request').mockRejectedValue({
      isAxiosError: true,
      message: 'Request failed',
      response: {
        status: 429,
        data: {
          message: 'rate limited',
          error_code: 'RATE_LIMITED',
          retryable: true,
        },
      },
    })

    await expect(postJson('/api/ping', { ok: true })).rejects.toMatchObject({
      name: 'ApiRequestError',
      payload: expect.objectContaining({
        status: 429,
        error_code: 'RATE_LIMITED',
        message: 'rate limited',
        retryable: true,
      }),
    })
  })

  it('createApiError 会读取 fetch Response 的 JSON 错误体', async () => {
    const response = new Response(JSON.stringify({ message: 'bad request', error_code: 'BAD_REQUEST' }), {
      status: 400,
      headers: { 'content-type': 'application/json' },
    })

    await expect(createApiError(response)).resolves.toBeInstanceOf(ApiRequestError)
  })

  it('normalizeApiError 对未知异常回退为通用消息', () => {
    expect(normalizeApiError('boom')).toEqual({
      message: '请求失败，请稍后重试。',
    })
  })
})
```

- [ ] **Step 2: 运行失败用例，确认共享 helper 还没齐**

Run: `npm --prefix frontend run test -- src/services/http.test.ts`

Expected: FAIL，报错集中在 `getJson` / `postJson` 缺失或行为不匹配。

- [ ] **Step 3: 在 `http.ts` 中实现唯一共享请求基座**

把 `frontend/src/services/http.ts` 收口成唯一底层 client：

```ts
import axios, { AxiosRequestConfig } from 'axios'

import { ApiErrorPayload, ApiRequestError } from '../types/api'
import { DEFAULT_API_BASE_URL } from '../utils/constants'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, '')

export const http = axios.create({
  baseURL: API_BASE_URL,
})

type RequestOptions = Omit<AxiosRequestConfig, 'url' | 'method' | 'data'>

export function buildApiUrl(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}

async function parseErrorBody(response: Response): Promise<Record<string, unknown> | null> {
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    try {
      return (await response.json()) as Record<string, unknown>
    } catch {
      return null
    }
  }

  const text = await response.text().catch(() => '')
  return text ? { message: text } : null
}

export async function createApiError(response: Response): Promise<ApiRequestError> {
  const body = await parseErrorBody(response)
  return new ApiRequestError({
    status: response.status,
    error_code: typeof body?.error_code === 'string' ? body.error_code : undefined,
    message: typeof body?.message === 'string' ? body.message : `请求失败（${response.status}）`,
    details: typeof body?.details === 'string' ? body.details : undefined,
    provider: typeof body?.provider === 'string' ? body.provider : undefined,
    retryable: typeof body?.retryable === 'boolean' ? body.retryable : undefined,
  })
}

export function normalizeApiError(error: unknown): ApiErrorPayload {
  if (error instanceof ApiRequestError) {
    return error.payload
  }

  if (axios.isAxiosError(error)) {
    const data = error.response?.data as Record<string, unknown> | undefined
    return {
      status: error.response?.status,
      error_code: typeof data?.error_code === 'string' ? data.error_code : undefined,
      message: typeof data?.message === 'string' ? data.message : error.message || '请求失败，请稍后重试。',
      details: typeof data?.details === 'string' ? data.details : undefined,
      provider: typeof data?.provider === 'string' ? data.provider : undefined,
      retryable: typeof data?.retryable === 'boolean' ? data.retryable : undefined,
    }
  }

  if (error instanceof Error) {
    return { message: error.message || '请求失败，请稍后重试。' }
  }

  return { message: '请求失败，请稍后重试。' }
}

async function requestJson<T>(method: AxiosRequestConfig['method'], url: string, data?: unknown, config?: RequestOptions) {
  try {
    const response = await http.request<T>({
      ...config,
      method,
      url,
      data,
    })
    return response.data
  } catch (error) {
    throw new ApiRequestError(normalizeApiError(error))
  }
}

export function getJson<T>(url: string, config?: RequestOptions) {
  return requestJson<T>('GET', url, undefined, config)
}

export function postJson<T>(url: string, data?: unknown, config?: RequestOptions) {
  return requestJson<T>('POST', url, data, config)
}

export function putJson<T>(url: string, data?: unknown, config?: RequestOptions) {
  return requestJson<T>('PUT', url, data, config)
}

export async function deleteVoid(url: string, config?: RequestOptions) {
  await requestJson<unknown>('DELETE', url, undefined, config)
}

export function postForm<T>(url: string, data: FormData, config?: RequestOptions) {
  return requestJson<T>('POST', url, data, config)
}
```

- [ ] **Step 4: 运行共享 client 用例，确认公共行为已经稳定**

Run: `npm --prefix frontend run test -- src/services/http.test.ts`

Expected: PASS，输出 `5 passed`。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/http.ts frontend/src/services/http.test.ts
git commit -m "refactor(frontend): unify shared http client"
```

### Task 3: 迁移普通 JSON 领域 API 到统一 helper

**Files:**
- Modify: `frontend/src/services/dailyReviewApi.ts`
- Modify: `frontend/src/services/settingsApi.ts`
- Modify: `frontend/src/services/graphApi.ts`
- Modify: `frontend/src/services/promptApi.ts`
- Create: `frontend/src/services/domainApi.test.ts`
- Test: `frontend/src/services/domainApi.test.ts`

- [ ] **Step 1: 先写领域 API 调用约束的失败用例**

创建 `frontend/src/services/domainApi.test.ts`：

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getJson = vi.fn()
const putJson = vi.fn()
const postJson = vi.fn()

vi.mock('./http', () => ({
  getJson,
  putJson,
  postJson,
}))

import { fetchDailyReview } from './dailyReviewApi'
import { fetchGraphData } from './graphApi'
import {
  fetchAllPrompts,
  fetchComposedPrompt,
  fetchKnowledgeProfile,
  fetchPrompt,
  resetPrompt,
  updatePrompt,
} from './promptApi'
import { fetchModelConfig, updateModelConfig } from './settingsApi'

describe('domain api modules', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchDailyReview 使用共享 GET helper', async () => {
    getJson.mockResolvedValue({ summary: 'ok' })
    await fetchDailyReview()
    expect(getJson).toHaveBeenCalledWith('/api/daily-review')
  })

  it('fetchModelConfig 与 updateModelConfig 走统一 settings endpoint', async () => {
    getJson.mockResolvedValue({ dialog: {}, knowledge_build: {} })
    putJson.mockResolvedValue({ dialog: {}, knowledge_build: {} })

    await fetchModelConfig()
    await updateModelConfig({ dialog_api_key: 'abc' })

    expect(getJson).toHaveBeenCalledWith('/api/settings/model-config')
    expect(putJson).toHaveBeenCalledWith('/api/settings/model-config', { dialog_api_key: 'abc' })
  })

  it('fetchGraphData 会转发 group_id 和 limit 查询参数', async () => {
    getJson.mockResolvedValue({ nodes: [], edges: [] })
    await fetchGraphData('focus', 20)
    expect(getJson).toHaveBeenCalledWith('/api/graph/data', {
      params: { group_id: 'focus', limit: 20 },
    })
  })

  it('prompt 相关接口都通过统一 helper 调用对应 endpoint', async () => {
    getJson.mockResolvedValue({})
    putJson.mockResolvedValue({})
    postJson.mockResolvedValue({})

    await fetchAllPrompts()
    await fetchPrompt('text_optimization')
    await updatePrompt('text_optimization', { content: 'next' })
    await resetPrompt('text_optimization')
    await fetchKnowledgeProfile()
    await fetchComposedPrompt()

    expect(getJson).toHaveBeenCalledWith('/api/prompts')
    expect(getJson).toHaveBeenCalledWith('/api/prompts/text_optimization')
    expect(putJson).toHaveBeenCalledWith('/api/prompts/text_optimization', { content: 'next' })
    expect(postJson).toHaveBeenCalledWith('/api/prompts/text_optimization/reset')
    expect(getJson).toHaveBeenCalledWith('/api/prompts/knowledge-profile')
    expect(getJson).toHaveBeenCalledWith('/api/prompts/composed-system-prompt')
  })
})
```

- [ ] **Step 2: 运行失败用例，确认当前领域模块还没完全收口**

Run: `npm --prefix frontend run test -- src/services/domainApi.test.ts`

Expected: FAIL，报错集中在领域模块仍引用 `apiClient.ts` 或直接使用 `axios`。

- [ ] **Step 3: 把普通 JSON API 全部迁移到统一 helper**

按下面的最小实现收口领域模块：

`frontend/src/services/dailyReviewApi.ts`

```ts
import { getJson } from './http'
import { DailyReviewResponse } from '../types/dailyReview'

export function fetchDailyReview() {
  return getJson<DailyReviewResponse>('/api/daily-review')
}
```

`frontend/src/services/settingsApi.ts`

```ts
import { getJson, putJson } from './http'
import { ModelConfigRead, ModelConfigUpdate } from '../types/settings'

export function fetchModelConfig() {
  return getJson<ModelConfigRead>('/api/settings/model-config')
}

export function updateModelConfig(payload: ModelConfigUpdate) {
  return putJson<ModelConfigRead>('/api/settings/model-config', payload)
}
```

`frontend/src/services/graphApi.ts`

```ts
import { getJson } from './http'
import { GraphData } from '../types/graph'

export function fetchGraphData(groupId: string = 'default', limit: number = 50): Promise<GraphData> {
  return getJson<GraphData>('/api/graph/data', {
    params: { group_id: groupId, limit },
  })
}
```

`frontend/src/services/promptApi.ts`

```ts
import { getJson, postJson, putJson } from './http'
import { ComposedPrompt, KnowledgeProfile, PromptConfig, PromptConfigUpdate } from '../types/prompt'

export function fetchAllPrompts(): Promise<Record<string, PromptConfig>> {
  return getJson<Record<string, PromptConfig>>('/api/prompts')
}

export function fetchPrompt(key: string): Promise<PromptConfig> {
  return getJson<PromptConfig>(`/api/prompts/${key}`)
}

export function updatePrompt(key: string, data: PromptConfigUpdate): Promise<PromptConfig> {
  return putJson<PromptConfig>(`/api/prompts/${key}`, data)
}

export function resetPrompt(key: string): Promise<PromptConfig> {
  return postJson<PromptConfig>(`/api/prompts/${key}/reset`)
}

export function fetchKnowledgeProfile(): Promise<KnowledgeProfile> {
  return getJson<KnowledgeProfile>('/api/prompts/knowledge-profile')
}

export function fetchComposedPrompt(): Promise<ComposedPrompt> {
  return getJson<ComposedPrompt>('/api/prompts/composed-system-prompt')
}
```

- [ ] **Step 4: 运行领域 API 用例，确认迁移后的 endpoint 行为稳定**

Run: `npm --prefix frontend run test -- src/services/domainApi.test.ts`

Expected: PASS，输出 `4 passed`。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/dailyReviewApi.ts frontend/src/services/settingsApi.ts frontend/src/services/graphApi.ts frontend/src/services/promptApi.ts frontend/src/services/domainApi.test.ts
git commit -m "refactor(frontend): migrate domain api modules"
```

### Task 4: 对齐流式特例、遗留服务和错误导入点，并删除旧基座

**Files:**
- Modify: `frontend/src/services/memoryGateway.ts`
- Modify: `frontend/src/services/textApi.ts`
- Modify: `frontend/src/services/uploadApi.ts`
- Modify: `frontend/src/services/chatApi.ts`
- Delete: `frontend/src/services/apiClient.ts`
- Modify: `frontend/src/components/upload/PromptEditor.tsx`
- Modify: `frontend/src/components/upload/UploadForm.tsx`
- Modify: `frontend/src/pages/MemoryManagementPage.tsx`
- Modify: `frontend/src/pages/MemoryUploadPage.tsx`
- Modify: `frontend/src/pages/SettingsPage.tsx`
- Create: `frontend/src/services/chatApi.test.ts`
- Test: `frontend/src/services/chatApi.test.ts`

- [ ] **Step 1: 先写流式接口与旧导入清理的失败用例**

创建 `frontend/src/services/chatApi.test.ts`：

```ts
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
```

- [ ] **Step 2: 运行失败用例，确认 chat 与旧导入仍依赖 `apiClient.ts`**

Run: `npm --prefix frontend run test -- src/services/chatApi.test.ts`

Expected: FAIL，报错集中在导入路径或共享 helper 行为不匹配。

- [ ] **Step 3: 清理遗留服务与导入点，删除旧 `apiClient.ts`**

按下面的最小改动完成收口：

`frontend/src/services/memoryGateway.ts`

```ts
import { deleteVoid, getJson, postJson, putJson } from './http'

export const temporalGraphGateway: MemoryGateway = {
  async listMemories(params) {
    return getJson<Memory[]>('/api/memories', {
      params: {
        keyword: params?.keyword,
      },
    })
  },

  async updateMemory(input) {
    return putJson<Memory>(`/api/memories/${input.id}`, input.payload)
  },

  async deleteMemory(id) {
    await deleteVoid(`/api/memories/${id}`)
  },

  async addToKnowledgeGraph(memory) {
    await postJson(`/api/memories/${memory.id}/add-to-graph`)
  },
}
```

`frontend/src/services/textApi.ts`

```ts
import { postJson } from './http'

export async function optimizeText(text: string): Promise<string> {
  const data = await postJson<TextOptimizationResponse>('/api/text/optimize', { text })
  return data.optimized_text
}
```

`frontend/src/services/uploadApi.ts`

```ts
import { UploadMemoryInput, UploadMemoryResponse } from '../types/upload'
import { postForm } from './http'

export async function uploadMemory(input: UploadMemoryInput) {
  const formData = new FormData()
  formData.append('content', input.content)
  input.images.forEach((image) => formData.append('images', image))

  return postForm<UploadMemoryResponse>('/api/uploads/memories', formData)
}
```

`frontend/src/services/chatApi.ts`

```ts
import { buildApiUrl, createApiError, normalizeApiError } from './http'
```

页面和组件的错误处理导入统一改为：

```ts
import { normalizeApiError } from '../services/http'
```

组件内相对路径版本统一改为：

```ts
import { normalizeApiError } from '../../services/http'
```

然后删除旧文件：

```bash
git rm frontend/src/services/apiClient.ts
```

- [ ] **Step 4: 运行测试、构建和遗留写法扫描，确认旧基座已经被清空**

Run: `npm --prefix frontend run test -- src/services/chatApi.test.ts`

Expected: PASS，输出 `2 passed`。

Run: `npm --prefix frontend run test`

Expected: PASS，输出 `11 passed`。

Run: `npm --prefix frontend run build`

Expected: PASS，Vite 构建成功，无 TypeScript 错误。

Run: `Get-ChildItem -Recurse 'frontend/src' -Include *.ts,*.tsx | Select-String -Pattern 'apiClient|axios\\.get\\(|axios\\.put\\(|fetch\\(buildApiUrl\\('`

Expected: 没有 `apiClient` 命中；`fetch(buildApiUrl(` 只允许出现在 `frontend/src/services/chatApi.ts`。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/http.ts frontend/src/services/memoryGateway.ts frontend/src/services/textApi.ts frontend/src/services/uploadApi.ts frontend/src/services/chatApi.ts frontend/src/components/upload/PromptEditor.tsx frontend/src/components/upload/UploadForm.tsx frontend/src/pages/MemoryManagementPage.tsx frontend/src/pages/MemoryUploadPage.tsx frontend/src/pages/SettingsPage.tsx frontend/src/services/chatApi.test.ts
git rm frontend/src/services/apiClient.ts
git commit -m "refactor(frontend): align stream api and remove api client"
```

## 自检结果

- Spec coverage：共享 client、普通 JSON API、流式特例、错误归一化导入点、遗留基座删除、前端构建验证，都已有对应任务。
- Placeholder scan：计划中没有 `TODO`、`TBD`、`implement later` 之类占位符。
- Type consistency：统一 helper 以 `getJson` / `postJson` / `putJson` / `deleteVoid` / `postForm` 命名，后续任务保持一致。
