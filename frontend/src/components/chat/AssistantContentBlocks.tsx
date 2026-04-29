import { Box } from '@mui/material'

import { ChatContentBlock } from '../../types/chat'
import { MarkdownContent } from './MarkdownContent'
import { ToolCallBlock } from './ToolCallBlock'

export function AssistantContentBlocks({
  blocks,
}: {
  blocks: ChatContentBlock[]
}) {
  const orderedBlocks = [...blocks].sort((a, b) => {
    if (a.order !== b.order) return a.order - b.order
    const aKey = 'id' in a ? a.id : ''
    const bKey = 'id' in b ? b.id : ''
    return `${a.type}:${aKey}`.localeCompare(`${b.type}:${bKey}`)
  })

  const toolResults = new Map(
    orderedBlocks
      .filter((block) => block.type === 'tool_result')
      .map((block) => [block.tool_use_id, block])
  )

  return (
    <Box>
      {orderedBlocks.map((block) => {
        if (block.type === 'markdown') {
          return <MarkdownContent key={block.id} content={block.text} />
        }

        if (block.type === 'tool_use') {
          return <ToolCallBlock key={block.id} toolUse={block} toolResult={toolResults.get(block.id)} />
        }

        if (orderedBlocks.some((candidate) => candidate.type === 'tool_use' && candidate.id === block.tool_use_id)) {
          return null
        }

        return (
          <ToolCallBlock
            key={block.id}
            toolUse={{
              type: 'tool_use',
              id: block.tool_use_id,
              name: 'unknown_tool',
              input: {},
              title: '工具调用',
              order: Math.max(0, block.order - 1),
            }}
            toolResult={block}
          />
        )
      })}
    </Box>
  )
}
