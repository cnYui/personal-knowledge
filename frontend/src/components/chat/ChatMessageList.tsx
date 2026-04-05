import { Box, Paper, Stack, Tooltip, Typography } from '@mui/material'

import { ChatMessage, ChatReference, SentenceCitation } from '../../types/chat'
import { MarkdownContent } from './MarkdownContent'
import { ThinkingProcess } from './ThinkingProcess'

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

function CitationList({ references, citationSection }: { references: ChatReference[]; citationSection?: string[] }) {
  const items = citationSection?.length ? citationSection : references.map((reference) => getReferenceText(reference))
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
      {items.map((item, index) => (
        <Typography
          key={`${item}-${index}`}
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', fontFamily: 'Poppins, Arial, sans-serif' }}
        >
          [{index + 1}] {item}
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
  const shouldUseSentenceMode =
    !looksLikeMarkdown(content) && (hasStructuredSentenceCitations || references.length > 0)

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
            {message.references?.length || message.citationSection?.length ? (
              <CitationList references={message.references ?? []} citationSection={message.citationSection} />
            ) : null}
            {message.isStreaming ? (
              <Box component="span" sx={{ color: 'text.secondary' }}>
                ▋
              </Box>
            ) : null}
          </Box>
        )
      ))}
    </Stack>
  )
}
