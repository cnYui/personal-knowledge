import { requestJson } from './apiClient'
import { ModelConfigRead, ModelConfigUpdate } from '../types/settings'

export function fetchModelConfig() {
  return requestJson<ModelConfigRead>('/api/settings/model-config')
}

export function updateModelConfig(payload: ModelConfigUpdate) {
  return requestJson<ModelConfigRead>('/api/settings/model-config', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}
