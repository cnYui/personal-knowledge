import { useMutation } from '@tanstack/react-query'

import { uploadMemory } from '../services/uploadApi'

export function useUploadMemory() {
  return useMutation({ mutationFn: uploadMemory })
}
