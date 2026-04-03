export interface ApiKeyFieldStatus {
  configured: boolean
  masked_value: string
}

export interface RuntimeModelConfigStatus {
  provider: string
  base_url: string
  model: string
  api_key: ApiKeyFieldStatus
}

export interface ModelConfigRead {
  dialog: RuntimeModelConfigStatus
  knowledge_build: RuntimeModelConfigStatus
}

export interface ModelConfigUpdate {
  dialog_api_key?: string
  knowledge_build_api_key?: string
}
