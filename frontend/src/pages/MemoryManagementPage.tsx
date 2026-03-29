import { Alert, Snackbar, Stack, Typography } from '@mui/material'
import { useMemo, useState } from 'react'

import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { ErrorState } from '../components/common/ErrorState'
import { LoadingState } from '../components/common/LoadingState'
import { PageHeader } from '../components/common/PageHeader'
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
import { Memory } from '../types/memory'

export function MemoryManagementPage() {
  const [keyword, setKeyword] = useState('')
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null)
  const [editingMemory, setEditingMemory] = useState<Memory | null>(null)
  const [deletingMemory, setDeletingMemory] = useState<Memory | null>(null)
  const [feedback, setFeedback] = useState<{ open: boolean; message: string }>({
    open: false,
    message: '',
  })
  const { data = [], isLoading, isError } = useMemories(keyword)
  const updateMutation = useUpdateMemory()
  const deleteMutation = useDeleteMemory()
  const addToGraphMutation = useAddMemoryToKnowledgeGraph()

  const empty = useMemo(() => !isLoading && data.length === 0, [data.length, isLoading])

  if (isLoading) return <LoadingState label="正在加载记忆..." />
  if (isError) return <ErrorState message="记忆加载失败" />

  return (
    <Stack spacing={3}>
      <PageHeader title="记忆管理" description="浏览、搜索、编辑和删除你的学习记忆。" />
      {updateMutation.isError || deleteMutation.isError ? (
        <Alert severity="error">操作失败，请稍后重试。</Alert>
      ) : null}
      <MemoryFilterBar keyword={keyword} onKeywordChange={setKeyword} />
      {empty ? <Typography color="text.secondary">当前没有匹配的记忆。</Typography> : null}

      <MemoryBubbleList memories={data} onSelect={setSelectedMemory} />

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
            setFeedback({ open: true, message: '已加入知识图谱（模拟）' })
          } catch {
            setFeedback({ open: true, message: '加入失败，请稍后重试' })
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
          setFeedback({ open: true, message: '知识已更新' })
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
          setFeedback({ open: true, message: '知识已删除' })
        }}
      />

      <Snackbar
        open={feedback.open}
        autoHideDuration={1800}
        onClose={() => {
          setFeedback((prev) => ({ ...prev, open: false }))
        }}
        message={feedback.message}
      />
    </Stack>
  )
}
