import { Memory, MemoryPayload } from '../types/memory'
import { memoryGateway } from './memoryGateway'

export async function listMemories(params?: { keyword?: string }) {
  return memoryGateway.listMemories(params)
}

export async function updateMemory(input: { id: string; payload: MemoryPayload }) {
  return memoryGateway.updateMemory(input)
}

export async function deleteMemory(id: string) {
  await memoryGateway.deleteMemory(id)
}

export async function addMemoryToKnowledgeGraph(memory: Memory) {
  await memoryGateway.addToKnowledgeGraph(memory)
}
