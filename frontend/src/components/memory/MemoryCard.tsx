import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import { Button, Card, CardContent, Collapse, IconButton, Stack, Typography } from '@mui/material'
import { useState } from 'react'

import { Memory } from '../../types/memory'
import { formatDate } from '../../utils/format'

export function MemoryCard({
  memory,
  onEdit,
  onDelete,
}: {
  memory: Memory
  onEdit: (memory: Memory) => void
  onDelete: (memory: Memory) => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <Card sx={{ borderRadius: 3 }}>
      <CardContent>
        <Stack spacing={2}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
            <Stack spacing={1}>
              <Typography variant="h6">{memory.title}</Typography>
              <Typography variant="body2" color="text.secondary">
                更新于 {formatDate(memory.updated_at)}
              </Typography>
            </Stack>
            <Stack direction="row" spacing={1}>
              <IconButton onClick={() => onEdit(memory)}>
                <EditOutlinedIcon />
              </IconButton>
              <IconButton color="error" onClick={() => onDelete(memory)}>
                <DeleteOutlineIcon />
              </IconButton>
            </Stack>
          </Stack>

          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
            {expanded ? memory.content : `${memory.content.slice(0, 180)}${memory.content.length > 180 ? '...' : ''}`}
          </Typography>

          <Collapse in={expanded}>
            <Typography variant="body2" color="text.secondary">
              创建时间：{formatDate(memory.created_at)}
            </Typography>
          </Collapse>

          <Button onClick={() => setExpanded((value) => !value)} sx={{ alignSelf: 'flex-start' }}>
            {expanded ? '收起' : '查看详情'}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  )
}
