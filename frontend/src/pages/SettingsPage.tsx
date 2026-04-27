import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import ExpandMoreOutlinedIcon from '@mui/icons-material/ExpandMoreOutlined'
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
  MenuItem,
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
import { AgentKnowledgeProfileStatus, ModelConfigUpdate, RuntimeModelConfigStatus } from '../types/settings'

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

const EMPTY_RUNTIME_CONFIG: RuntimeModelConfigStatus = {
  provider: '',
  base_url: '',
  model: '',
  reasoning_effort: '',
  api_key: {
    configured: false,
    masked_value: '',
  },
}

const REASONING_EFFORT_OPTIONS = [
  { value: '', label: '默认' },
  { value: 'minimal', label: 'minimal' },
  { value: 'low', label: 'low' },
  { value: 'medium', label: 'medium' },
  { value: 'high', label: 'high' },
  { value: 'xhigh', label: 'xhigh' },
]

const CUSTOM_PROVIDER_PRESET_ID = 'custom'

const MODEL_PROVIDER_PRESETS = [
  {
    id: 'openai',
    label: 'OpenAI',
    provider: 'openai',
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-5.4',
    reasoningEffort: 'xhigh',
    apiKeyRequired: true,
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    provider: 'deepseek',
    baseUrl: 'https://api.deepseek.com/v1',
    model: 'deepseek-chat',
    reasoningEffort: '',
    apiKeyRequired: true,
  },
  {
    id: 'api-121',
    label: 'API-121 公网转发',
    provider: 'cliproxyapi',
    baseUrl: 'https://api.aaccx.pw/v1',
    model: 'gpt-5.4',
    reasoningEffort: 'xhigh',
    apiKeyRequired: true,
  },
  {
    id: 'local-openai-compatible',
    label: '本地 OpenAI 兼容',
    provider: 'local-openai-compatible',
    baseUrl: 'http://localhost:1234/v1',
    model: 'local-model',
    reasoningEffort: '',
    apiKeyRequired: false,
  },
  {
    id: CUSTOM_PROVIDER_PRESET_ID,
    label: '自定义服务商',
    provider: 'custom',
    baseUrl: '',
    model: '',
    reasoningEffort: '',
    apiKeyRequired: false,
  },
]

type ModelProviderPreset = (typeof MODEL_PROVIDER_PRESETS)[number]

interface RuntimeConfigDraft {
  providerPreset: string
  provider: string
  baseUrl: string
  model: string
  reasoningEffort: string
  apiKey: string
  clearApiKey: boolean
}

