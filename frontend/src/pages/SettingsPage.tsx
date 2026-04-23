import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import ExpandMoreOutlinedIcon from '@mui/icons-material/ExpandMoreOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import KeyOutlinedIcon from '@mui/icons-material/KeyOutlined'
import RefreshOutlinedIcon from '@mui/icons-material/RefreshOutlined'
import SaveOutlinedIcon from '@mui/icons-material/SaveOutlined'
import VisibilityOffOutlinedIcon from '@mui/icons-material/VisibilityOffOutlined'
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined'
import WarningAmberOutlinedIcon from '@mui/icons-material/WarningAmberOutlined'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useEffect, useMemo, useState } from 'react'

import { useAppToast } from '../components/common/AppToastProvider'
import { ErrorState } from '../components/common/ErrorState'
import { LoadingState } from '../components/common/LoadingState'
import { useModelConfig, useUpdateModelConfig } from '../hooks/useModelConfig'
import { normalizeApiError } from '../services/http'
import { fetchComposedPrompt } from '../services/promptApi'
import { unifiedCardSx } from '../styles/cardStyles'
import { ComposedPrompt } from '../types/prompt'
import { AgentKnowledgeProfileStatus } from '../types/settings'

const EMPTY_KNOWLEDGE_PROFILE: AgentKnowledgeProfileStatus = {
  available: false,
  status: 'missing',
  major_topics: [],
  high_frequency_entities: [],
  high_frequency_relations: [],
  recent_focuses: [],
  rendered_overlay: '',
  updated_at: null,
  error_message: null,
}

interface ApiKeyCardProps {
  title: string
  description: string
  configured: boolean
  provider: string
  model: string
  baseUrl: string
  maskedValue: string
  value: string
  editing: boolean
  revealValue: boolean
  onToggleEdit: () => void
  onSave: () => void
  saving: boolean
  onToggleReveal: () => void
  onChange: (nextValue: string) => void
}

interface KnowledgeProfileSectionProps {
  available: boolean
  status: string
  updatedAt: string | null
  errorMessage: string | null
  majorTopics: string[]
  highFrequencyEntities: string[]
  highFrequencyRelations: string[]
  recentFocuses: string[]
  renderedOverlay: string
}

function ApiKeyCard({
  title,
  description,
  configured,
  provider,
  model,
  baseUrl,
  maskedValue,
  value,
  editing,
  revealValue,
  onToggleEdit,
  onSave,
  saving,
  onToggleReveal,
  onChange,
}: ApiKeyCardProps) {
  const displayValue = editing ? value : maskedValue

  return (
    <Paper
      sx={{
        ...unifiedCardSx,
        p: 3,
      }}
    >
      <Stack spacing={2}>
        <Stack direction="row" justifyContent="space-between" spacing={2} alignItems="flex-start">
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              {title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {description}
            </Typography>
          </Box>
          <Chip
            color={configured ? 'success' : 'warning'}
            icon={configured ? <CheckCircleOutlineIcon /> : <WarningAmberOutlinedIcon />}
            label={configured ? '已配置' : '未配置'}
            sx={{ alignSelf: 'flex-start' }}
          />
        </Stack>

        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
          <Chip size="small" variant="outlined" label={`Provider: ${provider}`} />
          <Chip size="small" variant="outlined" label={`Model: ${model}`} />
          <Chip size="small" variant="outlined" label={baseUrl} />
        </Stack>

        <TextField
          label="API Key"
          fullWidth
          type={revealValue ? 'text' : 'password'}
          value={displayValue}
          onChange={(event) => onChange(event.target.value)}
          disabled={!editing}
          placeholder={editing ? '输入新的 API Key，留空保存可清空当前配置' : undefined}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <KeyOutlinedIcon fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <IconButton onClick={onToggleReveal} edge="end" aria-label="toggle api key visibility">
                  {revealValue ? <VisibilityOffOutlinedIcon /> : <VisibilityOutlinedIcon />}
                </IconButton>
              </InputAdornment>
            ),
          }}
          helperText={
            editing ? '编辑模式下可输入新 Key，保存后会立即热更新后端运行时配置。' : '当前显示的是掩码后的配置值。'
          }
        />

        {editing ? (
          <Stack direction="row" justifyContent="flex-end" spacing={1}>
            <Button variant="contained" startIcon={<SaveOutlinedIcon />} onClick={onSave} disabled={saving}>
              {saving ? '保存中...' : '保存'}
            </Button>
            <Button variant="outlined" startIcon={<EditOutlinedIcon />} onClick={onToggleEdit} disabled={saving}>
              取消编辑
            </Button>
          </Stack>
        ) : (
          <Stack direction="row" justifyContent="flex-end">
            <Button variant="outlined" startIcon={<EditOutlinedIcon />} onClick={onToggleEdit}>
              编辑 Key
            </Button>
          </Stack>
        )}
      </Stack>
    </Paper>
  )
}

