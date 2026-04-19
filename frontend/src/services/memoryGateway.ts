import { mockMemories } from '../mocks/memories'
import { Memory, MemoryPayload } from '../types/memory'
import { deleteVoid, getJson, postJson, putJson } from './http'

type ListMemoriesParams = {
  keyword?: string
}

export interface MemoryGateway {
  listMemories(params?: ListMemoriesParams): Promise<Memory[]>
  updateMemory(input: { id: string; payload: MemoryPayload }): Promise<Memory>
  deleteMemory(id: string): Promise<void>
  addToKnowledgeGraph(memory: Memory): Promise<void>
}

type MemoryGatewayMode = 'mock' | 'temporal'

let memoryStore: Memory[] = [...mockMemories]

function applyFilters(items: Memory[], params?: ListMemoriesParams) {
  const normalizedKeyword = params?.keyword?.trim().toLowerCase() || ''

  return items.filter((memory) => {
    const hitKeyword =
      normalizedKeyword.length === 0 ||
      memory.title.toLowerCase().includes(normalizedKeyword) ||
      memory.content.toLowerCase().includes(normalizedKeyword)

    return hitKeyword
  })
}

export const mockMemoryGateway: MemoryGateway = {
  async listMemories(params) {
    const filtered = applyFilters(memoryStore, params)
    return filtered.sort((a, b) => {
      const left = a.updated_at || a.created_at || ''
      const right = b.updated_at || b.created_at || ''
      return right.localeCompare(left)
    })
  },

  async updateMemory(input) {
    const target = memoryStore.find((memory) => memory.id === input.id)
    if (!target) {
      throw new Error('未找到要更新的知识')
    }

    const updatedMemory: Memory = {
      ...target,
      ...input.payload,
      updated_at: new Date().toISOString(),
    }

    memoryStore = memoryStore.map((memory) => (memory.id === input.id ? updatedMemory : memory))
    return updatedMemory
  },

  async deleteMemory(id) {
    memoryStore = memoryStore.filter((memory) => memory.id !== id)
  },

  async addToKnowledgeGraph(_memory) {
    await new Promise((resolve) => {
      setTimeout(resolve, 300)
    })
  },
}

export const temporalGraphGateway: MemoryGateway = {
  listMemories(params) {
    return getJson<Memory[]>('/api/memories', {
      params: {
        keyword: params?.keyword,
      },
    })
  },

  updateMemory(input) {
    return putJson<Memory>(`/api/memories/${input.id}`, input.payload)
  },

  async deleteMemory(id) {
    await deleteVoid(`/api/memories/${id}`)
  },

  async addToKnowledgeGraph(memory) {
    await postJson(`/api/memories/${memory.id}/add-to-graph`)
  },
}

function resolveMemoryGateway(mode: MemoryGatewayMode): MemoryGateway {
  if (mode === 'temporal') {
    return temporalGraphGateway
  }

  return mockMemoryGateway
}

const configuredMode = (import.meta.env.VITE_MEMORY_GATEWAY_MODE ?? 'temporal') as MemoryGatewayMode

export const memoryGateway: MemoryGateway = resolveMemoryGateway(configuredMode)
