import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import HubOutlinedIcon from '@mui/icons-material/HubOutlined'
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from '@mui/material'

import { Memory } from '../../types/memory'
import { formatDate } from '../../utils/format'

export function MemoryDetailDialog({
  memory,
  open,
  addingToGraph,
  onClose,
  onEdit,
  onDelete,
  onAddToGraph,
}: {
  memory: Memory | null
  open: boolean
  addingToGraph: boolean
  onClose: () => void
  onEdit: (memory: Memory) => void
  onDelete: (memory: Memory) => void
  onAddToGraph: (memory: Memory) => Promise<void>
}) {
  if (!memory) return null

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>{memory.title}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
            {memory.content}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            创建时间：{formatDate(memory.created_at)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            更新时间：{formatDate(memory.updated_at)}
          </Typography>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button color="error" startIcon={<DeleteOutlineIcon />} onClick={() => onDelete(memory)}>
          删除
        </Button>
        <Button startIcon={<EditOutlinedIcon />} onClick={() => onEdit(memory)}>
          编辑
        </Button>
        <Button
          variant="contained"
          startIcon={<HubOutlinedIcon />}
          disabled={addingToGraph}
          onClick={async () => {
            await onAddToGraph(memory)
          }}
        >
          加入知识图谱
        </Button>
      </DialogActions>
    </Dialog>
  )
}
