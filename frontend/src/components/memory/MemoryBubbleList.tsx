import { Stack } from '@mui/material'

import { Memory } from '../../types/memory'
import { MemoryBubbleItem } from './MemoryBubbleItem'

export function MemoryBubbleList({
  memories,
  onSelect,
}: {
  memories: Memory[]
  onSelect: (memory: Memory) => void
}) {
  return (
    <Stack spacing={1.5}>
      {memories.map((memory) => (
        <MemoryBubbleItem key={memory.id} memory={memory} onSelect={onSelect} />
      ))}
    </Stack>
  )
}
