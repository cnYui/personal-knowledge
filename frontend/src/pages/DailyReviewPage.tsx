import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import AccessTimeOutlinedIcon from '@mui/icons-material/AccessTimeOutlined'
import PlaylistAddCheckCircleOutlinedIcon from '@mui/icons-material/PlaylistAddCheckCircleOutlined'
import SearchIcon from '@mui/icons-material/Search'
import ScheduleOutlinedIcon from '@mui/icons-material/ScheduleOutlined'
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useMemo, useState } from 'react'

import { ErrorState } from '../components/common/ErrorState'
import { LoadingState } from '../components/common/LoadingState'
import { useDailyReview } from '../hooks/useDailyReview'
import { unifiedCardHoverSx, unifiedCardMutedBackground, unifiedCardSx } from '../styles/cardStyles'
import { DailyReviewCard, DailyReviewTopic } from '../types/dailyReview'
import { formatDate } from '../utils/format'

function OverviewStrip({
  recommendedCount,
  recentCount,
  activeTopicsLabel,
}: {
  recommendedCount: number
  recentCount: number
  activeTopicsLabel: string
}) {
  return (
    <Paper
      sx={{
        ...unifiedCardSx,
        px: 2,
        py: 1.5,
        bgcolor: 'rgba(255, 253, 248, 0.72)',
      }}
    >
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} useFlexGap flexWrap="wrap" alignItems={{ md: 'center' }}>
        <Typography variant="caption" color="text.secondary" sx={{ minWidth: { md: 72 } }}>
          今日概览
        </Typography>
        <Chip size="small" variant="outlined" label={`推荐回顾 ${recommendedCount}`} />
        <Chip size="small" variant="outlined" label={`最近 14 天新增 ${recentCount}`} />
        <Typography variant="caption" color="text.secondary">
          活跃主题：{activeTopicsLabel}
        </Typography>
      </Stack>
    </Paper>
  )
}

function DailyReviewFilterBar() {
  return (
    <Stack>
      <TextField
        fullWidth
        placeholder="浏览今日推荐内容"
        value=""
        inputProps={{ readOnly: true }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
        }}
        sx={{
          '& .MuiInputBase-root': {
            bgcolor: '#fffdf8',
          },
        }}
      />
    </Stack>
  )
}

function getReviewStatusChip(item: DailyReviewCard, refinementTone: boolean) {
  if (refinementTone) {
    return (
      <Chip
        label="待继续整理"
        size="small"
        variant="outlined"
        icon={<PlaylistAddCheckCircleOutlinedIcon />}
        sx={{
          borderColor: 'rgba(217, 119, 87, 0.28)',
          color: '#b25f45',
          backgroundColor: 'rgba(217, 119, 87, 0.06)',
        }}
      />
    )
  }

  return (
    <Chip
      label={item.graph_status === 'added' ? '已在图谱' : '待整理'}
      size="small"
      color={item.graph_status === 'added' ? 'success' : 'default'}
      icon={item.graph_status === 'added' ? <CheckCircleOutlineIcon /> : <ScheduleOutlinedIcon />}
    />
  )
}

function ReviewCard({
  item,
  onOpen,
  tone = 'default',
}: {
  item: DailyReviewCard
  onOpen: (item: DailyReviewCard) => void
  tone?: 'default' | 'refinement'
}) {
  const refinementTone = tone === 'refinement'
  const title = item.title?.trim() ? item.title : '待生成标题'
  const summary = item.summary.length > 120 ? `${item.summary.slice(0, 120)}...` : item.summary

  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
      <Paper
        onClick={() => onOpen(item)}
        elevation={0}
        sx={{
          ...unifiedCardSx,
          ...unifiedCardHoverSx,
          px: 2,
          py: 1.65,
          cursor: 'pointer',
          maxWidth: { xs: '100%', md: '82%' },
          border: refinementTone ? '1px dashed rgba(217, 119, 87, 0.32)' : '1px solid',
          borderColor: refinementTone ? 'rgba(217, 119, 87, 0.32)' : item.graph_status === 'added' ? 'rgba(120, 140, 93, 0.42)' : 'divider',
          bgcolor: unifiedCardMutedBackground,
          '&:hover': {
            ...((unifiedCardHoverSx as { '&:hover'?: object })['&:hover'] ?? {}),
            borderColor: refinementTone ? 'rgba(217, 119, 87, 0.46)' : 'rgba(20, 20, 19, 0.28)',
            bgcolor: unifiedCardMutedBackground,
          },
        }}
      >
        <Stack spacing={1}>
          <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
            <Typography variant="subtitle1" fontWeight={600} sx={{ color: 'text.primary' }}>
              {title}
            </Typography>
            {getReviewStatusChip(item, refinementTone)}
          </Stack>

          <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
            {summary}
          </Typography>

          {item.reasons.length ? (
            <Typography variant="caption" color="text.secondary">
              {item.reasons[0]?.label}
            </Typography>
          ) : null}

          <Stack direction="row" spacing={0.5} alignItems="center" color="text.secondary">
            <AccessTimeOutlinedIcon fontSize="inherit" />
            <Typography variant="caption">{formatDate(item.updated_at || item.created_at)}</Typography>
          </Stack>
        </Stack>
      </Paper>
    </Box>
  )
}

