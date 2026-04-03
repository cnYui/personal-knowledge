import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { fetchModelConfig, updateModelConfig } from '../services/settingsApi'
import { ModelConfigUpdate } from '../types/settings'

export function useModelConfig() {
  return useQuery({
    queryKey: ['model-config'],
    queryFn: fetchModelConfig,
  })
}

export function useUpdateModelConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ModelConfigUpdate) => updateModelConfig(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(['model-config'], data)
    },
  })
}
