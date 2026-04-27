import { beforeEach, describe, expect, it, vi } from 'vitest'

const { deleteVoid, getJson, putJson, postJson } = vi.hoisted(() => ({
  deleteVoid: vi.fn(),
  getJson: vi.fn(),
  putJson: vi.fn(),
  postJson: vi.fn(),
}))

vi.mock('./http', () => ({
  deleteVoid,
  getJson,
  putJson,
  postJson,
}))

import { fetchDailyReview } from './dailyReviewApi'
import { fetchGraphData } from './graphApi'
import { temporalGraphGateway } from './memoryGateway'
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

  it('memoryGateway 入图操作调用 memories add-to-graph endpoint', async () => {
    postJson.mockResolvedValue({})

    await temporalGraphGateway.addToKnowledgeGraph({ id: 'mem-1' } as never)

    expect(postJson).toHaveBeenCalledWith('/api/memories/mem-1/add-to-graph')
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
