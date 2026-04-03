import { isAxiosError } from 'axios'

import { ApiErrorPayload, ApiRequestError } from '../types/api'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')

export function buildApiUrl(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}

async function parseErrorBody(response: Response): Promise<Record<string, unknown> | null> {
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    try {
      return (await response.json()) as Record<string, unknown>
    } catch {
      return null
    }
  }

  try {
    const text = await response.text()
    if (!text) {
      return null
    }
    return { message: text }
  } catch {
    return null
  }
}

export async function createApiError(response: Response): Promise<ApiRequestError> {
  const body = await parseErrorBody(response)
  const payload: ApiErrorPayload = {
    status: response.status,
    error_code: typeof body?.error_code === 'string' ? body.error_code : undefined,
    message:
      typeof body?.message === 'string'
        ? body.message
        : `请求失败（${response.status}）`,
    details: typeof body?.details === 'string' ? body.details : undefined,
    provider: typeof body?.provider === 'string' ? body.provider : undefined,
    retryable: typeof body?.retryable === 'boolean' ? body.retryable : undefined,
  }

  return new ApiRequestError(payload)
}

export function normalizeApiError(error: unknown): ApiErrorPayload {
  if (error instanceof ApiRequestError) {
    return error.payload
  }

  if (isAxiosError(error)) {
    const data = error.response?.data as Record<string, unknown> | undefined
    return {
      status: error.response?.status,
      error_code: typeof data?.error_code === 'string' ? data.error_code : undefined,
      message:
        typeof data?.message === 'string'
          ? data.message
          : error.message || '请求失败，请稍后重试。',
      details: typeof data?.details === 'string' ? data.details : undefined,
      provider: typeof data?.provider === 'string' ? data.provider : undefined,
      retryable: typeof data?.retryable === 'boolean' ? data.retryable : undefined,
    }
  }

  if (error instanceof Error) {
    return {
      message: error.message || '请求失败，请稍后重试。',
    }
  }

  return {
    message: '请求失败，请稍后重试。',
  }
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), init)
  if (!response.ok) {
    throw await createApiError(response)
  }
  return (await response.json()) as T
}
