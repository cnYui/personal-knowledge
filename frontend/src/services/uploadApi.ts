import { UploadMemoryInput, UploadMemoryResponse } from '../types/upload'
import { http } from './http'

export async function uploadMemory(input: UploadMemoryInput) {
  const formData = new FormData()
  formData.append('content', input.content)
  input.images.forEach((image) => formData.append('images', image))

  const { data } = await http.post<UploadMemoryResponse>('/api/uploads/memories', formData)
  return data
}