function ProfileGroup({ title, items }: { title: string; items: string[] }) {
  return (
    <Stack spacing={1.25}>
      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
        {title}
      </Typography>
      {items.length ? (
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
          {items.map((item) => (
            <Chip key={`${title}-${item}`} size="small" variant="outlined" label={item} />
          ))}
        </Stack>
      ) : (
        <Typography variant="body2" color="text.secondary">
          暂无内容
        </Typography>
      )}
    </Stack>
  )
}

function KnowledgeProfileSection({
  available,
  status,
  updatedAt,
  errorMessage,
  majorTopics,
  highFrequencyEntities,
  highFrequencyRelations,
  recentFocuses,
  renderedOverlay,
}: KnowledgeProfileSectionProps) {
  const [composedPrompt, setComposedPrompt] = useState<ComposedPrompt | null>(null)
  const [loadingComposed, setLoadingComposed] = useState(false)

  const statusLabel =
    status === 'ready' ? '已就绪' : status === 'building' ? '生成中' : status === 'failed' ? '生成失败' : '未生成'
  const statusColor = status === 'ready' ? 'success' : status === 'failed' ? 'error' : 'default'
  const updatedLabel = updatedAt ? new Date(updatedAt).toLocaleString('zh-CN') : '暂无记录'

  const handleLoadComposedPrompt = async () => {
    setLoadingComposed(true)
    try {
      const data = await fetchComposedPrompt()
      setComposedPrompt(data)
    } catch {
      // ignore
    } finally {
      setLoadingComposed(false)
    }
  }

  return (
    <Paper
      sx={{
        ...unifiedCardSx,
        p: 3,
      }}
    >
      <Stack spacing={2.5}>
        <Stack direction="row" justifyContent="space-between" spacing={2} alignItems="flex-start">
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              当前知识画像
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              当前 Agent 启动时会把这份自动生成的知识画像拼接到固定策略 prompt 后面，用于帮助判断知识库里大致有哪些内容。
            </Typography>
          </Box>
          <Chip color={statusColor} label={statusLabel} sx={{ alignSelf: 'flex-start' }} />
        </Stack>

        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
          <Chip size="small" variant="outlined" label={`更新时间：${updatedLabel}`} />
          <Chip size="small" variant="outlined" label={available ? '已接入 Agent 运行时' : '当前暂无可用画像'} />
        </Stack>

        {status === 'failed' && errorMessage ? <Alert severity="error">知识画像刷新失败：{errorMessage}</Alert> : null}

        <ProfileGroup title="主要主题" items={majorTopics} />
        <ProfileGroup title="高频实体" items={highFrequencyEntities} />
        <ProfileGroup title="高频关系" items={highFrequencyRelations} />
        <ProfileGroup title="最近新增知识重点" items={recentFocuses} />

        <Accordion disableGutters elevation={0} sx={{ backgroundColor: 'transparent', '&:before': { display: 'none' } }}>
          <AccordionSummary expandIcon={<ExpandMoreOutlinedIcon />}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
              查看 Agent Prompt Overlay（动态画像部分）
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ pt: 0 }}>
            <Box
              sx={{
                p: 2,
                borderRadius: 0.75,
                border: '1px solid rgba(176, 174, 165, 0.22)',
                backgroundColor: 'rgba(250, 249, 245, 0.72)',
              }}
            >
              <Typography
                variant="body2"
                sx={{
                  whiteSpace: 'pre-wrap',
                  color: 'text.secondary',
                  lineHeight: 1.8,
                }}
              >
                {renderedOverlay || '当前还没有可展示的 overlay 文本。'}
              </Typography>
            </Box>
          </AccordionDetails>
        </Accordion>

        <Accordion disableGutters elevation={0} sx={{ backgroundColor: 'transparent', '&:before': { display: 'none' } }}>
          <AccordionSummary
            expandIcon={<ExpandMoreOutlinedIcon />}
            onClick={() => {
              if (!composedPrompt && !loadingComposed) {
                handleLoadComposedPrompt()
              }
            }}
          >
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                查看完整组合提示词（基础 + 画像）
              </Typography>
              {loadingComposed && <CircularProgress size={16} />}
            </Stack>
          </AccordionSummary>
          <AccordionDetails sx={{ pt: 0 }}>
            <Stack spacing={2}>
              <Box>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: 'primary.main' }}>
                    基础系统提示词
                  </Typography>
                  <Button
                    size="small"
                    startIcon={<RefreshOutlinedIcon />}
                    onClick={handleLoadComposedPrompt}
                    disabled={loadingComposed}
                  >
                    刷新
                  </Button>
                </Stack>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 0.75,
                    border: '1px solid rgba(25, 118, 210, 0.3)',
                    backgroundColor: 'rgba(25, 118, 210, 0.04)',
                    maxHeight: 300,
                    overflow: 'auto',
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      whiteSpace: 'pre-wrap',
                      color: 'text.secondary',
                      lineHeight: 1.8,
                      fontFamily: 'monospace',
                      fontSize: '0.8rem',
                    }}
                  >
                    {composedPrompt?.base_prompt || '点击展开加载...'}
                  </Typography>
                </Box>
              </Box>

              <Box>
                <Typography variant="caption" sx={{ fontWeight: 700, color: 'success.main', mb: 1, display: 'block' }}>
                  动态知识画像 Overlay（自动拼接）
                </Typography>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 0.75,
                    border: '1px solid rgba(46, 125, 50, 0.3)',
                    backgroundColor: 'rgba(46, 125, 50, 0.04)',
                    maxHeight: 200,
                    overflow: 'auto',
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      whiteSpace: 'pre-wrap',
                      color: 'text.secondary',
                      lineHeight: 1.8,
                      fontFamily: 'monospace',
                      fontSize: '0.8rem',
                    }}
                  >
                    {composedPrompt?.overlay || '（暂无动态画像）'}
                  </Typography>
                </Box>
              </Box>

              <Alert severity="info" sx={{ fontSize: '0.75rem' }}>
                当用户存入新内容并成功加入知识图谱后，系统会自动刷新知识画像。刷新后的画像会拼接到基础提示词后面，帮助
                Agent 更好地判断何时调用知识图谱检索工具。
              </Alert>
            </Stack>
          </AccordionDetails>
        </Accordion>
      </Stack>
    </Paper>
  )
}

