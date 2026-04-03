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

function buildThinkingTimelineFromEvents(timelineEvents: ChatTimelineEvent[]) {
  if (!timelineEvents.length) return null

  const latestById = new Map<string, ChatTimelineEvent>()
  timelineEvents
    .slice()
    .sort((a, b) => a.order - b.order)
    .forEach((event) => {
      latestById.set(event.id, event)
    })

  const items: ThinkingTimelineItem[] = Array.from(latestById.values())
    .sort((a, b) => a.order - b.order)
    .map((event) => ({
      key: event.id,
      label: event.title,
      detail: event.detail,
      status: event.status === 'error' ? 'error' : event.status === 'done' ? 'done' : 'current',
      previewItems: event.preview_items ?? [],
      previewTotal: event.preview_total ?? null,
    }))

  return items
}

function buildThinkingTimeline(timelineEvents: ChatTimelineEvent[], trace: AgentTrace | null, active: boolean) {
  const fromEvents = buildThinkingTimelineFromEvents(timelineEvents)
  if (fromEvents?.length) {
    const hasCurrent = fromEvents.some((item) => item.status === 'current')
    if (active && !hasCurrent) {
      const hasUnderstand = fromEvents.some((item) => item.key === 'understand-question')
      const hasRetrieval = fromEvents.some((item) => item.key.startsWith('tool-round-'))
      const hasFinalAnswer = fromEvents.some((item) => item.key === 'final-answer')

      if (!hasUnderstand) {
        return [
          {
            key: 'placeholder-understand',
            label: '理解问题',
            detail: '正在理解你的问题',
            status: 'current' as const,
            placeholder: true,
          },
        ]
      }

      if (!hasRetrieval && !hasFinalAnswer) {
        return [
          ...fromEvents,
          {
            key: 'placeholder-retrieval',
            label: '准备检索',
            detail: '正在准备知识图谱检索',
            status: 'current' as const,
            placeholder: true,
          },
        ]
      }

      if (hasRetrieval && !hasFinalAnswer) {
        return [
          ...fromEvents,
          {
            key: 'placeholder-answer',
            label: '组织最终回答',
            detail: '正在基于当前证据生成回答',
            status: 'current' as const,
            placeholder: true,
          },
        ]
      }
    }
    return fromEvents
  }

  const toolSteps = trace?.tool_loop?.tool_steps ?? []
  if (toolSteps.length) {
    const timeline: ThinkingTimelineItem[] = toolSteps.map((step) => {
      const query = typeof step.arguments?.query === 'string' ? step.arguments.query : ''
      const hitCount = step.result_summary?.retrieved_edge_count
      const evidence = step.result_summary?.has_enough_evidence
      const suffix = typeof hitCount === 'number' ? `，命中 ${hitCount} 条图谱证据` : ''
      const evidenceText =
        typeof evidence === 'boolean' ? `，证据${evidence ? '已足够' : '仍不足'}` : ''
      return {
        key: `round-${step.round_index}`,
        label: `检索第 ${step.round_index + 1} 轮`,
        detail: query ? `使用查询"${query}"发起知识图谱检索${suffix}${evidenceText}。` : `发起第 ${step.round_index + 1} 轮知识图谱检索${suffix}${evidenceText}。`,
        status: 'done' as const,
      }
    })

    const finalAction = trace?.final_action
    if (finalAction === 'kb_grounded_answer') {
      timeline.push({
        key: 'final-answer',
        label: '组织最终回答',
        detail: 'Agent 已停止继续检索，正在基于当前证据生成最终回答。',
        status: 'current' as const,
      })
    } else if (finalAction === 'kb_plus_general_answer') {
      timeline.push({
        key: 'final-fallback',
        label: '补充通用回答',
        detail: '知识库证据仍不足，正在补充通用模型回答并保留已有引用。',
        status: 'current' as const,
      })
    }
    return timeline
  }

  if (active) {
    return [
      {
        key: 'placeholder-understand',
        label: '理解问题',
        detail: '正在理解你的问题',
        status: 'current' as const,
        placeholder: true,
      },
    ]
  }

  return [
    {
      key: 'idle',
      label: '执行过程',
      detail: '本轮执行轨迹将在这里显示。',
      status: 'done' as const,
    },
  ]
}

export function ThinkingProcess({ timelineEvents, trace, active = false }: ThinkingProcessProps) {
  const [expanded, setExpanded] = useState(false)
  const [typedDetail, setTypedDetail] = useState('')
  const timeline = useMemo(() => buildThinkingTimeline(timelineEvents, trace, active), [timelineEvents, trace, active])
  const currentStep = timeline[timeline.length - 1]

  useEffect(() => {
    if (!currentStep?.placeholder) {
      setTypedDetail(currentStep?.detail ?? '')
      return
    }

    let frame = 0
    let typingLength = 0
    let deleting = false
    const fullText = currentStep.detail

    const timer = window.setInterval(() => {
      if (!deleting) {
        typingLength = Math.min(fullText.length, typingLength + 1)
        setTypedDetail(fullText.slice(0, typingLength))
        if (typingLength === fullText.length) {
          frame += 1
          if (frame >= 12) {
            deleting = true
            frame = 0
          }
        }
        return
      }

      typingLength = Math.max(0, typingLength - 1)
      setTypedDetail(fullText.slice(0, typingLength))
      if (typingLength === 0) {
        deleting = false
      }
    }, 55)

    return () => window.clearInterval(timer)
  }, [currentStep])

  const currentDetail = currentStep.placeholder ? typedDetail || ' ' : currentStep.detail
  const stepCount = timeline.length

  // 如果没有有效的时间线，不显示组件
  if (!currentStep || currentStep.key === 'idle') {
    return null
  }

  return (
    <Box sx={{ mb: 1 }}>
      <Box
        onClick={() => setExpanded((value) => !value)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          cursor: 'pointer',
          userSelect: 'none',
          '&:hover': {
            opacity: 0.8,
          },
        }}
      >
        <Typography
          variant="caption"
          sx={{
            color: 'text.secondary',
            lineHeight: 1.4,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            flex: 1,
          }}
        >
          {currentDetail}
          {!active && stepCount > 1 && ` · 共${stepCount}步`}
        </Typography>
        <ExpandMoreIcon
          sx={{
            fontSize: 16,
            color: 'text.secondary',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 180ms ease',
          }}
        />
      </Box>

      {/* 展开内容将在下一个任务实现 */}
    </Box>
  )
}
