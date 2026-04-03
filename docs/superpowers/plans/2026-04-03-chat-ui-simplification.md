# Chat UI 简化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 简化聊天界面，去除AI消息的视觉包裹，优化思考过程展示为轻量级可折叠组件

**Architecture:** 重构ChatMessageList组件，创建新的ThinkingProcess轻量组件替代ThinkingSummaryPanel，移除AI消息的Paper包裹，保持用户消息样式不变

**Tech Stack:** React, TypeScript, Material-UI, React Hooks

---

## 文件结构

### 新建文件
- `frontend/src/components/chat/ThinkingProcess.tsx` - 新的轻量级思考过程组件

### 修改文件
- `frontend/src/components/chat/ChatMessageList.tsx` - 重构消息列表，移除AI消息Paper包裹，集成新组件

---

## Task 1: 创建ThinkingProcess组件基础结构

**Files:**
- Create: `frontend/src/components/chat/ThinkingProcess.tsx`

- [ ] **Step 1.1: 创建组件文件和基础类型定义**

```typescript
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

export function ThinkingProcess({ timelineEvents, trace, active = false }: ThinkingProcessProps) {
  return null
}
```

- [ ] **Step 1.2: 提交基础结构**

```bash
git add frontend/src/components/chat/ThinkingProcess.tsx
git commit -m "feat: create ThinkingProcess component skeleton"
```

---

## Task 2: 实现时间线构建逻辑

**Files:**
- Modify: `frontend/src/components/chat/ThinkingProcess.tsx`

- [ ] **Step 2.1: 添加buildThinkingTimelineFromEvents函数**

```typescript
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
```

- [ ] **Step 2.2: 添加buildThinkingTimeline主函数**

```typescript
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
```

- [ ] **Step 2.3: 提交时间线构建逻辑**

```bash
git add frontend/src/components/chat/ThinkingProcess.tsx
git commit -m "feat: add timeline building logic to ThinkingProcess"
```

---

## Task 3: 实现折叠状态UI

**Files:**
- Modify: `frontend/src/components/chat/ThinkingProcess.tsx`

- [ ] **Step 3.1: 添加状态管理和占位符动画**

在ThinkingProcess组件内添加：

```typescript
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

  return null // 临时返回，下一步实现UI
}
```

- [ ] **Step 3.2: 实现折叠状态UI**

替换return null为：

```typescript
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
```

- [ ] **Step 3.3: 提交折叠状态UI**

```bash
git add frontend/src/components/chat/ThinkingProcess.tsx
git commit -m "feat: implement collapsed state UI for ThinkingProcess"
```

---

## Task 4: 实现展开状态时间线UI

**Files:**
- Modify: `frontend/src/components/chat/ThinkingProcess.tsx`

- [ ] **Step 4.1: 在折叠状态UI后添加展开内容**

在`</Box>`之前，`{/* 展开内容将在下一个任务实现 */}`位置替换为：

```typescript
      <Collapse in={expanded} timeout={200}>
        <Box
          sx={{
            mt: 1,
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
      </Collapse>
```

- [ ] **Step 4.2: 提交展开状态UI**

```bash
git add frontend/src/components/chat/ThinkingProcess.tsx
git commit -m "feat: implement expanded timeline UI for ThinkingProcess"
```

---

## Task 5: 重构ChatMessageList组件

**Files:**
- Modify: `frontend/src/components/chat/ChatMessageList.tsx`

- [ ] **Step 5.1: 导入新的ThinkingProcess组件**

在文件顶部的import部分，移除未使用的图标导入，添加ThinkingProcess导入：

```typescript
import { Box, Chip, Stack, Tooltip, Typography, Paper } from '@mui/material'
import { useMemo } from 'react'

import { ChatMessage, ChatReference } from '../../types/chat'
import { MarkdownContent } from './MarkdownContent'
import { ThinkingProcess } from './ThinkingProcess'
```

- [ ] **Step 5.2: 移除旧的ThinkingSummaryPanel和相关辅助函数**

删除以下函数和组件（保留getReferenceText, looksLikeMarkdown, splitIntoSentences, buildSentenceReferenceMap, CitationList, CitationInline, AssistantContent）：
- `buildThinkingTimelineFromEvents`
- `buildThinkingTimeline`
- `ThinkingSummaryPanel`

- [ ] **Step 5.3: 重构ChatMessageList的返回JSX**

替换整个return语句为：

