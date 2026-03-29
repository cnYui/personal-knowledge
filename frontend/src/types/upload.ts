export interface UploadMemoryInput {
  content: string
  images: File[]
}

export interface UploadMemoryResponse {
  id: string
  title: string
  title_status: 'pending' | 'ready' | 'failed'
  content: string
  group_id: string
  images_count: number
  processing_status: string
}
