import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import MoreHorizRoundedIcon from '@mui/icons-material/MoreHorizRounded'
import { Box, Chip, Collapse, Paper, Stack, Tooltip, Typography } from '@mui/material'
import { useEffect, useMemo, useState } from 'react'

import { AgentTrace, ChatMessage, ChatReference, ChatTimelineEvent } from '../../types/chat'
import { MarkdownContent } from './MarkdownContent'

function getReferenceText(reference: ChatReference) {
  return reference.fact || reference.summary || reference.name || reference.type
}

function looksLikeMarkdown(content: string) {
  return /(^|\n)\s*[-*#>`]|\[[^\]]+\]\([^)]+\)|```|\|/.test(content)
}

function splitIntoSentences(content: string) {
  return content
    .split(/(?<=[。！？!?])|\n+/)
    .map((part) => part.trim())
    .filter(Boolean)
}

function buildSentenceReferenceMap(sentences: string[], references: ChatReference[]) {
  const map = new Map<number, ChatReference[]>()

  references.forEach((reference, index) => {
    const sentenceIndex = sentences.length === 0 ? 0 : Math.min(index, sentences.length - 1)
    const existing = map.get(sentenceIndex) ?? []
    existing.push(reference)
    map.set(sentenceIndex, existing)
  })

  return map
}

function CitationList({ references }: { references: ChatReference[] }) {
  return (
    <Stack spacing={0.65} sx={{ mt: 1.75 }}>
      {references.map((reference, index) => (
        <Typography
          key={`${reference.type}-${index}`}
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', fontFamily: 'Poppins, Arial, sans-serif' }}
        >
          [{index + 1}] {getReferenceText(reference)}
        </Typography>
      ))}
    </Stack>
  )
}

function CitationInline({ references }: { references: ChatReference[] }) {
  return (
    <Box component="span" sx={{ ml: 0.5, display: 'inline-flex', alignItems: 'center', flexWrap: 'wrap' }}>
      {references.map((reference, index) => (
        <Tooltip key={`${reference.type}-${index}`} title={getReferenceText(reference)} arrow placement="top">
          <Box
            component="sup"
            sx={{
              mx: 0.25,
              color: 'secondary.main',
              cursor: 'help',
              fontWeight: 700,
              fontSize: '0.75rem',
              lineHeight: 1,
            }}
          >
            [{index + 1}]
          </Box>
        </Tooltip>
      ))}
    </Box>
  )
}

type ThinkingTimelineItem = {
  key: string
  label: string
  detail: string
  status: 'done' | 'current' | 'error'
  previewItems?: string[]
  previewTotal?: number | null
  placeholder?: boolean
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
        detail: query ? `使用查询“${query}”发起知识图谱检索${suffix}${evidenceText}。` : `发起第 ${step.round_index + 1} 轮知识图谱检索${suffix}${evidenceText}。`,
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

function ThinkingSummaryPanel({
  timelineEvents,
  trace,
  active = false,
}: {
  timelineEvents: ChatTimelineEvent[]
  trace: AgentTrace | null
  active?: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const [typedDetail, setTypedDetail] = useState('')
  const timeline = useMemo(() => buildThinkingTimeline(timelineEvents, trace, active), [timelineEvents, trace, active])
  const currentStep = timeline[timeline.length - 1]
  const statusLabel = useMemo(() => {
    if (currentStep.status === 'error') return '异常'
    if (currentStep.status === 'done' && !active) return '已完成'
    if (/检索/.test(currentStep.label)) return '检索中'
    if (/回答|组织/.test(currentStep.label)) return '组织回答'
    return '处理中'
  }, [active, currentStep])

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

  return (
    <Paper
      sx={{
        px: 1.5,
        py: 1.15,
        maxWidth: '80%',
        alignSelf: 'flex-start',
        minWidth: { xs: '100%', md: 560 },
        borderRadius: 0.9,
        border: '1px solid rgba(176, 174, 165, 0.24)',
        background: 'linear-gradient(180deg, rgba(255,253,248,0.96) 0%, rgba(246,243,235,0.96) 100%)',
        color: 'text.secondary',
        boxShadow: '0 14px 30px rgba(20, 20, 19, 0.05)',
        overflow: 'hidden',
      }}
    >
      <Stack spacing={expanded ? 1.5 : 0}>
        <Box
          onClick={() => setExpanded((value) => !value)}
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 1.5,
            cursor: 'pointer',
            userSelect: 'none',
          }}
        >
          <Stack direction="row" spacing={1.25} alignItems="center" sx={{ minWidth: 0, flex: 1 }}>
            <Box
              sx={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                display: 'grid',
                placeItems: 'center',
                color: 'secondary.main',
                background: 'radial-gradient(circle at 30% 30%, rgba(217,119,87,0.2), rgba(217,119,87,0.04))',
                '@keyframes thinkingGlow': {
                  '0%': { transform: 'scale(0.96)', opacity: 0.7 },
                  '100%': { transform: 'scale(1.04)', opacity: 1 },
                },
                animation: 'thinkingGlow 1.2s ease-in-out infinite alternate',
              }}
            >
              <AutoAwesomeRoundedIcon sx={{ fontSize: 18 }} />
            </Box>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography
                variant="body2"
                sx={{
                  fontWeight: 700,
                  color: 'text.primary',
                  lineHeight: 1.4,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {currentDetail}
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                {active ? '思考仍在继续，点击展开查看系统轨迹' : '点击展开查看系统思考轨迹'}
              </Typography>
            </Box>
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              size="small"
              label={active ? statusLabel : '已完成'}
              sx={{
                height: 24,
                bgcolor: 'rgba(232, 230, 220, 0.7)',
                color: 'text.secondary',
                border: '1px solid rgba(176, 174, 165, 0.24)',
                borderRadius: 0.5,
              }}
            />
            <Box
              sx={{
                display: 'grid',
                placeItems: 'center',
                width: 28,
                height: 28,
                borderRadius: '50%',
                bgcolor: 'rgba(232, 230, 220, 0.72)',
                color: 'text.secondary',
                transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform 180ms ease',
              }}
            >
              <ExpandMoreIcon sx={{ fontSize: 20 }} />
            </Box>
          </Stack>
        </Box>

        <Collapse in={expanded} timeout={200}>
          <Stack spacing={1.25} sx={{ pt: 0.5 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ pl: 0.5 }}>
              <Typography variant="caption" sx={{ color: 'text.disabled', letterSpacing: '0.08em' }}>
                执行过程
              </Typography>
              <Chip
                size="small"
                variant="outlined"
                label={`共 ${timeline.length} 步`}
                sx={{ height: 22, borderColor: 'rgba(176, 174, 165, 0.24)', color: 'text.secondary' }}
              />
            </Stack>

            <Box
              sx={{
                position: 'relative',
                pl: 2.25,
                '&:before': {
                  content: '""',
                  position: 'absolute',
                  left: 9,
                  top: 6,
                  bottom: 6,
                  width: 1.5,
                  borderRadius: 0.5,
                  background: 'linear-gradient(180deg, rgba(176,174,165,0.4) 0%, rgba(176,174,165,0.12) 100%)',
                },
              }}
            >
              <Stack spacing={1.2}>
                {timeline.map((step) => {
                  const isCurrent = step.status === 'current'
                  const isDone = step.status === 'done'
                  const isError = step.status === 'error'
                  const stepDetail = step.placeholder && step.key === currentStep.key ? currentDetail : step.detail
                  const previewOverflow =
                    step.previewTotal && step.previewItems?.length
                      ? Math.max(step.previewTotal - step.previewItems.length, 0)
                      : 0

                  return (
                    <Box key={step.key} sx={{ position: 'relative', pl: 1.25 }}>
                      <Box
                        sx={{
                          position: 'absolute',
                          left: -16,
                          top: 4,
                          width: 14,
                          height: 14,
                          borderRadius: '50%',
                          display: 'grid',
                          placeItems: 'center',
                          bgcolor: isCurrent ? 'rgba(217,119,87,0.12)' : 'rgba(255,253,248,0.95)',
                          color: isError ? 'error.main' : isCurrent ? 'secondary.main' : 'rgba(111,106,97,0.9)',
                          border: '1px solid rgba(176, 174, 165, 0.2)',
                          boxShadow: isCurrent ? '0 0 0 6px rgba(217,119,87,0.08)' : 'none',
                        }}
                      >
                        {isDone ? (
                          <CheckCircleRoundedIcon sx={{ fontSize: 12 }} />
                        ) : (
                          <MoreHorizRoundedIcon
                            sx={{
                              fontSize: 12,
                              '@keyframes thinkingDotShift': {
                                '0%': { opacity: 0.55, transform: 'translateX(-1px)' },
                                '100%': { opacity: 1, transform: 'translateX(1px)' },
                              },
                              animation: isCurrent ? 'thinkingDotShift 0.7s ease-in-out infinite alternate' : 'none',
                            }}
                          />
                        )}
                      </Box>

                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.3, flexWrap: 'wrap' }}>
                        <Typography
                          variant="caption"
                          sx={{
                            fontWeight: 700,
                            color: isError ? 'error.main' : isCurrent ? 'secondary.main' : 'text.secondary',
                            letterSpacing: '0.08em',
                          }}
                        >
                          {step.label}
                        </Typography>
                        {isCurrent ? (
                          <Chip
                            size="small"
                            label="处理中"
                            sx={{
                              height: 20,
                              bgcolor: 'rgba(217,119,87,0.1)',
                              color: 'secondary.main',
                              border: '1px solid rgba(217,119,87,0.16)',
                            }}
                          />
                        ) : isError ? (
                          <Chip
                            size="small"
                            label="失败"
                            sx={{
                              height: 20,
                              bgcolor: 'rgba(211, 47, 47, 0.1)',
                              color: 'error.main',
                              border: '1px solid rgba(211, 47, 47, 0.2)',
                            }}
                          />
                        ) : null}
                      </Stack>

                      <Typography
                        variant="body2"
                        sx={{
                          color: isError ? 'error.main' : isCurrent ? 'text.primary' : 'text.secondary',
                          lineHeight: 1.7,
                        }}
                      >
                        {stepDetail}
                      </Typography>
                      {step.previewItems?.length ? (
                        <Stack direction="row" spacing={0.75} sx={{ mt: 0.9, flexWrap: 'wrap' }}>
                          {step.previewItems.map((item) => (
                            <Chip
                              key={`${step.key}-${item}`}
                              size="small"
                              label={item}
                              variant="outlined"
                              sx={{
                                height: 24,
                                mb: 0.6,
                                borderColor: 'rgba(217,119,87,0.18)',
                                bgcolor: 'rgba(255,253,248,0.72)',
                                color: 'text.secondary',
                              }}
                            />
                          ))}
                          {previewOverflow > 0 ? (
                            <Chip
                              size="small"
                              label={`+${previewOverflow} 条证据`}
                              sx={{
                                height: 24,
                                mb: 0.6,
                                bgcolor: 'rgba(232, 230, 220, 0.8)',
                                color: 'text.secondary',
                              }}
                            />
                          ) : null}
                        </Stack>
                      ) : null}
                    </Box>
                  )
                })}
              </Stack>
            </Box>
          </Stack>
        </Collapse>
      </Stack>
    </Paper>
  )
}

