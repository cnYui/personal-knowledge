export interface MemoryImage {
  id: string
  original_file_name: string
  stored_path: string
  ocr_text?: string | null
  image_description?: string | null
}

export interface Memory {
  id: string
  title: string
  title_status?: 'pending' | 'ready' | 'failed'
  content: string
  group_id?: string
  created_at?: string | null
  updated_at?: string | null
  images?: MemoryImage[]
  graph_status?: 'not_added' | 'pending' | 'added' | 'failed' | null
  graph_error?: string | null
  graph_added_at?: string | null
  graph_episode_uuid?: string | null
}

export interface MemoryPayload {
  title: string
  content: string
  title_status?: 'pending' | 'ready' | 'failed'
}