export function SettingsPage() {
  const { data, isLoading, isError } = useModelConfig()
  const updateMutation = useUpdateModelConfig()
  const { showToast } = useAppToast()
  const [dialogValue, setDialogValue] = useState('')
  const [knowledgeBuildValue, setKnowledgeBuildValue] = useState('')
  const [isEditingDialog, setIsEditingDialog] = useState(false)
  const [isEditingKnowledgeBuild, setIsEditingKnowledgeBuild] = useState(false)
  const [showDialogValue, setShowDialogValue] = useState(false)
  const [showKnowledgeBuildValue, setShowKnowledgeBuildValue] = useState(false)

  useEffect(() => {
    if (!data) {
      return
    }
    if (!isEditingDialog) {
      setDialogValue('')
    }
    if (!isEditingKnowledgeBuild) {
      setKnowledgeBuildValue('')
    }
  }, [data, isEditingDialog, isEditingKnowledgeBuild])

  const missingConfigs = useMemo(() => {
    if (!data) {
      return []
    }
    const items: string[] = []
    if (!data.dialog.api_key.configured) {
      items.push('对话 API Key')
    }
    if (!data.knowledge_build.api_key.configured) {
      items.push('知识库构建 API Key')
    }
    return items
  }, [data])

  if (isLoading) {
    return <LoadingState label="正在加载模型设置..." />
  }

  if (isError || !data) {
    return <ErrorState message="模型设置加载失败" />
  }

  const knowledgeProfile = data.knowledge_profile ?? EMPTY_KNOWLEDGE_PROFILE

  const persistPayload = async (payload: { dialog_api_key?: string; knowledge_build_api_key?: string }) => {
    if (!Object.keys(payload).length) {
      showToast({ severity: 'info', message: '当前没有需要保存的改动。' })
      return
    }

    try {
      await updateMutation.mutateAsync(payload)
      showToast({ severity: 'success', message: 'API Key 已保存，并已立即热更新到后端。' })
    } catch (error) {
      const normalizedError = normalizeApiError(error)
      showToast({
        severity: normalizedError.error_code === 'MODEL_API_KEY_MISSING' ? 'warning' : 'error',
        message: normalizedError.message,
      })
      throw error
    }
  }

  const handleSave = async () => {
    const payload: { dialog_api_key?: string; knowledge_build_api_key?: string } = {}
    if (isEditingDialog) {
      payload.dialog_api_key = dialogValue
    }
    if (isEditingKnowledgeBuild) {
      payload.knowledge_build_api_key = knowledgeBuildValue
    }

    try {
      await persistPayload(payload)
      setIsEditingDialog(false)
      setIsEditingKnowledgeBuild(false)
      setShowDialogValue(false)
      setShowKnowledgeBuildValue(false)
      setDialogValue('')
      setKnowledgeBuildValue('')
    } catch {}
  }

  const handleSaveDialogKey = async () => {
    if (!isEditingDialog) {
      return
    }
    try {
      await persistPayload({ dialog_api_key: dialogValue })
      setIsEditingDialog(false)
      setShowDialogValue(false)
      setDialogValue('')
    } catch {}
  }

  const handleSaveKnowledgeBuildKey = async () => {
    if (!isEditingKnowledgeBuild) {
      return
    }
    try {
      await persistPayload({ knowledge_build_api_key: knowledgeBuildValue })
      setIsEditingKnowledgeBuild(false)
      setShowKnowledgeBuildValue(false)
      setKnowledgeBuildValue('')
    } catch {}
  }

  return (
    <Box sx={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', pr: 1 }}>
        <Stack spacing={2.5}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
            <Button variant="contained" startIcon={<SaveOutlinedIcon />} onClick={handleSave} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? '保存中...' : '保存设置'}
            </Button>
          </Box>

          {missingConfigs.length ? (
            <Alert severity="warning">
              当前仍有未配置项：{missingConfigs.join('、')}。未配置时，对话或知识库构建会弹出提示并中止请求。
            </Alert>
          ) : (
            <Alert severity="success">当前两套 API Key 都已配置完成，新的请求会直接使用这里保存的值。</Alert>
          )}

          <Stack spacing={2.5} sx={{ pb: 1 }}>
            <ApiKeyCard
              title="对话模型 API Key"
              description="用于知识对话、通用补充回答、标题生成、文本优化等面向用户的模型调用。"
              configured={data.dialog.api_key.configured}
              provider={data.dialog.provider}
              model={data.dialog.model}
              baseUrl={data.dialog.base_url}
              maskedValue={data.dialog.api_key.masked_value}
              value={dialogValue}
              editing={isEditingDialog}
              revealValue={showDialogValue}
              onSave={handleSaveDialogKey}
              saving={updateMutation.isPending}
              onToggleEdit={() => {
                setIsEditingDialog((prev) => !prev)
                setDialogValue('')
                setShowDialogValue(false)
              }}
              onToggleReveal={() => setShowDialogValue((prev) => !prev)}
              onChange={setDialogValue}
            />

            <ApiKeyCard
              title="知识库构建 API Key"
              description="用于知识图谱构建、图谱检索相关的模型调用，以及后续知识库增强任务。"
              configured={data.knowledge_build.api_key.configured}
              provider={data.knowledge_build.provider}
              model={data.knowledge_build.model}
              baseUrl={data.knowledge_build.base_url}
              maskedValue={data.knowledge_build.api_key.masked_value}
              value={knowledgeBuildValue}
              editing={isEditingKnowledgeBuild}
              revealValue={showKnowledgeBuildValue}
              onSave={handleSaveKnowledgeBuildKey}
              saving={updateMutation.isPending}
              onToggleEdit={() => {
                setIsEditingKnowledgeBuild((prev) => !prev)
                setKnowledgeBuildValue('')
                setShowKnowledgeBuildValue(false)
              }}
              onToggleReveal={() => setShowKnowledgeBuildValue((prev) => !prev)}
              onChange={setKnowledgeBuildValue}
            />

            <KnowledgeProfileSection
              available={knowledgeProfile.available}
              status={knowledgeProfile.status}
              updatedAt={knowledgeProfile.updated_at}
              errorMessage={knowledgeProfile.error_message}
              majorTopics={knowledgeProfile.major_topics}
              highFrequencyEntities={knowledgeProfile.high_frequency_entities}
              highFrequencyRelations={knowledgeProfile.high_frequency_relations}
              recentFocuses={knowledgeProfile.recent_focuses}
              renderedOverlay={knowledgeProfile.rendered_overlay}
            />
          </Stack>
        </Stack>
      </Box>
    </Box>
  )
}
