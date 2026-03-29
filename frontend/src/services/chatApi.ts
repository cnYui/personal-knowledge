import { ChatMessage, ChatResponse } from '../types/chat'
import { http } from './http'

export async function fetchChatMessages() {
  const { data } = await http.get<ChatMessage[]>('/api/chat/messages')
  return data
}

export async function sendChatMessage(message: string) {
  const { data } = await http.post<ChatResponse>('/api/chat/messages', { message })
  return data
}

export async function clearChatMessages() {
  const { data } = await http.delete<{ success: boolean }>('/api/chat/messages')
  return data
}
