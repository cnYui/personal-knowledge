import axios, { AxiosRequestConfig } from 'axios'

import { ApiErrorPayload, ApiRequestError } from '../types/api'
import { DEFAULT_API_BASE_URL } from '../utils/constants'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, '')

export const http = axios.create({
  baseURL: API_BASE_URL,
})

type RequestOptions = Omit<AxiosRequestConfig, 'url' | 'method' | 'data'>

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

  const text = await response.text().catch(() => '')
  return text ? { message: text } : null
}

export async function createApiError(response: Response): Promise<ApiRequestError> {
  const body = await parseErrorBody(response)

  return new ApiRequestError({
    status: response.status,
    error_code: typeof body?.error_code === 'string' ? body.error_code : undefined,
    message: typeof body?.message === 'string' ? body.message : `请求失败（${response.status}）`,
    details: typeof body?.details === 'string' ? body.details : undefined,
    provider: typeof body?.provider === 'string' ? body.provider : undefined,
    retryable: typeof body?.retryable === 'boolean' ? body.retryable : undefined,
  })
}

export function normalizeApiError(error: unknown): ApiErrorPayload {
  if (error instanceof ApiRequestError) {
    return error.payload
  }

  if (axios.isAxiosError(error)) {
    const data = error.response?.data as Record<string, unknown> | undefined

    return {
      status: error.response?.status,
      error_code: typeof data?.error_code === 'string' ? data.error_code : undefined,
      message: typeof data?.message === 'string' ? data.message : error.message || '请求失败，请稍后重试。',
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

async function requestJson<T>(
  method: AxiosRequestConfig['method'],
  url: string,
  data?: unknown,
  config?: RequestOptions
): Promise<T> {
  try {
    const response = await http.request<T>({
      ...config,
      method,
      url,
      data,
    })

    return response.data
  } catch (error) {
    throw new ApiRequestError(normalizeApiError(error))
  }
}

export function getJson<T>(url: string, config?: RequestOptions) {
  return requestJson<T>('GET', url, undefined, config)
}

export function postJson<T>(url: string, data?: unknown, config?: RequestOptions) {
  return requestJson<T>('POST', url, data, config)
}

export function putJson<T>(url: string, data?: unknown, config?: RequestOptions) {
  return requestJson<T>('PUT', url, data, config)
}

export async function deleteVoid(url: string, config?: RequestOptions) {
  await requestJson<unknown>('DELETE', url, undefined, config)
}

export function postForm<T>(url: string, data: FormData, config?: RequestOptions) {
  return requestJson<T>('POST', url, data, config)
}
