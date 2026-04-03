import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import MoreHorizRoundedIcon from '@mui/icons-material/MoreHorizRounded'
import { Box, Chip, Collapse, Stack, Typography } from '@mui/material'
import { useEffect, useMemo, useState } from 'react'

import { AgentTrace, ChatTimelineEvent } from '../../types/chat'

type ThinkingTimelineItem = {
  key: string
  label: string
  detail: string
  status: 'done' | 'current' | 'error'
  previewItems?: string[]
  previewTotal?: number | null
  placeholder?: boolean
}

interface ThinkingProcessProps {
  timelineEvents: ChatTimelineEvent[]
  trace: AgentTrace | null
  active?: boolean
}

export function ThinkingProcess({ timelineEvents, trace, active = false }: ThinkingProcessProps) {
  return null
}
