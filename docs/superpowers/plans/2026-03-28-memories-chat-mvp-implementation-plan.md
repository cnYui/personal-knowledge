# Memories Chat MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `/memories` card list with chat-bubble rows, add detail dialog actions (edit/delete/add-to-graph placeholder), and introduce a pluggable memory gateway backed by mock data for MVP.

**Architecture:** Keep the current React page structure, but route all memory operations through a thin `MemoryGateway` abstraction. Use a mock gateway implementation for list/update/delete/add-to-graph now, so the future temporal knowledge graph backend only requires swapping gateway implementation. UI remains in `MemoryManagementPage` with focused bubble/detail components.

**Tech Stack:** React 18, TypeScript, Material UI, React Query, React Router, Axios

---

### Task 1: Create Gateway + Mock Data Foundation

**Files:**
- Create: `frontend/src/mocks/memories.ts`
- Create: `frontend/src/services/memoryGateway.ts`
- Modify: `frontend/src/services/memoryApi.ts`
- Test: manual UI verification in `/memories`

- [ ] **Step 1: Add mock memories dataset**

```ts
// frontend/src/mocks/memories.ts
import { Memory } from '../types/memory'

export const mockMemories: Memory[] = [
  {
    id: 'm-001',
    title: 'Graphiti 的 Episode 设计',
    content: '每条知识作为一个 episode 写入，保留 valid_at 与 created_at 便于时序追踪。',
    tags: ['graphiti', '知识图谱', '时序'],
    importance: 5,
    created_at: '2026-03-20T09:00:00Z',
    updated_at: '2026-03-20T09:00:00Z',
  },
  // ...再补 8~12 条模拟知识
]
```

- [ ] **Step 2: Create memory gateway interface and mock implementation**

```ts
// frontend/src/services/memoryGateway.ts
import { mockMemories } from '../mocks/memories'
import { Memory, MemoryPayload } from '../types/memory'

type ListParams = { keyword?: string; tag?: string }

export interface MemoryGateway {
  listMemories(params?: ListParams): Promise<Memory[]>
  updateMemory(input: { id: string; payload: MemoryPayload }): Promise<Memory>
  deleteMemory(id: string): Promise<void>
  addToKnowledgeGraph(memory: Memory): Promise<void>
}

let store = [...mockMemories]

export const mockMemoryGateway: MemoryGateway = {
  async listMemories(params) {
    const keyword = (params?.keyword || '').trim().toLowerCase()
    const tag = (params?.tag || '').trim().toLowerCase()
    return store.filter((item) => {
      const hitKeyword =
        !keyword ||
        item.title.toLowerCase().includes(keyword) ||
        item.content.toLowerCase().includes(keyword)
      const hitTag = !tag || item.tags.some((t) => t.toLowerCase().includes(tag))
      return hitKeyword && hitTag
    })
  },
  async updateMemory({ id, payload }) {
    const target = store.find((m) => m.id === id)
    if (!target) throw new Error('Memory not found')
    const updated: Memory = { ...target, ...payload, updated_at: new Date().toISOString() }
    store = store.map((m) => (m.id === id ? updated : m))
    return updated
  },
  async deleteMemory(id) {
    store = store.filter((m) => m.id !== id)
  },
  async addToKnowledgeGraph(_memory) {
    await new Promise((resolve) => setTimeout(resolve, 300))
  },
}

export const memoryGateway = mockMemoryGateway
```

- [ ] **Step 3: Make `memoryApi` delegate to gateway**

```ts
// frontend/src/services/memoryApi.ts
import { memoryGateway } from './memoryGateway'

export const listMemories = memoryGateway.listMemories
export const updateMemory = memoryGateway.updateMemory
export const deleteMemory = memoryGateway.deleteMemory
```

- [ ] **Step 4: Run frontend typecheck/build**

Run: `npm run build`
Expected: build succeeds with no TS errors from new gateway files.

### Task 2: Build Chat Bubble List + Detail Dialog Components

**Files:**
- Create: `frontend/src/components/memory/MemoryBubbleItem.tsx`
- Create: `frontend/src/components/memory/MemoryBubbleList.tsx`
- Create: `frontend/src/components/memory/MemoryDetailDialog.tsx`
- Test: manual interaction verification

- [ ] **Step 1: Implement single bubble item**

```tsx
// MemoryBubbleItem.tsx
import { Paper, Stack, Typography, Chip } from '@mui/material'
import { Memory } from '../../types/memory'

export function MemoryBubbleItem({ memory, onClick }: { memory: Memory; onClick: () => void }) {
  return (
    <Paper
      onClick={onClick}
      sx={{ p: 1.5, borderRadius: 3, maxWidth: '80%', cursor: 'pointer', bgcolor: 'primary.50' }}
      elevation={0}
    >
      <Stack spacing={1}>
        <Typography variant="subtitle2">{memory.title}</Typography>
        <Typography variant="body2" color="text.secondary">
          {memory.content.length > 110 ? `${memory.content.slice(0, 110)}...` : memory.content}
        </Typography>
        <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
          {memory.tags.slice(0, 3).map((tag) => (
            <Chip key={tag} label={tag} size="small" />
          ))}
        </Stack>
      </Stack>
    </Paper>
  )
}
```

