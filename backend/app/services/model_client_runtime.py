from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from graphiti_core.llm_client.config import LLMConfig
from openai import AsyncOpenAI

from app.core.model_errors import ModelAPIError, map_model_api_error
from app.schemas.settings import RuntimeModelConfig
from app.services.model_config_service import ModelConfigService, model_config_service

LOCAL_COMPATIBLE_PLACEHOLDER_API_KEY = 'not-needed'
ModelRuntimePurpose = Literal['dialog', 'knowledge_build']


def resolve_openai_compatible_api_key(api_key: str) -> str:
    return api_key.strip() or LOCAL_COMPATIBLE_PLACEHOLDER_API_KEY


def create_openai_compatible_client(*, api_key: str, base_url: str) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=resolve_openai_compatible_api_key(api_key),
        base_url=base_url,
    )


@dataclass(frozen=True)
class ModelRuntime:
    purpose: ModelRuntimePurpose
    provider: str
    base_url: str
    model: str
    reasoning_effort: str
    version: int
    client: Any
    signature: tuple[str, str, str, str, str, str, int]

    def completion_extra(self) -> dict[str, str]:
        if not self.reasoning_effort:
            return {}
        return {'reasoning_effort': self.reasoning_effort}

    def map_error(self, error: Exception) -> ModelAPIError:
        return map_model_api_error(error, provider=self.provider)


class ModelRuntimeGateway:
    """统一管理 OpenAI 兼容模型运行时，避免业务流程散落 API 配置细节。"""

    def __init__(
        self,
        *,
        model_config_service_instance: ModelConfigService | None = None,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.model_config_service = model_config_service_instance or model_config_service
        self.client_factory = client_factory or create_openai_compatible_client
        self._runtime_cache: dict[ModelRuntimePurpose, ModelRuntime] = {}

    def _get_config(self, purpose: ModelRuntimePurpose) -> RuntimeModelConfig:
        if purpose == 'dialog':
            return self.model_config_service.get_dialog_config()
        if purpose == 'knowledge_build':
            return self.model_config_service.get_knowledge_build_config()
        raise ValueError(f'Unsupported model runtime purpose: {purpose}')

    def _build_signature(
        self,
        purpose: ModelRuntimePurpose,
        config: RuntimeModelConfig,
    ) -> tuple[str, str, str, str, str, str, int]:
        return (
            purpose,
            config.provider,
            config.api_key,
            config.base_url,
            config.model,
            config.reasoning_effort,
            self.model_config_service.version,
        )

    def get_runtime(self, purpose: ModelRuntimePurpose) -> ModelRuntime:
        config = self._get_config(purpose)
        signature = self._build_signature(purpose, config)
        cached_runtime = self._runtime_cache.get(purpose)
        if cached_runtime is not None and cached_runtime.signature == signature:
            return cached_runtime

        runtime = ModelRuntime(
            purpose=purpose,
            provider=config.provider,
            base_url=config.base_url,
            model=config.model,
            reasoning_effort=config.reasoning_effort,
            version=self.model_config_service.version,
            client=self.client_factory(
                api_key=resolve_openai_compatible_api_key(config.api_key),
                base_url=config.base_url,
            ),
            signature=signature,
        )
        self._runtime_cache[purpose] = runtime
        return runtime

    def build_graphiti_llm_config(
        self,
        purpose: ModelRuntimePurpose,
        *,
        max_tokens: int | None = None,
    ) -> LLMConfig:
        config = self._get_config(purpose)
        return LLMConfig(
            api_key=resolve_openai_compatible_api_key(config.api_key),
            base_url=config.base_url,
            model=config.model,
            small_model=config.model,
            max_tokens=max_tokens,
        )


model_runtime_gateway = ModelRuntimeGateway()
