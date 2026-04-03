import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import MoreHorizRoundedIcon from '@mui/icons-material/MoreHorizRounded'
import { Accordion, AccordionDetails, AccordionSummary, Box, Chip, Collapse, Paper, Stack, Tooltip, Typography } from '@mui/material'
import { useMemo, useState } from 'react'

import { AgentTrace, ChatMessage, ChatReference } from '../../types/chat'
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

function AgentTraceSummary({ trace }: { trace: AgentTrace }) {
  const canvasEvents = trace.canvas?.events ?? []
  const toolSteps = trace.tool_loop?.tool_steps ?? []
  const citationItems = trace.citation?.items ?? []
  const directAnswer = trace.final_action === 'direct_general_answer'
  const summaryModeLabel = directAnswer ? '直接回答' : '图谱检索'

  return (
    <Accordion
      disableGutters
      elevation={0}
      sx={{
        mt: 1.5,
        backgroundColor: 'rgba(247, 245, 238, 0.85)',
        border: '1px solid rgba(176, 174, 165, 0.2)',
        borderRadius: 3,
        '&:before': { display: 'none' },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          px: 1.5,
          minHeight: 44,
          '& .MuiAccordionSummary-content': {
            my: 0.5,
          },
        }}
      >
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
          <Chip size="small" label={`模式: ${summaryModeLabel}`} />
          <Chip size="small" label={`检索轮次: ${trace.retrieval_rounds}`} />
          <Chip size="small" label={`最终动作: ${trace.final_action || 'unknown'}`} />
        </Stack>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 1.5, pt: 0.5, pb: 1.5 }}>
        <Stack spacing={1.25}>
          {trace.canvas ? (
            <Box
              sx={{
                borderRadius: 2.5,
                backgroundColor: 'rgba(255,253,248,0.86)',
                border: '1px solid rgba(176, 174, 165, 0.18)',
                px: 1.25,
                py: 1,
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', mb: 0.75 }}>
                Canvas
              </Typography>
              <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', mb: 0.75 }}>
                <Chip size="small" variant="outlined" label={`路径: ${trace.canvas.execution_path.join(' -> ') || '无'}`} />
                {trace.reference_store ? (
                  <>
                    <Chip size="small" label={`图谱证据: ${trace.reference_store.graph_evidence_count}`} />
                    <Chip size="small" label={`Chunks: ${trace.reference_store.chunk_count}`} />
                    <Chip size="small" label={`文档: ${trace.reference_store.doc_count}`} />
                  </>
                ) : null}
              </Stack>
              {canvasEvents.length ? (
                <Stack spacing={0.5}>
                  {canvasEvents.map((event, index) => (
                    <Typography key={`${event.event}-${event.node_id}-${index}`} variant="body2" color="text.secondary">
                      {event.event} · {event.node_id}
                      {event.node_type ? ` (${event.node_type})` : ''}
                    </Typography>
                  ))}
                </Stack>
              ) : null}
            </Box>
          ) : null}

          {trace.steps.map((step, index) => (
            <Box
              key={`${step.step_type}-${index}`}
              sx={{
                borderRadius: 2.5,
                backgroundColor: 'rgba(255,253,248,0.86)',
                border: '1px solid rgba(176, 174, 165, 0.18)',
                px: 1.25,
                py: 1,
              }}
            >
              <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: 'wrap', mb: 0.5 }}>
                <Typography variant="caption" sx={{ fontWeight: 700 }}>
                  Step {index + 1}
                </Typography>
                <Chip size="small" variant="outlined" label={step.step_type} />
                {step.action ? <Chip size="small" label={`动作: ${step.action}`} /> : null}
                {typeof step.retrieved_edge_count === 'number' ? (
                  <Chip size="small" label={`命中边: ${step.retrieved_edge_count}`} />
                ) : null}
                {typeof step.evidence_found === 'boolean' ? (
                  <Chip size="small" label={`证据: ${step.evidence_found ? '有' : '无'}`} />
                ) : null}
              </Stack>
              {step.query ? (
                <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
                  检索问题: {step.query}
                </Typography>
              ) : null}
              {step.rewritten_query ? (
                <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
                  改写问题: {step.rewritten_query}
                </Typography>
              ) : null}
              {step.message ? (
                <Typography variant="body2" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>
                  {step.message}
                </Typography>
              ) : null}
            </Box>
          ))}

          {trace.tool_loop ? (
            <Box
              sx={{
                borderRadius: 2.5,
                backgroundColor: 'rgba(255,253,248,0.86)',
                border: '1px solid rgba(176, 174, 165, 0.18)',
                px: 1.25,
                py: 1,
              }}
            >
              <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: 'wrap', mb: toolSteps.length ? 0.75 : 0 }}>
                <Typography variant="caption" sx={{ fontWeight: 700 }}>
                  Tool Loop
                </Typography>
                <Chip size="small" label={`轮次超限: ${trace.tool_loop.tool_rounds_exceeded ? '是' : '否'}`} />
              </Stack>
              {toolSteps.length ? (
                <Stack spacing={0.75}>
                  {toolSteps.map((step, index) => (
                    <Box
                      key={`${step.tool_name}-${step.round_index}-${index}`}
                      sx={{ borderRadius: 2, bgcolor: 'rgba(250,249,245,0.92)', px: 1, py: 0.75 }}
                    >
                      <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', mb: 0.5 }}>
                        <Chip size="small" variant="outlined" label={`Round ${step.round_index + 1}`} />
                        <Chip size="small" label={step.tool_name} />
                        {typeof step.result_summary?.retrieved_edge_count === 'number' ? (
                          <Chip size="small" label={`命中边: ${step.result_summary.retrieved_edge_count}`} />
                        ) : null}
                        {typeof step.result_summary?.has_enough_evidence === 'boolean' ? (
                          <Chip size="small" label={`证据: ${step.result_summary.has_enough_evidence ? '有' : '无'}`} />
                        ) : null}
                      </Stack>
                      <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
                        参数: {JSON.stringify(step.arguments, null, 2)}
                      </Typography>
                      {step.result_summary?.empty_reason ? (
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>
                          空结果原因: {step.result_summary.empty_reason}
                        </Typography>
                      ) : null}
                      {step.error ? (
                        <Typography variant="body2" color="error.main" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>
                          错误: {step.error}
                        </Typography>
                      ) : null}
                    </Box>
                  ))}
                </Stack>
              ) : null}
            </Box>
          ) : null}

          {trace.citation ? (
            <Box
              sx={{
                borderRadius: 2.5,
                backgroundColor: 'rgba(255,253,248,0.86)',
                border: '1px solid rgba(176, 174, 165, 0.18)',
                px: 1.25,
                py: 1,
              }}
            >
              <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', mb: citationItems.length ? 0.75 : 0 }}>
                <Typography variant="caption" sx={{ fontWeight: 700 }}>
                  Citation
                </Typography>
                <Chip size="small" label={`引用数: ${trace.citation.count}`} />
                <Chip size="small" label={`通用补充: ${trace.citation.used_general_fallback ? '是' : '否'}`} />
              </Stack>
              {citationItems.length ? (
                <Stack spacing={0.5}>
                  {citationItems.map((item) => (
                    <Typography key={`${item.type}-${item.index}`} variant="body2" color="text.secondary">
                      [{item.index}] {item.label}
                    </Typography>
                  ))}
                </Stack>
              ) : null}
            </Box>
          ) : null}
        </Stack>
      </AccordionDetails>
    </Accordion>
  )
}

