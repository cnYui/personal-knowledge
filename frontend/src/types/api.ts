export interface ApiErrorPayload {
  status?: number
  error_code?: string
  message: string
  details?: string
  provider?: string
  retryable?: boolean
}

export class ApiRequestError extends Error {
  status: number
  payload: ApiErrorPayload

  constructor(payload: ApiErrorPayload) {
    super(payload.message)
    this.name = 'ApiRequestError'
    this.status = payload.status ?? 500
    this.payload = payload
  }
}
