import { UploadMemoryInput, UploadMemoryResponse } from '../types/upload'
import { postForm } from './http'

export async function uploadMemory(input: UploadMemoryInput) {
  const formData = new FormData()
  formData.append('content', input.content)
  input.images.forEach((image) => formData.append('images', image))

  return postForm<UploadMemoryResponse>('/api/uploads/memories', formData)
}