```typescript
  return (
    <Stack spacing={2}>
      {messages.map((message) => {
        if (message.role === 'user') {
          return (
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
          )
        }

        // AI消息 - 无Paper包裹
        return (
          <Box
            key={message.id}
            sx={{
              maxWidth: '80%',
              alignSelf: 'flex-start',
            }}
          >
            {(message.isStreaming || message.timeline?.length || message.agentTrace) ? (
              <ThinkingProcess
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
          </Box>
        )
      })}
    </Stack>
  )
```

- [ ] **Step 5.4: 提交ChatMessageList重构**

```bash
git add frontend/src/components/chat/ChatMessageList.tsx
git commit -m "refactor: simplify ChatMessageList, remove AI message Paper wrapper"
```

---

## Task 6: 测试和验证

**Files:**
- Test: `frontend/src/pages/KnowledgeChatPage.tsx`
- Test: `frontend/src/components/chat/ChatMessageList.tsx`
- Test: `frontend/src/components/chat/ThinkingProcess.tsx`

- [ ] **Step 6.1: 启动开发服务器**

```bash
cd frontend
npm run dev
```

预期：开发服务器在http://localhost:5173启动

- [ ] **Step 6.2: 手动测试折叠状态**

测试步骤：
1. 打开浏览器访问聊天页面
2. 发送一条测试消息
3. 观察AI回复：
   - 用户消息应该有背景色和边框（右对齐）
   - AI回复应该无背景色、无边框（左对齐）
   - 思考过程应该显示为单行小字
   - 点击思考过程应该能展开/收起

预期结果：
- AI消息无Paper包裹
- 思考过程折叠时显示单行
- 用户消息保持原样式

- [ ] **Step 6.3: 测试展开状态**

测试步骤：
1. 点击思考过程文字
2. 观察展开的时间线
3. 验证步骤显示、图标、状态标签
4. 再次点击收起

预期结果：
- 展开动画流畅（200ms）
- 时间线显示完整步骤信息
- 步骤图标和状态正确
- 预览项正确显示

- [ ] **Step 6.4: 测试实时更新**

测试步骤：
1. 发送一条新消息
2. 观察思考过程实时更新
3. 验证占位符动画效果
4. 验证步骤状态变化

预期结果：
- 占位符打字动画正常
- 步骤实时更新
- 状态图标正确切换

- [ ] **Step 6.5: 测试响应式布局**

测试步骤：
1. 调整浏览器窗口大小
2. 测试移动端视图（开发者工具）
3. 验证消息宽度和对齐

预期结果：
- 移动端和桌面端布局正常
- 消息最大宽度80%
- 对齐方式正确

- [ ] **Step 6.6: 测试边界情况**

测试场景：
1. 无思考过程的消息
2. 只有占位符的消息
3. 错误状态的消息
4. 长文本消息

预期结果：
- 无思考过程时不显示ThinkingProcess
- 占位符动画正常
- 错误状态显示红色
- 长文本正确截断和换行

- [ ] **Step 6.7: 验证引用功能**

测试步骤：
1. 发送需要引用的消息
2. 验证内联引用显示
3. 验证引用列表显示

预期结果：
- CitationInline正常显示
- CitationList在内容末尾显示
- 引用悬停提示正常

- [ ] **Step 6.8: 最终提交**

```bash
git add -A
git commit -m "test: verify chat UI simplification implementation"
```

---

## 自查清单

### 规格覆盖
- ✅ Task 1-2: 时间线构建逻辑（设计第2节）
- ✅ Task 3: 折叠状态UI（设计第2节）
- ✅ Task 4: 展开状态UI（设计第2节）
- ✅ Task 5: 移除AI消息Paper包裹（设计第1节）
- ✅ Task 6: 测试所有功能（设计第7节）

### 占位符检查
- ✅ 所有代码块完整
- ✅ 所有步骤有明确指令
- ✅ 所有测试有预期结果
- ✅ 无TBD或TODO

### 类型一致性
- ✅ ThinkingTimelineItem类型定义一致
- ✅ ThinkingProcessProps接口一致
- ✅ 函数签名匹配
- ✅ 组件导入导出一致

---

## 实施注意事项

1. **保留功能**：所有现有功能（实时更新、占位符动画、引用显示）必须正常工作
2. **样式一致性**：颜色、字体、间距遵循设计规范
3. **动画流畅**：展开/收起动画200ms，占位符动画55ms间隔
4. **响应式**：移动端和桌面端都要测试
5. **边界情况**：无思考过程、错误状态、长文本都要处理
6. **提交频率**：每个任务完成后立即提交，保持小步快跑

## 预计时间
- Task 1: 5分钟
- Task 2: 10分钟
- Task 3: 10分钟
- Task 4: 15分钟
- Task 5: 10分钟
- Task 6: 20分钟
- 总计: 约70分钟