function AssistantContent({ content, references }: { content: string; references: ChatReference[] }) {
  const shouldUseSentenceMode = references.length > 0 && !looksLikeMarkdown(content)

  if (!shouldUseSentenceMode) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <MarkdownContent content={content} />
        </Box>
        {references.length ? <CitationInline references={references} /> : null}
      </Box>
    )
  }

  const sentences = splitIntoSentences(content)
  const sentenceReferenceMap = buildSentenceReferenceMap(sentences, references)

  return (
    <Stack spacing={1}>
      {sentences.map((sentence, index) => {
        const sentenceReferences = sentenceReferenceMap.get(index) ?? []

        return (
          <Typography key={`${sentence}-${index}`} sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
            {sentence}
            {sentenceReferences.length ? <CitationInline references={sentenceReferences} /> : null}
          </Typography>
        )
      })}
    </Stack>
  )
}

export function ChatMessageList({
  messages,
}: {
  messages: ChatMessage[]
}) {
  return (
    <Stack spacing={2}>
      {messages.map((message) => (
        <Paper
          key={message.id}
          sx={{
            px: 2.25,
            py: message.role === 'user' ? 1.4 : 2.25,
            maxWidth: '80%',
            alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
            bgcolor: message.role === 'user' ? 'primary.main' : 'background.paper',
            color: message.role === 'user' ? 'primary.contrastText' : 'text.primary',
            borderRadius: 0.9,
            border: message.role === 'user' ? '1px solid rgba(20, 20, 19, 0.08)' : '1px solid rgba(176, 174, 165, 0.22)',
            boxShadow: message.role === 'user' ? '0 12px 24px rgba(20, 20, 19, 0.1)' : '0 16px 34px rgba(20, 20, 19, 0.05)',
            background: message.role === 'user' ? undefined : 'linear-gradient(180deg, #fffdf8 0%, #f7f4eb 100%)',
          }}
        >
          {message.role === 'user' ? (
            <Typography sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.35 }}>{message.content}</Typography>
          ) : (
            <>
              <Typography variant="caption" sx={{ opacity: 0.8 }}>
                AI
              </Typography>
              {(message.isStreaming || message.timeline?.length || message.agentTrace) ? (
                <ThinkingSummaryPanel
                  timelineEvents={message.timeline ?? []}
                  trace={message.agentTrace ?? null}
                  active={Boolean(message.isStreaming)}
                />
              ) : null}
              <AssistantContent content={message.content} references={message.references ?? []} />
              {message.references?.length ? <CitationList references={message.references} /> : null}
              {message.isStreaming ? (
                <Box component="span" sx={{ color: 'text.secondary' }}>
                  ▋
                </Box>
              ) : null}
            </>
          )}
        </Paper>
      ))}
    </Stack>
  )
}
