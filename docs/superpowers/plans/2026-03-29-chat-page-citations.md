# Chat Page Citations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the `/chat` page so the title copy is removed, the top bar and side navigation remain fixed while browsing long conversations, and assistant messages persist and render interactive citation references.

**Architecture:** Keep the existing React + MUI structure, but move the app shell to a fixed-height layout with the chat page owning the scrollable transcript region. Extend the chat message model to persist `references` in local storage during streaming, then render assistant answers with inline citation chips, a compact sources block, and hover tooltips.

**Tech Stack:** React, TypeScript, Material UI, React Router, TanStack Query, browser `localStorage`

---

## File Structure

### Existing files to modify

- `frontend/src/components/layout/AppLayout.tsx`
  - Own the viewport-sized app shell and stop page-level scrolling.
- `frontend/src/components/layout/TopBar.tsx`
  - Make the top header sticky with a stable height and background.
- `frontend/src/components/layout/SideNav.tsx`
  - Keep the side navigation fixed-height and visually stable while content scrolls.
- `frontend/src/pages/KnowledgeChatPage.tsx`
  - Replace the page header with a lighter chat control bar and create the 3-region layout.
- `frontend/src/components/chat/ChatMessageList.tsx`
  - Render assistant citations inline, show compact source entries, and support hover tooltips.
- `frontend/src/types/chat.ts`
  - Extend `ChatMessage` with optional `references`.
- `frontend/src/services/chatApi.ts`
  - Persist assistant `references` while streaming and keep storage backward compatible.
- `frontend/src/hooks/useChat.ts`
  - Preserve streaming references so the current in-flight assistant message can render citations.

### Verification targets

- `frontend/src/pages/KnowledgeChatPage.tsx`
- `frontend/src/components/chat/ChatMessageList.tsx`
- `frontend/src/services/chatApi.ts`

### Task 1: Persist references in chat message data

**Files:**
- Modify: `frontend/src/types/chat.ts`
- Modify: `frontend/src/services/chatApi.ts`
- Modify: `frontend/src/hooks/useChat.ts`

- [ ] **Step 1: Extend the chat message type to hold references**

```ts
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at?: string | null
  references?: ChatReference[]
}
```

- [ ] **Step 2: Update the streaming assistant placeholder to carry references**

```ts
const assistantMessage: ChatMessage = {
  id: assistantId,
  role: 'assistant',
  content: '',
  created_at: new Date().toISOString(),
  references: [],
}
```

- [ ] **Step 3: Persist references when the stream emits them**

```ts
if (data.type === 'references') {
  const references = Array.isArray(data.content) ? data.content : []
  onReferences(references)

  const currentMessages = loadMessagesFromStorage()
  const msgIndex = currentMessages.findIndex((m) => m.id === assistantId)
  if (msgIndex !== -1) {
    currentMessages[msgIndex].references = references
    saveMessagesToStorage(currentMessages)
  }
}
```

- [ ] **Step 4: Keep the hook-level streaming state aligned with the same reference payload**

```ts
const [references, setReferences] = useState<ChatReference[]>([])

(refs) => {
  setReferences(refs)
}
```

- [ ] **Step 5: Clear temporary streaming state on success and error without losing persisted history**

```ts
() => {
  setIsStreaming(false)
  setStreamingContent('')
  setReferences([])
  queryClient.invalidateQueries({ queryKey: ['chat-messages'] })
  resolve()
}
```

```ts
(error) => {
  setIsStreaming(false)
  setStreamingContent('')
  setReferences([])
  queryClient.invalidateQueries({ queryKey: ['chat-messages'] })
  reject(new Error(error))
}
```

### Task 2: Lock the app shell and chat page layout

**Files:**
- Modify: `frontend/src/components/layout/AppLayout.tsx`
- Modify: `frontend/src/components/layout/TopBar.tsx`
- Modify: `frontend/src/components/layout/SideNav.tsx`
- Modify: `frontend/src/pages/KnowledgeChatPage.tsx`

- [ ] **Step 1: Change the app shell to a fixed-height layout**

```tsx
<Box sx={{ display: 'flex', height: '100vh', bgcolor: 'background.default', overflow: 'hidden' }}>
  <SideNav />
  <Box sx={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
    <TopBar />
    <Box component="main" sx={{ flex: 1, minHeight: 0, p: 3, overflow: 'hidden' }}>
      <Outlet />
    </Box>
  </Box>
</Box>
```

- [ ] **Step 2: Make the top bar sticky and visually solid**

```tsx
<AppBar
  position="sticky"
  color="transparent"
  elevation={0}
  sx={{
    top: 0,
    zIndex: (theme) => theme.zIndex.drawer + 1,
    borderBottom: '1px solid #e5e7eb',
    bgcolor: 'rgba(255,255,255,0.96)',
    backdropFilter: 'blur(10px)',
  }}
>
```

- [ ] **Step 3: Make the side navigation fill the viewport and not move with the transcript**

```tsx
<Box
  sx={{
    width: 240,
    height: '100vh',
    flexShrink: 0,
    overflowY: 'auto',
    bgcolor: '#111827',
    color: '#fff',
    px: 2,
    py: 3,
  }}
>
```

