import { Box, Paper, Stack, Tooltip, Typography } from '@mui/material'

import { ChatMessage, ChatReference, SentenceCitation } from '../../types/chat'
import { MarkdownContent } from './MarkdownContent'
import { ThinkingProcess } from './ThinkingProcess'

function getReferenceText(reference: ChatReference) {
  return reference.fact || reference.summary || reference.name || reference.type
}

function looksLikeMarkdown(content: string) {
  return /(^|\n)\s*(?:[-*#>`]|\d+\.)|\*\*[^*]+\*\*|__[^_]+__|\[[^\]]+\]\([^)]+\)|```|\|/.test(content)
}

function collectInlineCitationIndexes(content: string) {
  const indexes = new Set<number>()
  for (const match of content.matchAll(/\[(\d+)\]/g)) {
    const value = Number(match[1])
    if (Number.isInteger(value) && value > 0) {
      indexes.add(value)
    }
  }
  return [...indexes].sort((a, b) => a - b)
}

function collectSentenceCitationIndexes(sentenceCitations?: SentenceCitation[]) {
  const indexes = new Set<number>()
  for (const item of sentenceCitations ?? []) {
    for (const citationIndex of item.citation_indexes ?? []) {
      if (Number.isInteger(citationIndex) && citationIndex > 0) {
        indexes.add(citationIndex)
      }
    }
  }
  return [...indexes].sort((a, b) => a - b)
}

function buildVisibleCitationItems({
  content,
  references,
  citationSection,
  sentenceCitations,
}: {
  content: string
  references: ChatReference[]
  citationSection?: string[]
  sentenceCitations?: SentenceCitation[]
}) {
  const indexes = new Set<number>([
    ...collectInlineCitationIndexes(content),
    ...collectSentenceCitationIndexes(sentenceCitations),
  ])

  return [...indexes]
    .sort((a, b) => a - b)
    .map((index) => {
      const label = citationSection?.[index - 1] ?? getReferenceText(references[index - 1])
      if (!label) {
        return null
      }
      return { index, label }
    })
    .filter((item): item is { index: number; label: string } => item !== null)
}

function splitIntoSentences(content: string) {
  return content
    .split(/(?<=[。！？!?])|\n+/)
    .map((part) => part.trim())
    .filter(Boolean)
}

function CitationList({ items }: { items: Array<{ index: number; label: string }> }) {
  if (!items.length) return null

  return (
    <Stack spacing={0.65} sx={{ mt: 1.75 }}>
      <Typography
        variant="caption"
        sx={{
          display: 'block',
          color: 'text.secondary',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          fontFamily: 'Poppins, Arial, sans-serif',
        }}
      >
        参考引用
      </Typography>
      {items.map((item) => (
        <Typography
          key={`${item.index}-${item.label}`}
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', fontFamily: 'Poppins, Arial, sans-serif' }}
        >
          [{item.index}] {item.label}
        </Typography>
      ))}
    </Stack>
  )
}

function CitationInline({ citationIndexes, references }: { citationIndexes: number[]; references: ChatReference[] }) {
  return (
    <Box component="span" sx={{ ml: 0.5, display: 'inline-flex', alignItems: 'center', flexWrap: 'wrap' }}>
      {citationIndexes.map((citationIndex) => {
        const reference = references[citationIndex - 1]
        if (!reference) return null
        return (
        <Tooltip key={`${citationIndex}-${reference.type}`} title={getReferenceText(reference)} arrow placement="top">
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
            [{citationIndex}]
          </Box>
        </Tooltip>
      )})}
    </Box>
  )
}

function renderSentenceWithCitationMarkers(sentence: string, citationIndexes: number[], references: ChatReference[]) {
  const trimmed = sentence.trim()
  if (!citationIndexes.length) {
    return <>{sentence}</>
  }

  const match = trimmed.match(/^(.*?)([。！？!?；;：:]*)$/)
  const body = match?.[1] ?? trimmed
  const punctuation = match?.[2] ?? ''
  return (
    <>
      {body}
      <CitationInline citationIndexes={citationIndexes} references={references} />
      {punctuation}
    </>
  )
}

function AssistantContent({
  content,
  references,
  sentenceCitations,
}: {
  content: string
  references: ChatReference[]
  sentenceCitations?: SentenceCitation[]
}) {
  const hasStructuredSentenceCitations = Boolean(sentenceCitations?.length)
  const shouldUseSentenceMode = !looksLikeMarkdown(content) && hasStructuredSentenceCitations

  if (!shouldUseSentenceMode) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <MarkdownContent content={content} />
        </Box>
      </Box>
    )
  }

  const sentences = splitIntoSentences(content)
  const sentenceCitationMap = new Map<number, number[]>()
  for (const item of sentenceCitations ?? []) {
    if (typeof item.sentence_index !== 'number' || !Array.isArray(item.citation_indexes)) {
      continue
    }
    sentenceCitationMap.set(item.sentence_index, item.citation_indexes)
  }

  return (
    <Stack spacing={1}>
      {sentences.map((sentence, index) => {
        const citationIndexes = sentenceCitationMap.get(index) ?? []

        return (
          <Typography key={`${sentence}-${index}`} sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
            {renderSentenceWithCitationMarkers(sentence, citationIndexes, references)}
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
        message.role === 'user' ? (
          <Paper
            key={message.id}
            sx={{
              px: 2.25,
              py: 1.4,
              maxWidth: '80%',
              alignSelf: 'flex-end',
              bgcolor: 'primary.main',
              color: 'primary.contrastText',
              borderRadius: 0.9,
              border: '1px solid rgba(20, 20, 19, 0.08)',
              boxShadow: '0 12px 24px rgba(20, 20, 19, 0.1)',
            }}
          >
            <Typography sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.35 }}>{message.content}</Typography>
          </Paper>
        ) : (
          <Box
            key={message.id}
            sx={{
              maxWidth: '80%',
              alignSelf: 'flex-start',
            }}
          >
            {(() => {
              const visibleCitationItems = buildVisibleCitationItems({
                content: message.content,
                references: message.references ?? [],
                citationSection: message.citationSection,
                sentenceCitations: message.sentenceCitations,
              })

              return (
                <>
            <ThinkingProcess
              timelineEvents={message.timeline ?? []}
              trace={message.agentTrace ?? null}
              active={Boolean(message.isStreaming)}
            />
            <AssistantContent
              content={message.content}
              references={message.references ?? []}
              sentenceCitations={message.sentenceCitations}
            />
            {visibleCitationItems.length ? (
              <CitationList items={visibleCitationItems} />
            ) : null}
            {message.isStreaming ? (
              <Box component="span" sx={{ color: 'text.secondary' }}>
                ▋
              </Box>
            ) : null}
                </>
              )
            })()}
          </Box>
        )
      ))}
    </Stack>
  )
}
