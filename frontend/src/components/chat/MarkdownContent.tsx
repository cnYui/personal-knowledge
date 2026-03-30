import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Box } from '@mui/material'

interface MarkdownContentProps {
  content: string
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <Box
      sx={{
        '& p': {
          margin: '0.5em 0',
          '&:first-of-type': { marginTop: 0 },
          '&:last-of-type': { marginBottom: 0 },
        },
        '& ul, & ol': {
          margin: '0.5em 0',
          paddingLeft: '1.5em',
        },
        '& li': {
          margin: '0.25em 0',
        },
        '& code': {
          backgroundColor: 'rgba(0, 0, 0, 0.05)',
          padding: '0.2em 0.4em',
          borderRadius: '3px',
          fontSize: '0.9em',
          fontFamily: 'monospace',
        },
        '& pre': {
          backgroundColor: 'rgba(0, 0, 0, 0.05)',
          padding: '1em',
          borderRadius: '6px',
          overflow: 'auto',
          margin: '0.5em 0',
        },
        '& pre code': {
          backgroundColor: 'transparent',
          padding: 0,
        },
        '& blockquote': {
          borderLeft: '4px solid rgba(0, 0, 0, 0.1)',
          paddingLeft: '1em',
          margin: '0.5em 0',
          color: 'rgba(0, 0, 0, 0.6)',
        },
        '& h1, & h2, & h3, & h4, & h5, & h6': {
          margin: '1em 0 0.5em 0',
          fontWeight: 600,
          '&:first-of-type': { marginTop: 0 },
        },
        '& h1': { fontSize: '1.5em' },
        '& h2': { fontSize: '1.3em' },
        '& h3': { fontSize: '1.1em' },
        '& strong': {
          fontWeight: 600,
        },
        '& a': {
          color: 'primary.main',
          textDecoration: 'none',
          '&:hover': {
            textDecoration: 'underline',
          },
        },
        '& table': {
          borderCollapse: 'collapse',
          width: '100%',
          margin: '0.5em 0',
        },
        '& th, & td': {
          border: '1px solid rgba(0, 0, 0, 0.1)',
          padding: '0.5em',
          textAlign: 'left',
        },
        '& th': {
          backgroundColor: 'rgba(0, 0, 0, 0.05)',
          fontWeight: 600,
        },
        '& hr': {
          border: 'none',
          borderTop: '1px solid rgba(0, 0, 0, 0.1)',
          margin: '1em 0',
        },
      }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </Box>
  )
}