- [ ] **Step 2: Implement bubble list wrapper**

```tsx
// MemoryBubbleList.tsx
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
    <Stack spacing={1.25}>
      {memories.map((memory) => (
        <MemoryBubbleItem key={memory.id} memory={memory} onClick={() => onSelect(memory)} />
      ))}
    </Stack>
  )
}
```

- [ ] **Step 3: Implement memory detail dialog with actions**

```tsx
// MemoryDetailDialog.tsx
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from '@mui/material'
import { Memory } from '../../types/memory'
import { formatDate } from '../../utils/format'

export function MemoryDetailDialog({
  memory,
  open,
  onClose,
  onEdit,
  onDelete,
  onAddToGraph,
  adding,
}: {
  memory: Memory | null
  open: boolean
  onClose: () => void
  onEdit: (memory: Memory) => void
  onDelete: (memory: Memory) => void
  onAddToGraph: (memory: Memory) => void
  adding: boolean
}) {
  if (!memory) return null

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>{memory.title}</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={1.5}>
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>{memory.content}</Typography>
          <Typography variant="body2" color="text.secondary">标签：{memory.tags.join('、')}</Typography>
          <Typography variant="body2" color="text.secondary">重要度：{memory.importance}</Typography>
          <Typography variant="body2" color="text.secondary">更新于：{formatDate(memory.updated_at)}</Typography>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button color="error" onClick={() => onDelete(memory)}>删除</Button>
        <Button onClick={() => onEdit(memory)}>编辑</Button>
        <Button variant="contained" onClick={() => onAddToGraph(memory)} disabled={adding}>
          加入知识图谱
        </Button>
      </DialogActions>
    </Dialog>
  )
}
```

- [ ] **Step 4: Run frontend build to validate new components**

Run: `npm run build`
Expected: build succeeds and new components compile.

### Task 3: Refactor `MemoryManagementPage` to New UX and Wire Actions

**Files:**
- Modify: `frontend/src/pages/MemoryManagementPage.tsx`
- Modify: `frontend/src/hooks/useMemories.ts`
- Test: manual e2e in `/memories`

- [ ] **Step 1: Add add-to-graph mutation in hooks**

```ts
// useMemories.ts
import { addMemoryToKnowledgeGraph } from '../services/memoryApi'

export function useAddMemoryToKnowledgeGraph() {
  return useMutation({ mutationFn: addMemoryToKnowledgeGraph })
}
```

- [ ] **Step 2: Export API from memoryApi**

```ts
// memoryApi.ts
import { Memory } from '../types/memory'
import { memoryGateway } from './memoryGateway'

export async function addMemoryToKnowledgeGraph(memory: Memory) {
  await memoryGateway.addToKnowledgeGraph(memory)
}
```

- [ ] **Step 3: Replace card list with bubble list and detail dialog**

```tsx
// MemoryManagementPage.tsx (核心变更)
const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null)
const [snackbar, setSnackbar] = useState<{ open: boolean; message: string }>({ open: false, message: '' })
const addToGraphMutation = useAddMemoryToKnowledgeGraph()

<MemoryBubbleList memories={data} onSelect={setSelectedMemory} />

<MemoryDetailDialog
  memory={selectedMemory}
  open={Boolean(selectedMemory)}
  onClose={() => setSelectedMemory(null)}
  onEdit={(m) => setEditingMemory(m)}
  onDelete={(m) => setDeletingMemory(m)}
  adding={addToGraphMutation.isPending}
  onAddToGraph={async (m) => {
    try {
      await addToGraphMutation.mutateAsync(m)
      setSnackbar({ open: true, message: '已加入知识图谱（模拟）' })
    } catch {
      setSnackbar({ open: true, message: '加入失败，请稍后重试' })
    }
  }}
/>
```

- [ ] **Step 4: Keep existing edit/delete dialog flow compatible with selected memory**

Run: manual verify edit/delete from detail dialog works and list updates.
Expected: edited content refreshes, deleted row disappears.

- [ ] **Step 5: Add snackbar feedback UI**

```tsx
<Snackbar
  open={snackbar.open}
  autoHideDuration={1800}
  onClose={() => setSnackbar({ ...snackbar, open: false })}
  message={snackbar.message}
/>
```

### Task 4: Verification and Cleanup

**Files:**
- Modify (if needed): `frontend/src/pages/MemoryManagementPage.tsx`
- Test: build + manual checklist

- [ ] **Step 1: Run full frontend build**

Run: `npm run build`
Expected: success.

- [ ] **Step 2: Manual acceptance checks**

Checklist:
- `/memories` 页面显示聊天气泡，不显示卡片。
- 点击气泡打开详情弹窗。
- 弹窗内编辑可提交并刷新。
- 弹窗内删除可删除并关闭。
- “加入知识图谱”按钮出现成功 toast。
- 关键字/标签筛选继续生效。

- [ ] **Step 3: Commit**

```bash
git add frontend/src docs/superpowers/specs/2026-03-28-memories-chat-mvp-design.md docs/superpowers/plans/2026-03-28-memories-chat-mvp-implementation-plan.md
git commit -m "feat: switch memories to chat bubbles with mock gateway mvp"
```
