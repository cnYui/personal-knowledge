import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { Accordion, AccordionDetails, AccordionSummary, Box, Chip, Paper, Stack, Tooltip, Typography } from '@mui/material'

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
    <Stack spacing={0.5} sx={{ mt: 1.5 }}>
      {references.map((reference, index) => (
        <Typography key={`${reference.type}-${index}`} variant="caption" color="text.secondary" sx={{ display: 'block' }}>
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
              color: 'primary.main',
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
  const plannerStep = trace.steps.find((step) => step.step_type === 'planner')

  return (
    <Accordion
      disableGutters
      elevation={0}
      sx={{
        mt: 1.5,
        backgroundColor: 'transparent',
        border: '1px solid rgba(0,0,0,0.08)',
        borderRadius: 2,
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
          <Chip size="small" label={`模式: ${trace.mode === 'chitchat' ? '闲聊' : '图谱检索'}`} />
          <Chip size="small" label={`检索轮次: ${trace.retrieval_rounds}`} />
          <Chip size="small" label={`最终动作: ${trace.final_action || 'unknown'}`} />
          {plannerStep?.action ? (
            <Chip
              size="small"
              variant="outlined"
              label={`规划器: ${plannerStep.action}${plannerStep.rewritten_query ? ` -> ${plannerStep.rewritten_query}` : ''}`}
            />
          ) : null}
        </Stack>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 1.5, pt: 0.5, pb: 1.5 }}>
        <Stack spacing={1.25}>
          {trace.steps.map((step, index) => (
            <Box
              key={`${step.step_type}-${index}`}
              sx={{
                borderRadius: 2,
                backgroundColor: 'rgba(0,0,0,0.03)',
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
        </Stack>
      </AccordionDetails>
    </Accordion>
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
  loading,
  streamingContent,
  streamingReferences = [],
  streamingAgentTrace = null,
}: {
  messages: ChatMessage[]
  loading: boolean
  streamingContent?: string
  streamingReferences?: ChatReference[]
  streamingAgentTrace?: AgentTrace | null
}) {
  return (
    <Stack spacing={2}>
      {messages.map((message) => (
        <Paper
          key={message.id}
          sx={{
            p: 2,
            maxWidth: '80%',
            alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
            bgcolor: message.role === 'user' ? 'primary.main' : '#fff',
            color: message.role === 'user' ? '#fff' : 'text.primary',
            borderRadius: 3,
          }}
        >
          <Typography variant="caption" sx={{ opacity: 0.8 }}>
            {message.role === 'user' ? '你' : 'AI'}
          </Typography>
          {message.role === 'user' ? (
            <Typography sx={{ whiteSpace: 'pre-wrap' }}>{message.content}</Typography>
          ) : (
            <>
              <AssistantContent content={message.content} references={message.references ?? []} />
              {message.references?.length ? <CitationList references={message.references} /> : null}
              {message.agentTrace ? <AgentTraceSummary trace={message.agentTrace} /> : null}
            </>
          )}
        </Paper>
      ))}
      {loading && streamingContent && (
        <Paper
          sx={{
            p: 2,
            maxWidth: '80%',
            alignSelf: 'flex-start',
            bgcolor: '#fff',
            color: 'text.primary',
            borderRadius: 3,
          }}
        >
          <Typography variant="caption" sx={{ opacity: 0.8 }}>
            AI
          </Typography>
          <AssistantContent content={streamingContent} references={streamingReferences} />
          {streamingReferences.length ? <CitationList references={streamingReferences} /> : null}
          {streamingAgentTrace ? <AgentTraceSummary trace={streamingAgentTrace} /> : null}
          <Box component="span" sx={{ color: 'text.secondary' }}>
            ▋
          </Box>
        </Paper>
      )}
      {loading && !streamingContent && <Typography color="text.secondary">AI 正在思考...</Typography>}
    </Stack>
  )
}
