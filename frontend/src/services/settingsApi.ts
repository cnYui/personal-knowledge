import { getJson, putJson } from './http'
import { ModelConfigRead, ModelConfigUpdate } from '../types/settings'

export function fetchModelConfig() {
  return getJson<ModelConfigRead>('/api/settings/model-config')
}

export function updateModelConfig(payload: ModelConfigUpdate) {
  return putJson<ModelConfigRead>('/api/settings/model-config', payload)
}