- [ ] **Step 4: Replace the chat page header with a compact control bar and a scrollable transcript panel**

```tsx
<Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
  <Stack direction="row" alignItems="center" justifyContent="space-between">
    <Box>
      <Typography variant="h5" fontWeight={700}>聊天</Typography>
    </Box>
    <Button variant="outlined" onClick={() => clearMutation.mutate()} disabled={clearMutation.isPending}>
      清空对话
    </Button>
  </Stack>

  <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
    ...messages or empty state...
  </Box>

  <Box sx={{ flexShrink: 0 }}>
    <ChatInput ... />
  </Box>
</Box>
```

- [ ] **Step 5: Remove the old title/description copy**

```tsx
// Remove PageHeader usage entirely from KnowledgeChatPage.tsx
```

### Task 3: Render inline citations and hoverable sources

**Files:**
- Modify: `frontend/src/components/chat/ChatMessageList.tsx`
- Modify: `frontend/src/pages/KnowledgeChatPage.tsx`

- [ ] **Step 1: Pass streaming references into the message list**

```tsx
<ChatMessageList
  messages={data}
  loading={sendMutation.isPending}
  streamingContent={sendMutation.streamingContent}
  streamingReferences={sendMutation.references}
/>
```

- [ ] **Step 2: Add a source text helper with stable fallback priority**

```ts
function getReferenceText(reference: ChatReference): string {
  return reference.fact || reference.summary || reference.name || reference.type
}
```

- [ ] **Step 3: Render assistant text with inline citation triggers**

```tsx
function CitationInline({ references }: { references: ChatReference[] }) {
  return (
    <Box component="span" sx={{ ml: 0.75 }}>
      {references.map((reference, index) => (
        <Tooltip key={`${reference.type}-${index}`} title={getReferenceText(reference)} arrow>
          <Box component="sup" sx={{ mx: 0.25, color: 'primary.main', cursor: 'help', fontWeight: 700 }}>
            [{index + 1}]
          </Box>
        </Tooltip>
      ))}
    </Box>
  )
}
```

- [ ] **Step 4: Attach the inline citations after assistant markdown content and add a compact sources block below**

```tsx
<MarkdownContent content={message.content} />
{message.references?.length ? <CitationInline references={message.references} /> : null}
{message.references?.length ? (
  <Stack spacing={0.5} sx={{ mt: 1.5 }}>
    {message.references.map((reference, index) => (
      <Typography key={`${reference.type}-${index}`} variant="caption" color="text.secondary">
        [{index + 1}] {getReferenceText(reference)}
      </Typography>
    ))}
  </Stack>
) : null}
```

- [ ] **Step 5: Mirror the same rendering path for the in-flight streaming assistant message**

```tsx
{loading && streamingContent && (
  <Paper ...>
    <MarkdownContent content={streamingContent} />
    {streamingReferences.length ? <CitationInline references={streamingReferences} /> : null}
    ...sources block...
  </Paper>
)}
```

### Task 4: Verify the chat page behavior

**Files:**
- Verify: `frontend/src/components/layout/AppLayout.tsx`
- Verify: `frontend/src/pages/KnowledgeChatPage.tsx`
- Verify: `frontend/src/components/chat/ChatMessageList.tsx`
- Verify: `frontend/src/services/chatApi.ts`

- [ ] **Step 1: Review the final UI against the spec acceptance criteria**

Check manually:

```text
- /chat no longer shows the old title and subtitle copy
- top bar stays visible while transcript scrolls
- side navigation stays fixed while transcript scrolls
- assistant responses show numbered references when present
- hover on [1]/[2]/[3] shows source text
- source list renders under the assistant response in smaller text
```

- [ ] **Step 2: Run frontend lint or typecheck if available**

Run:

```bash
npm run build
```

Expected:

```text
Vite production build succeeds with no TypeScript errors caused by the changes.
```

- [ ] **Step 3: Smoke test persistence behavior**

Check manually:

```text
1. Send a chat message that returns references.
2. Confirm inline [1]/[2] markers render.
3. Refresh the page.
4. Confirm the same assistant message still shows its sources.
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/AppLayout.tsx frontend/src/components/layout/TopBar.tsx frontend/src/components/layout/SideNav.tsx frontend/src/pages/KnowledgeChatPage.tsx frontend/src/components/chat/ChatMessageList.tsx frontend/src/types/chat.ts frontend/src/services/chatApi.ts frontend/src/hooks/useChat.ts docs/superpowers/specs/2026-03-29-chat-page-citations-design.md docs/superpowers/plans/2026-03-29-chat-page-citations.md
git commit -m "rewrite chat page layout and citations"
```

## Self-review

- Spec coverage: layout shell, chat page copy removal, citation persistence, inline source rendering, hover display, and refresh persistence are all covered by Tasks 1-4.
- Placeholder scan: no `TODO`, `TBD`, or unresolved placeholders remain.
- Type consistency: the plan consistently uses `references`, `streamingReferences`, and `ChatReference` across data, UI, and verification steps.
