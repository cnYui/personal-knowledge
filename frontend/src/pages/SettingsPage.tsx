import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import KeyOutlinedIcon from '@mui/icons-material/KeyOutlined'
import SaveOutlinedIcon from '@mui/icons-material/SaveOutlined'
import VisibilityOffOutlinedIcon from '@mui/icons-material/VisibilityOffOutlined'
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined'
import WarningAmberOutlinedIcon from '@mui/icons-material/WarningAmberOutlined'
import {
  Alert,
  Box,
  Button,
  Chip,
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
import { normalizeApiError } from '../services/apiClient'

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
  onToggleReveal: () => void
  onChange: (nextValue: string) => void
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
  onToggleReveal,
  onChange,
}: ApiKeyCardProps) {
  const displayValue = editing ? value : maskedValue

  return (
    <Paper
      sx={{
        p: 3,
        borderRadius: 4,
        border: '1px solid rgba(176, 174, 165, 0.24)',
        background: 'linear-gradient(180deg, rgba(255,253,248,0.98) 0%, rgba(245,241,232,0.94) 100%)',
        boxShadow: '0 18px 40px rgba(20, 20, 19, 0.05)',
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

        <Stack direction="row" justifyContent="flex-end">
          <Button variant={editing ? 'contained' : 'outlined'} startIcon={<EditOutlinedIcon />} onClick={onToggleEdit}>
            {editing ? '取消编辑' : '编辑 Key'}
          </Button>
        </Stack>
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

  const handleSave = async () => {
    const payload: { dialog_api_key?: string; knowledge_build_api_key?: string } = {}
    if (isEditingDialog) {
      payload.dialog_api_key = dialogValue
    }
    if (isEditingKnowledgeBuild) {
      payload.knowledge_build_api_key = knowledgeBuildValue
    }

    if (!Object.keys(payload).length) {
      showToast({ severity: 'info', message: '当前没有需要保存的改动。' })
      return
    }

    try {
      await updateMutation.mutateAsync(payload)
      setIsEditingDialog(false)
      setIsEditingKnowledgeBuild(false)
      setShowDialogValue(false)
      setShowKnowledgeBuildValue(false)
      setDialogValue('')
      setKnowledgeBuildValue('')
      showToast({ severity: 'success', message: 'API Key 已保存，并已立即热更新到后端。' })
    } catch (error) {
      const normalizedError = normalizeApiError(error)
      showToast({
        severity: normalizedError.error_code === 'MODEL_API_KEY_MISSING' ? 'warning' : 'error',
        message: normalizedError.message,
      })
    }
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
              onToggleEdit={() => {
                setIsEditingKnowledgeBuild((prev) => !prev)
                setKnowledgeBuildValue('')
                setShowKnowledgeBuildValue(false)
              }}
              onToggleReveal={() => setShowKnowledgeBuildValue((prev) => !prev)}
              onChange={setKnowledgeBuildValue}
            />
          </Stack>
        </Stack>
      </Box>
    </Box>
  )
}
