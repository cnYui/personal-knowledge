import { Alert, Box, Stack, Typography } from '@mui/material'
import { useMemo, useState } from 'react'

import { useAppToast } from '../components/common/AppToastProvider'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { ErrorState } from '../components/common/ErrorState'
import { LoadingState } from '../components/common/LoadingState'
import { MemoryBubbleList } from '../components/memory/MemoryBubbleList'
import { MemoryDetailDialog } from '../components/memory/MemoryDetailDialog'
import { MemoryEditDialog } from '../components/memory/MemoryEditDialog'
import { MemoryFilterBar } from '../components/memory/MemoryFilterBar'
import {
  useAddMemoryToKnowledgeGraph,
  useDeleteMemory,
  useMemories,
  useUpdateMemory,
} from '../hooks/useMemories'
import { normalizeApiError } from '../services/http'
import { Memory } from '../types/memory'

function resolveAddToGraphErrorMessage(error: unknown) {
  const normalizedError = normalizeApiError(error)
  const message = normalizedError.details || normalizedError.message || ''
  const normalized = message.toLowerCase()
  if (normalized.includes('rate limit') || normalized.includes('429') || normalized.includes('too many requests')) {
    return 'Rate limit exceeded（上游模型限流，请稍后重试）'
  }
  if (message) {
    return message
  }

  return '加入失败，请稍后重试'
}

export function MemoryManagementPage() {
  const { showToast } = useAppToast()
  const [keyword, setKeyword] = useState('')
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null)
  const [editingMemory, setEditingMemory] = useState<Memory | null>(null)
  const [deletingMemory, setDeletingMemory] = useState<Memory | null>(null)
  const { data = [], isLoading, isError } = useMemories(keyword)
  const updateMutation = useUpdateMemory()
  const deleteMutation = useDeleteMemory()
  const addToGraphMutation = useAddMemoryToKnowledgeGraph()

  const empty = useMemo(() => !isLoading && data.length === 0, [data.length, isLoading])

  if (isLoading) return <LoadingState label="正在加载记忆..." />
  if (isError) return <ErrorState message="记忆加载失败" />

  return (
    <Box sx={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', pr: 1 }}>
        <Stack spacing={3}>
          {updateMutation.isError || deleteMutation.isError ? (
            <Alert severity="error">操作失败，请稍后重试。</Alert>
          ) : null}
          <MemoryFilterBar keyword={keyword} onKeywordChange={setKeyword} />
          {empty ? <Typography color="text.secondary">当前没有匹配的记忆。</Typography> : null}

          <MemoryBubbleList memories={data} onSelect={setSelectedMemory} />
        </Stack>
      </Box>

      <MemoryDetailDialog
        memory={selectedMemory}
        open={Boolean(selectedMemory)}
        addingToGraph={addToGraphMutation.isPending}
        onClose={() => setSelectedMemory(null)}
        onEdit={(memory) => {
          setEditingMemory(memory)
        }}
        onDelete={(memory) => {
          setDeletingMemory(memory)
        }}
        onAddToGraph={async (memory) => {
          try {
            await addToGraphMutation.mutateAsync(memory)
            showToast({ severity: 'success', message: '已加入知识图谱处理队列，正在构建中...' })
          } catch (error) {
            showToast({ severity: 'error', message: resolveAddToGraphErrorMessage(error) })
          }
        }}
      />

      <MemoryEditDialog
        memory={editingMemory}
        open={Boolean(editingMemory)}
        loading={updateMutation.isPending}
        onClose={() => {
          setEditingMemory(null)
        }}
        onSubmit={async (payload) => {
          if (!editingMemory) return
          await updateMutation.mutateAsync({ id: editingMemory.id, payload })
          setEditingMemory(null)
          setSelectedMemory(null)
          showToast({ severity: 'success', message: '知识已更新' })
        }}
      />

      <ConfirmDialog
        open={Boolean(deletingMemory)}
        title="删除记忆"
        description="删除后将无法恢复，确认继续吗？"
        onClose={() => {
          setDeletingMemory(null)
        }}
        onConfirm={async () => {
          if (!deletingMemory) return
          await deleteMutation.mutateAsync(deletingMemory.id)
          setSelectedMemory(null)
          setDeletingMemory(null)
          showToast({ severity: 'success', message: '知识已删除' })
        }}
      />
    </Box>
  )
}