function TopicCard({ topic }: { topic: DailyReviewTopic }) {
  return (
    <Paper
      sx={{
        ...unifiedCardSx,
        px: 2,
        py: 1.65,
      }}
    >
      <Stack spacing={1.1}>
        <Stack direction="row" justifyContent="space-between" spacing={2} alignItems="center">
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            {topic.topic}
          </Typography>
          <Chip size="small" variant="outlined" label={`${topic.count} 条相关记录`} />
        </Stack>
        <Typography variant="body2" color="text.secondary">
          {topic.summary}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          最近出现：{formatDate(topic.last_seen_at)}
        </Typography>
      </Stack>
    </Paper>
  )
}

function ReviewDetailDrawer({
  item,
  open,
  onClose,
}: {
  item: DailyReviewCard | null
  open: boolean
  onClose: () => void
}) {
  if (!item) {
    return null
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>
        <span>{item.title}</span>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.9 }}>
            {item.content}
          </Typography>

          <Stack spacing={0.75}>
            <Typography variant="caption" color="text.secondary">
              创建时间：{formatDate(item.created_at)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              更新时间：{formatDate(item.updated_at)}
            </Typography>
            {item.graph_status === 'added' && item.graph_added_at ? (
              <Typography variant="caption" color="success.main">
                ✓ 已添加到知识图谱：{formatDate(item.graph_added_at)}
              </Typography>
            ) : null}
          </Stack>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>关闭</Button>
      </DialogActions>
    </Dialog>
  )
}

function SectionBlock({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <Stack spacing={1.25}>
      <Stack spacing={0.5}>
        <Typography variant="h6" sx={{ fontWeight: 800 }}>
          {title}
        </Typography>
        {description ? (
          <Typography variant="body2" color="text.secondary">
            {description}
          </Typography>
        ) : null}
      </Stack>
      {children}
    </Stack>
  )
}

export function DailyReviewPage() {
  const { data, isLoading, isError } = useDailyReview()
  const [selectedCard, setSelectedCard] = useState<DailyReviewCard | null>(null)

  const activeTopicsLabel = useMemo(() => data?.overview.active_topics?.slice(0, 3).join(' / ') || '暂无明显主题', [data])
  const recommendedItems = data?.recommended ?? []
  const topicFocuses = data?.topic_focuses ?? []
  const graphHighlights = data?.graph_highlights ?? []
  const needsRefinement = data?.needs_refinement ?? []

  if (isLoading) {
    return <LoadingState label="正在整理今日回顾..." />
  }

  if (isError || !data) {
    return <ErrorState message="每日回顾加载失败" />
  }

  return (
    <Box sx={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', pr: 1 }}>
        <Stack spacing={3}>
          <DailyReviewFilterBar />

          <OverviewStrip
            recommendedCount={data.overview.recommended_count}
            recentCount={data.overview.recent_memory_count}
            activeTopicsLabel={activeTopicsLabel}
          />

          <SectionBlock title="今日推荐回顾" description="今天最值得重新回看的知识条目。">
            {recommendedItems.length ? (
              <Stack spacing={1.5}>
                {recommendedItems.map((item) => (
                  <ReviewCard key={item.id} item={item} onOpen={setSelectedCard} />
                ))}
              </Stack>
            ) : (
              <Alert severity="info">今天暂无推荐回顾内容。</Alert>
            )}
          </SectionBlock>

          <SectionBlock title="最近主题聚焦" description="最近几天持续出现的主题，适合集中复盘。">
            <Stack spacing={1.5}>
              {topicFocuses.map((topic) => (
                <TopicCard key={topic.topic} topic={topic} />
              ))}
            </Stack>
          </SectionBlock>

          <SectionBlock title="最近已沉淀进知识图谱" description="这些内容已成功进入知识图谱，更适合作为系统已吸收的知识回看。">
            <Stack spacing={1.5}>
              {graphHighlights.map((item) => (
                <ReviewCard key={`graph-${item.id}`} item={item} onOpen={setSelectedCard} />
              ))}
            </Stack>
          </SectionBlock>

          <SectionBlock title="待继续整理" description="这些内容最近出现过，但还没有完全沉淀进知识图谱。">
            <Stack spacing={1.5} sx={{ pb: 1 }}>
              {needsRefinement.map((item) => (
                <ReviewCard key={`refine-${item.id}`} item={item} onOpen={setSelectedCard} tone="refinement" />
              ))}
            </Stack>
          </SectionBlock>
        </Stack>
      </Box>

      <ReviewDetailDrawer item={selectedCard} open={Boolean(selectedCard)} onClose={() => setSelectedCard(null)} />
    </Box>
  )
}