interface RuntimeConfigCardProps {
  title: string
  description: string
  configured: boolean
  maskedValue: string
  currentConfig: RuntimeModelConfigStatus
  draft: RuntimeConfigDraft
  editing: boolean
  revealValue: boolean
  saving: boolean
  onToggleEdit: () => void
  onSave: () => void
  onToggleReveal: () => void
  onApplyPreset: () => void
  onChange: (patch: Partial<RuntimeConfigDraft>) => void
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

function createRuntimeConfigDraft(config: RuntimeModelConfigStatus): RuntimeConfigDraft {
  const matchedPreset = findMatchingProviderPreset(config)
  return {
    providerPreset: matchedPreset.id,
    provider: config.provider,
    baseUrl: config.base_url,
    model: config.model,
    reasoningEffort: config.reasoning_effort,
    apiKey: '',
    clearApiKey: false,
  }
}

function findProviderPreset(presetId: string): ModelProviderPreset {
  return MODEL_PROVIDER_PRESETS.find((preset) => preset.id === presetId) ?? MODEL_PROVIDER_PRESETS[MODEL_PROVIDER_PRESETS.length - 1]!
}

function findMatchingProviderPreset(config: RuntimeModelConfigStatus): ModelProviderPreset {
  return (
    MODEL_PROVIDER_PRESETS.find(
      (preset) =>
        preset.id !== CUSTOM_PROVIDER_PRESET_ID &&
        preset.provider === config.provider &&
        preset.baseUrl === config.base_url
    ) ?? findProviderPreset(CUSTOM_PROVIDER_PRESET_ID)
  )
}

function isConfigApiKeyRequired(config: RuntimeModelConfigStatus) {
  return findMatchingProviderPreset(config).apiKeyRequired
}

function isApiKeyRequired(draft: RuntimeConfigDraft) {
  return findProviderPreset(draft.providerPreset).apiKeyRequired
}

function applyProviderPreset(draft: RuntimeConfigDraft, presetId: string): RuntimeConfigDraft {
  const preset = findProviderPreset(presetId)
  if (preset.id === CUSTOM_PROVIDER_PRESET_ID) {
    return {
      ...draft,
      providerPreset: preset.id,
      provider: draft.provider || preset.provider,
    }
  }
  return {
    ...draft,
    providerPreset: preset.id,
    provider: preset.provider,
    baseUrl: preset.baseUrl,
    model: preset.model,
    reasoningEffort: preset.reasoningEffort,
  }
}

function applyApi121Preset(config: RuntimeModelConfigStatus): RuntimeConfigDraft {
  return applyProviderPreset(createRuntimeConfigDraft(config), 'api-121')
}

function buildDialogUpdate(draft: RuntimeConfigDraft): ModelConfigUpdate {
  const payload: ModelConfigUpdate = {
    dialog_provider: draft.provider.trim(),
    dialog_base_url: draft.baseUrl.trim(),
    dialog_model: draft.model.trim(),
    dialog_reasoning_effort: draft.reasoningEffort.trim(),
  }
  if (draft.clearApiKey) {
    payload.dialog_api_key = ''
  } else if (draft.apiKey.trim()) {
    payload.dialog_api_key = draft.apiKey.trim()
  }
  return payload
}

function buildKnowledgeBuildUpdate(draft: RuntimeConfigDraft): ModelConfigUpdate {
  const payload: ModelConfigUpdate = {
    knowledge_build_provider: draft.provider.trim(),
    knowledge_build_base_url: draft.baseUrl.trim(),
    knowledge_build_model: draft.model.trim(),
    knowledge_build_reasoning_effort: draft.reasoningEffort.trim(),
  }
  if (draft.clearApiKey) {
    payload.knowledge_build_api_key = ''
  } else if (draft.apiKey.trim()) {
    payload.knowledge_build_api_key = draft.apiKey.trim()
  }
  return payload
}

function RuntimeConfigCard({
  title,
  description,
  configured,
  maskedValue,
  currentConfig,
  draft,
  editing,
  revealValue,
  saving,
  onToggleEdit,
  onSave,
  onToggleReveal,
  onApplyPreset,
  onChange,
}: RuntimeConfigCardProps) {
  const displayValue = editing ? draft.apiKey : maskedValue
  const reasoningLabel = currentConfig.reasoning_effort || '默认'
  const draftApiKeyRequired = isApiKeyRequired(draft)
  const currentApiKeyRequired = isConfigApiKeyRequired(currentConfig)
  const statusColor = configured ? 'success' : currentApiKeyRequired ? 'warning' : 'default'
  const statusLabel = configured ? 'Key 已配置' : currentApiKeyRequired ? 'Key 未配置' : 'Key 可选'

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
            color={statusColor}
            icon={configured ? <CheckCircleOutlineIcon /> : currentApiKeyRequired ? <WarningAmberOutlinedIcon /> : undefined}
            label={statusLabel}
            sx={{ alignSelf: 'flex-start' }}
          />
        </Stack>

        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
          <Chip size="small" variant="outlined" label={`Provider: ${currentConfig.provider || '未设置'}`} />
          <Chip size="small" variant="outlined" label={`Model: ${currentConfig.model || '未设置'}`} />
          <Chip size="small" variant="outlined" label={`Reasoning: ${reasoningLabel}`} />
          <Chip size="small" variant="outlined" label={currentConfig.base_url || '未设置 Base URL'} />
        </Stack>

        {editing ? (
          <Stack spacing={1.5}>
            <TextField
              select
              label="模型厂商"
              fullWidth
              value={draft.providerPreset}
              onChange={(event) => onChange(applyProviderPreset(draft, event.target.value))}
              helperText="选择厂商只会填入推荐配置，API URL 和模型名称仍可手动修改。"
            >
              {MODEL_PROVIDER_PRESETS.map((preset) => (
                <MenuItem key={preset.id} value={preset.id}>
                  {preset.label}
                </MenuItem>
              ))}
            </TextField>
            {draft.providerPreset === CUSTOM_PROVIDER_PRESET_ID ? (
              <TextField
                label="自定义服务商标识"
                fullWidth
                value={draft.provider}
                onChange={(event) => onChange({ provider: event.target.value })}
              />
            ) : null}
            <TextField
              label="Base URL"
              fullWidth
              value={draft.baseUrl}
              onChange={(event) => onChange({ baseUrl: event.target.value })}
            />
            <TextField
              label="Model"
              fullWidth
              value={draft.model}
              onChange={(event) => onChange({ model: event.target.value })}
            />
            <TextField
              select
              label="推理强度"
              fullWidth
              value={draft.reasoningEffort}
              onChange={(event) => onChange({ reasoningEffort: event.target.value })}
              helperText="`gpt-5.4` 预设默认使用 `xhigh`，其他模型可按兼容性自行调整。"
            >
              {REASONING_EFFORT_OPTIONS.map((option) => (
                <MenuItem key={option.value || 'default'} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
        ) : null}

        <TextField
          label={editing ? 'API Key（留空保留当前值）' : 'API Key'}
          fullWidth
          type={revealValue ? 'text' : 'password'}
          value={displayValue}
          onChange={(event) => onChange({ apiKey: event.target.value, clearApiKey: false })}
          disabled={!editing || draft.clearApiKey}
          placeholder={
            editing
              ? configured
                ? '留空表示保留当前 Key，输入新值会替换当前配置'
                : draftApiKeyRequired
                  ? '输入新的 API Key'
                  : '本地兼容服务可留空'
              : undefined
          }
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
            editing
              ? draft.clearApiKey
                ? '当前 Key 会在保存后被清空。'
                : configured
                  ? '当前 Key 已保留。留空不会覆盖，只有输入新值才会替换。'
                  : draftApiKeyRequired
                    ? '当前厂商通常需要 API Key；留空保存后调用时可能鉴权失败。'
                    : '当前厂商允许 API Key 留空；如果本地服务要求鉴权再填写。'
              : '当前显示的是掩码后的配置值。'
          }
        />

        {editing ? (
          <Typography variant="caption" color="text.secondary">
            当前 Key：{maskedValue || '未配置'}
          </Typography>
        ) : null}

        {editing ? (
          <Stack direction="row" justifyContent="space-between" spacing={1} sx={{ flexWrap: 'wrap' }}>
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
              <Button variant="text" onClick={onApplyPreset} disabled={saving}>
                填充 API-121 预设
              </Button>
              <Button
                variant="text"
                color={draft.clearApiKey ? 'warning' : 'inherit'}
                onClick={() =>
                  onChange({
                    clearApiKey: !draft.clearApiKey,
                    apiKey: '',
                  })
                }
                disabled={saving}
              >
                {draft.clearApiKey ? '取消清空 Key' : '清空当前 Key'}
              </Button>
            </Stack>

            <Stack direction="row" spacing={1}>
              <Button variant="contained" startIcon={<SaveOutlinedIcon />} onClick={onSave} disabled={saving}>
                {saving ? '保存中...' : '保存'}
              </Button>
              <Button variant="outlined" startIcon={<EditOutlinedIcon />} onClick={onToggleEdit} disabled={saving}>
                取消编辑
              </Button>
            </Stack>
          </Stack>
        ) : (
          <Stack direction="row" justifyContent="space-between" spacing={1} sx={{ flexWrap: 'wrap' }}>
            <Button variant="text" onClick={onApplyPreset}>
              填充 API-121 预设
            </Button>
            <Button variant="outlined" startIcon={<EditOutlinedIcon />} onClick={onToggleEdit}>
              编辑配置
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
  const [dialogDraft, setDialogDraft] = useState<RuntimeConfigDraft>(() => createRuntimeConfigDraft(EMPTY_RUNTIME_CONFIG))
  const [knowledgeBuildDraft, setKnowledgeBuildDraft] = useState<RuntimeConfigDraft>(() =>
    createRuntimeConfigDraft(EMPTY_RUNTIME_CONFIG)
  )
  const [isEditingDialog, setIsEditingDialog] = useState(false)
  const [isEditingKnowledgeBuild, setIsEditingKnowledgeBuild] = useState(false)
  const [showDialogValue, setShowDialogValue] = useState(false)
  const [showKnowledgeBuildValue, setShowKnowledgeBuildValue] = useState(false)

  useEffect(() => {
    if (!data) {
      return
    }
    if (!isEditingDialog) {
      setDialogDraft(createRuntimeConfigDraft(data.dialog))
    }
    if (!isEditingKnowledgeBuild) {
      setKnowledgeBuildDraft(createRuntimeConfigDraft(data.knowledge_build))
    }
  }, [data, isEditingDialog, isEditingKnowledgeBuild])

  const missingRequiredKeys = useMemo(() => {
    if (!data) {
      return []
    }
    const items: string[] = []
    if (isConfigApiKeyRequired(data.dialog) && !data.dialog.api_key.configured) {
      items.push('对话 API Key')
    }
    if (isConfigApiKeyRequired(data.knowledge_build) && !data.knowledge_build.api_key.configured) {
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

  const validateDraft = (label: string, draft: RuntimeConfigDraft) => {
    if (!draft.provider.trim()) {
      showToast({ severity: 'warning', message: `${label} 的 Provider 不能为空。` })
      return false
    }
    if (!draft.baseUrl.trim()) {
      showToast({ severity: 'warning', message: `${label} 的 Base URL 不能为空。` })
      return false
    }
    if (!draft.model.trim()) {
      showToast({ severity: 'warning', message: `${label} 的 Model 不能为空。` })
      return false
    }
    return true
  }

  const persistPayload = async (payload: ModelConfigUpdate) => {
    if (!Object.keys(payload).length) {
      showToast({ severity: 'info', message: '当前没有需要保存的改动。' })
      return
    }

    try {
      await updateMutation.mutateAsync(payload)
      showToast({ severity: 'success', message: '模型配置已保存，并已立即热更新到后端。' })
    } catch (error) {
      const normalizedError = normalizeApiError(error)
      showToast({
        severity: normalizedError.error_code === 'MODEL_API_KEY_MISSING' ? 'warning' : 'error',
        message: normalizedError.message,
      })
      throw error
    }
  }

  const startDialogEdit = () => {
    setDialogDraft(createRuntimeConfigDraft(data.dialog))
    setIsEditingDialog(true)
    setShowDialogValue(false)
  }

  const startKnowledgeBuildEdit = () => {
    setKnowledgeBuildDraft(createRuntimeConfigDraft(data.knowledge_build))
    setIsEditingKnowledgeBuild(true)
    setShowKnowledgeBuildValue(false)
  }

  const handleApplyPresetToDialog = () => {
    setDialogDraft(applyApi121Preset(data.dialog))
    setIsEditingDialog(true)
    setShowDialogValue(false)
    showToast({ severity: 'info', message: '已为对话模型填入 API-121 公网转发预设，请确认后保存。' })
  }

  const handleApplyPresetToKnowledgeBuild = () => {
    setKnowledgeBuildDraft(applyApi121Preset(data.knowledge_build))
    setIsEditingKnowledgeBuild(true)
    setShowKnowledgeBuildValue(false)
    showToast({ severity: 'info', message: '已为知识库构建模型填入 API-121 公网转发预设，请确认后保存。' })
  }

  const handleApplyPresetToAll = () => {
    setDialogDraft(applyApi121Preset(data.dialog))
    setKnowledgeBuildDraft(applyApi121Preset(data.knowledge_build))
    setIsEditingDialog(true)
    setIsEditingKnowledgeBuild(true)
    setShowDialogValue(false)
    setShowKnowledgeBuildValue(false)
    showToast({ severity: 'info', message: '已为两套模型配置填入 API-121 公网转发预设，请确认后保存。' })
  }

  const handleSave = async () => {
    if (isEditingDialog && !validateDraft('对话模型配置', dialogDraft)) {
      return
    }
    if (isEditingKnowledgeBuild && !validateDraft('知识库构建模型配置', knowledgeBuildDraft)) {
      return
    }

    const payload: ModelConfigUpdate = {}
    if (isEditingDialog) {
      Object.assign(payload, buildDialogUpdate(dialogDraft))
    }
    if (isEditingKnowledgeBuild) {
      Object.assign(payload, buildKnowledgeBuildUpdate(knowledgeBuildDraft))
    }

    try {
      await persistPayload(payload)
      setIsEditingDialog(false)
      setIsEditingKnowledgeBuild(false)
      setShowDialogValue(false)
      setShowKnowledgeBuildValue(false)
    } catch {}
  }

  const handleSaveDialogConfig = async () => {
    if (!isEditingDialog) {
      return
    }
    if (!validateDraft('对话模型配置', dialogDraft)) {
      return
    }
    try {
      await persistPayload(buildDialogUpdate(dialogDraft))
      setIsEditingDialog(false)
      setShowDialogValue(false)
    } catch {}
  }

  const handleSaveKnowledgeBuildConfig = async () => {
    if (!isEditingKnowledgeBuild) {
      return
    }
    if (!validateDraft('知识库构建模型配置', knowledgeBuildDraft)) {
      return
    }
    try {
      await persistPayload(buildKnowledgeBuildUpdate(knowledgeBuildDraft))
      setIsEditingKnowledgeBuild(false)
      setShowKnowledgeBuildValue(false)
    } catch {}
  }

  return (
    <Box sx={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', pr: 1 }}>
        <Stack spacing={2.5}>
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
            <Button variant="contained" startIcon={<SaveOutlinedIcon />} onClick={handleSave} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? '保存中...' : '保存设置'}
            </Button>
            <Button variant="outlined" onClick={handleApplyPresetToAll} disabled={updateMutation.isPending}>
              一键填充 API-121 预设
            </Button>
          </Stack>

          {missingRequiredKeys.length ? (
            <Alert severity="warning">
              当前云端厂商配置缺少：{missingRequiredKeys.join('、')}。本地 OpenAI 兼容服务可留空，云端服务通常需要填写。
            </Alert>
          ) : (
            <Alert severity="success">当前两套运行时模型配置已保存，新的请求会直接使用这里的厂商、URL、模型和推理强度。</Alert>
          )}

          <Alert severity="info">
            模型厂商只是预设模板，API URL、模型名称和推理强度都可以继续手动修改。编辑时 API Key 留空会保留当前值，只有点击“清空当前 Key”才会移除。
          </Alert>

          <Stack spacing={2.5} sx={{ pb: 1 }}>
            <RuntimeConfigCard
              title="对话模型配置"
              description="用于知识对话、通用补充回答、标题生成、文本优化等面向用户的模型调用。"
              configured={data.dialog.api_key.configured}
              maskedValue={data.dialog.api_key.masked_value}
              currentConfig={data.dialog}
              draft={dialogDraft}
              editing={isEditingDialog}
              revealValue={showDialogValue}
              saving={updateMutation.isPending}
              onSave={handleSaveDialogConfig}
              onToggleEdit={() => {
                if (isEditingDialog) {
                  setIsEditingDialog(false)
                  setDialogDraft(createRuntimeConfigDraft(data.dialog))
                  setShowDialogValue(false)
                  return
                }
                startDialogEdit()
              }}
              onToggleReveal={() => setShowDialogValue((prev) => !prev)}
              onApplyPreset={handleApplyPresetToDialog}
              onChange={(patch) => setDialogDraft((prev) => ({ ...prev, ...patch }))}
            />

            <RuntimeConfigCard
              title="知识库构建模型配置"
              description="用于知识图谱构建、图谱检索相关的模型调用，以及后续知识库增强任务。"
              configured={data.knowledge_build.api_key.configured}
              maskedValue={data.knowledge_build.api_key.masked_value}
              currentConfig={data.knowledge_build}
              draft={knowledgeBuildDraft}
              editing={isEditingKnowledgeBuild}
              revealValue={showKnowledgeBuildValue}
              saving={updateMutation.isPending}
              onSave={handleSaveKnowledgeBuildConfig}
              onToggleEdit={() => {
                if (isEditingKnowledgeBuild) {
                  setIsEditingKnowledgeBuild(false)
                  setKnowledgeBuildDraft(createRuntimeConfigDraft(data.knowledge_build))
                  setShowKnowledgeBuildValue(false)
                  return
                }
                startKnowledgeBuildEdit()
              }}
              onToggleReveal={() => setShowKnowledgeBuildValue((prev) => !prev)}
              onApplyPreset={handleApplyPresetToKnowledgeBuild}
              onChange={(patch) => setKnowledgeBuildDraft((prev) => ({ ...prev, ...patch }))}
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
