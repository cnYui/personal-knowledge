import { Box, Chip, Paper, Stack, Tooltip, Typography } from '@mui/material'
import { useMemo } from 'react'

import { ChatMessage, ChatReference } from '../../types/chat'
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
            <Typography variant="caption" sx={{ opacity: 0.6, ml: 0.5 }}>
              AI
            </Typography>
            <ThinkingProcess
              timelineEvents={message.timeline ?? []}
              trace={message.agentTrace ?? null}
              active={Boolean(message.isStreaming)}
            />
            <AssistantContent content={message.content} references={message.references ?? []} />
            {message.references?.length ? <CitationList references={message.references} /> : null}
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
