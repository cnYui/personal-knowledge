import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiRequestError } from '../types/api'
import { buildApiUrl, createApiError, getJson, http, normalizeApiError, postJson } from './http'

describe('http service', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('buildApiUrl 会统一补齐前导斜杠', () => {
    expect(buildApiUrl('api/ping')).toBe('http://127.0.0.1:8000/api/ping')
    expect(buildApiUrl('/api/ping')).toBe('http://127.0.0.1:8000/api/ping')
  })

  it('getJson 通过共享 axios client 返回 data', async () => {
    vi.spyOn(http, 'request').mockResolvedValue({ data: { ok: true } } as never)

    await expect(getJson<{ ok: boolean }>('/api/ping')).resolves.toEqual({ ok: true })
  })

  it('postJson 失败时抛出归一化后的 ApiRequestError', async () => {
    vi.spyOn(http, 'request').mockRejectedValue({
      isAxiosError: true,
      message: 'Request failed',
      response: {
        status: 429,
        data: {
          message: 'rate limited',
          error_code: 'RATE_LIMITED',
          retryable: true,
        },
      },
    })

    await expect(postJson('/api/ping', { ok: true })).rejects.toMatchObject({
      name: 'ApiRequestError',
      payload: expect.objectContaining({
        status: 429,
        error_code: 'RATE_LIMITED',
        message: 'rate limited',
        retryable: true,
      }),
    })
  })

  it('createApiError 会读取 fetch Response 的 JSON 错误体', async () => {
    const response = new Response(JSON.stringify({ message: 'bad request', error_code: 'BAD_REQUEST' }), {
      status: 400,
      headers: { 'content-type': 'application/json' },
    })

    await expect(createApiError(response)).resolves.toBeInstanceOf(ApiRequestError)
  })

  it('normalizeApiError 对未知异常回退为通用消息', () => {
    expect(normalizeApiError('boom')).toEqual({
      message: '请求失败，请稍后重试。',
    })
  })
})