type ThinkingTimelineItem = {
  key: string
  label: string
  detail: string
  status: 'done' | 'current'
}

function buildThinkingTimeline(trace: AgentTrace | null, steps: string[]) {
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

  if (steps.length) {
    return steps.map<ThinkingTimelineItem>((step, index) => ({
      key: `step-${index}`,
      label: index === steps.length - 1 ? '当前步骤' : `步骤 ${String(index + 1).padStart(2, '0')}`,
      detail: step,
      status: index === steps.length - 1 ? ('current' as const) : ('done' as const),
    }))
  }

  return [
    {
      key: 'workflow',
      label: '创建工作流',
      detail: '已创建工作流，正在整理问题与上下文。',
      status: 'done' as const,
    },
    {
      key: 'agent',
      label: 'Agent 接管会话',
      detail: 'Agent 正在决定是否调用知识检索工具。',
      status: 'done' as const,
    },
    {
      key: 'answer',
      label: '组织最终回答',
      detail: '正在汇总证据并准备组织最终回答。',
      status: 'current' as const,
    },
  ]
}

function ThinkingSummaryPanel({
  steps,
  trace,
  active = false,
}: {
  steps: string[]
  trace: AgentTrace | null
  active?: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const timeline = useMemo(() => buildThinkingTimeline(trace, steps), [trace, steps])
  const currentStep = timeline[timeline.length - 1]
  const doneCount = Math.max(timeline.filter((step) => step.status === 'done').length, 0)
  const currentRound = trace?.tool_loop?.tool_steps?.length ?? 0
  const statusLabel = useMemo(() => {
    if (currentRound > 0) {
      return `检索第 ${currentRound} 轮`
    }
    if (/回答|整理/.test(currentStep.detail)) return '组织回答'
    if (/决定|接管|工作流|上下文/.test(currentStep.detail)) return '推理中'
    return '思考中'
  }, [currentRound, currentStep])

  return (
    <Paper
      sx={{
        px: 1.5,
        py: 1.15,
        maxWidth: '80%',
        alignSelf: 'flex-start',
        minWidth: { xs: '100%', md: 560 },
        borderRadius: 4,
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
                {currentStep.detail}
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
              <Typography variant="caption" sx={{ color: 'text.disabled', letterSpacing: '0.12em' }}>
                THINKING CHAIN
              </Typography>
              <Chip
                size="small"
                variant="outlined"
                label={currentRound > 0 ? `已执行 ${currentRound} 轮检索` : `阶段 ${timeline.length}`}
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
                  borderRadius: 999,
                  background: 'linear-gradient(180deg, rgba(176,174,165,0.4) 0%, rgba(176,174,165,0.12) 100%)',
                },
              }}
            >
              <Stack spacing={1.2}>
                {timeline.map((step, index) => {
                  const isCurrent = step.status === 'current'
                  const isDone = step.status === 'done'

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
                          color: isCurrent ? 'secondary.main' : 'rgba(111,106,97,0.9)',
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
                            color: isCurrent ? 'secondary.main' : 'text.secondary',
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
                        ) : null}
                      </Stack>

                      <Typography
                        variant="body2"
                        sx={{
                          color: isCurrent ? 'text.primary' : 'text.secondary',
                          lineHeight: 1.7,
                        }}
                      >
                        {step.detail}
                      </Typography>
                    </Box>
                  )
                })}
              </Stack>
            </Box>

            <Typography variant="caption" sx={{ color: 'text.disabled', pl: 0.5 }}>
              已完成 {doneCount} 个步骤，系统会继续更新当前阶段并在回答结束后保留完整轨迹。
            </Typography>
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
            p: 2.25,
            maxWidth: '80%',
            alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
            bgcolor: message.role === 'user' ? 'primary.main' : 'background.paper',
            color: message.role === 'user' ? 'primary.contrastText' : 'text.primary',
            borderRadius: 4,
            border: message.role === 'user' ? '1px solid rgba(20, 20, 19, 0.08)' : '1px solid rgba(176, 174, 165, 0.22)',
            boxShadow: message.role === 'user' ? '0 12px 24px rgba(20, 20, 19, 0.1)' : '0 16px 34px rgba(20, 20, 19, 0.05)',
            background: message.role === 'user' ? undefined : 'linear-gradient(180deg, #fffdf8 0%, #f7f4eb 100%)',
          }}
        >
          <Typography variant="caption" sx={{ opacity: 0.8 }}>
            {message.role === 'user' ? '你' : 'AI'}
          </Typography>
          {message.role === 'user' ? (
            <Typography sx={{ whiteSpace: 'pre-wrap' }}>{message.content}</Typography>
          ) : (
            <>
              {(message.thinkingSteps?.length || message.agentTrace) ? (
                <ThinkingSummaryPanel
                  steps={message.thinkingSteps ?? []}
                  trace={message.agentTrace ?? null}
                  active={Boolean(message.isStreaming)}
                />
              ) : null}
              <AssistantContent content={message.content} references={message.references ?? []} />
              {message.references?.length ? <CitationList references={message.references} /> : null}
              {message.agentTrace ? <AgentTraceSummary trace={message.agentTrace} /> : null}
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
