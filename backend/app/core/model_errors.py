from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ModelAPIError(Exception):
    error_code: str
    message: str
    status_code: int
    details: str = ''
    provider: str = ''
    retryable: bool = False

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> dict[str, Any]:
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'provider': self.provider,
            'retryable': self.retryable,
        }


def missing_api_key_error(*, provider: str, purpose: str) -> ModelAPIError:
    return ModelAPIError(
        error_code='MODEL_API_KEY_MISSING',
        message='尚未配置 API Key，请先前往设置页面完成配置。',
        status_code=400,
        details=f'{purpose} 缺少可用的 {provider} API Key。',
        provider=provider,
        retryable=False,
    )


def map_model_api_error(error: Exception, *, provider: str) -> ModelAPIError:
    if isinstance(error, ModelAPIError):
        return error

    status_code = getattr(error, 'status_code', None) or getattr(error, 'http_status', None)
    details = str(error)
    normalized = details.lower()

    if status_code == 402 or '402' in normalized or 'insufficient' in normalized or 'quota' in normalized:
        return ModelAPIError(
            error_code='MODEL_API_QUOTA_EXCEEDED',
            message='当前 API Key 可用额度已用完，请更换 Key 或检查账号额度。',
            status_code=402,
            details=details,
            provider=provider,
            retryable=False,
        )

    if status_code in {401, 403} or 'invalid api key' in normalized or 'auth' in normalized:
        return ModelAPIError(
            error_code='MODEL_API_AUTH_FAILED',
            message='API Key 无效或鉴权失败，请检查设置中的 Key 是否正确。',
            status_code=401,
            details=details,
            provider=provider,
            retryable=False,
        )

    if status_code == 429 or '429' in normalized or 'rate limit' in normalized or 'too many requests' in normalized:
        return ModelAPIError(
            error_code='MODEL_API_RATE_LIMITED',
            message='请求过于频繁，请稍后再试。',
            status_code=429,
            details=details,
            provider=provider,
            retryable=True,
        )

    if status_code and int(status_code) >= 500:
        return ModelAPIError(
            error_code='MODEL_API_UPSTREAM_ERROR',
            message='模型服务暂时不可用，请稍后重试。',
            status_code=int(status_code),
            details=details,
            provider=provider,
            retryable=True,
        )

    if any(keyword in normalized for keyword in ('timeout', 'connection', 'dns', 'unreachable', 'connect')):
        return ModelAPIError(
            error_code='MODEL_API_NETWORK_ERROR',
            message='无法连接模型服务，请检查网络或服务地址配置。',
            status_code=503,
            details=details,
            provider=provider,
            retryable=True,
        )

    return ModelAPIError(
        error_code='MODEL_API_UPSTREAM_ERROR',
        message='模型服务暂时不可用，请稍后重试。',
        status_code=500,
        details=details,
        provider=provider,
        retryable=True,
    )
