from __future__ import annotations

from pathlib import Path
from threading import RLock

from app.core.config import ENV_FILE_PATH, settings
from app.core.env_store import EnvStore
from app.schemas.settings import (
    AgentKnowledgeProfileRead,
    ApiKeyFieldStatus,
    ModelConfigRead,
    ModelConfigUpdate,
    RuntimeModelConfig,
    RuntimeModelConfigStatus,
)


def _mask_api_key(api_key: str) -> str:
    if not api_key:
        return ''
    if len(api_key) <= 8:
        return '*' * len(api_key)
    return f'{api_key[:4]}{"*" * max(len(api_key) - 8, 4)}{api_key[-4:]}'


class ModelConfigService:
    """Runtime source of truth for model configuration with .env persistence."""

    def __init__(self, *, env_path: str | Path | None = None) -> None:
        self.env_store = EnvStore(env_path or ENV_FILE_PATH)
        self._lock = RLock()
        self._version = 0
        self.reload()

    @property
    def version(self) -> int:
        return self._version

    def _read_value(self, env_values: dict[str, str], key: str, fallback: str) -> str:
        value = env_values.get(key)
        if value is None:
            return fallback
        return value.strip()

    def _sync_runtime_settings(self, env_values: dict[str, str]) -> None:
        settings.dialog_provider = self._read_value(env_values, 'DIALOG_PROVIDER', settings.dialog_provider)
        settings.dialog_api_key = self._read_value(env_values, 'DIALOG_API_KEY', settings.dialog_api_key)
        settings.dialog_base_url = self._read_value(env_values, 'DIALOG_BASE_URL', settings.dialog_base_url)
        settings.dialog_model = self._read_value(env_values, 'DIALOG_MODEL', settings.dialog_model)
        settings.dialog_reasoning_effort = self._read_value(
            env_values,
            'DIALOG_REASONING_EFFORT',
            settings.dialog_reasoning_effort,
        )
        settings.knowledge_build_provider = self._read_value(
            env_values,
            'KNOWLEDGE_BUILD_PROVIDER',
            settings.knowledge_build_provider,
        )
        settings.knowledge_build_api_key = self._read_value(
            env_values,
            'KNOWLEDGE_BUILD_API_KEY',
            settings.knowledge_build_api_key,
        )
        settings.knowledge_build_base_url = self._read_value(
            env_values,
            'KNOWLEDGE_BUILD_BASE_URL',
            settings.knowledge_build_base_url,
        )
        settings.knowledge_build_model = self._read_value(
            env_values,
            'KNOWLEDGE_BUILD_MODEL',
            settings.knowledge_build_model,
        )
        settings.knowledge_build_reasoning_effort = self._read_value(
            env_values,
            'KNOWLEDGE_BUILD_REASONING_EFFORT',
            settings.knowledge_build_reasoning_effort,
        )

    def _dialog_defaults(self) -> RuntimeModelConfig:
        provider = (settings.dialog_provider or 'deepseek').strip() or 'deepseek'
        return RuntimeModelConfig(
            provider=provider,
            api_key=settings.dialog_api_key,
            base_url=settings.dialog_base_url,
            model=settings.dialog_model,
            reasoning_effort=settings.dialog_reasoning_effort,
        )

    def _knowledge_build_defaults(self) -> RuntimeModelConfig:
        provider = (settings.knowledge_build_provider or 'deepseek').strip() or 'deepseek'
        return RuntimeModelConfig(
            provider=provider,
            api_key=settings.knowledge_build_api_key,
            base_url=settings.knowledge_build_base_url,
            model=settings.knowledge_build_model,
            reasoning_effort=settings.knowledge_build_reasoning_effort,
        )

    def reload(self) -> None:
        with self._lock:
            env_values = self.env_store.read()
            self._sync_runtime_settings(env_values)
            self._dialog_config = self._dialog_defaults()
            self._knowledge_build_config = self._knowledge_build_defaults()
            self._version += 1

    def get_dialog_config(self) -> RuntimeModelConfig:
        with self._lock:
            return self._dialog_config.model_copy(deep=True)

    def get_knowledge_build_config(self) -> RuntimeModelConfig:
        with self._lock:
            return self._knowledge_build_config.model_copy(deep=True)

    def get_masked_config(self) -> ModelConfigRead:
        with self._lock:
            return ModelConfigRead(
                dialog=RuntimeModelConfigStatus(
                    provider=self._dialog_config.provider,
                    base_url=self._dialog_config.base_url,
                    model=self._dialog_config.model,
                    reasoning_effort=self._dialog_config.reasoning_effort,
                    api_key=ApiKeyFieldStatus(
                        configured=bool(self._dialog_config.api_key),
                        masked_value=_mask_api_key(self._dialog_config.api_key),
                    ),
                ),
                knowledge_build=RuntimeModelConfigStatus(
                    provider=self._knowledge_build_config.provider,
                    base_url=self._knowledge_build_config.base_url,
                    model=self._knowledge_build_config.model,
                    reasoning_effort=self._knowledge_build_config.reasoning_effort,
                    api_key=ApiKeyFieldStatus(
                        configured=bool(self._knowledge_build_config.api_key),
                        masked_value=_mask_api_key(self._knowledge_build_config.api_key),
                    ),
                ),
                knowledge_profile=AgentKnowledgeProfileRead(
                    available=False,
                    status='missing',
                    major_topics=[],
                    high_frequency_entities=[],
                    high_frequency_relations=[],
                    recent_focuses=[],
                    rendered_overlay='',
                    updated_at=None,
                    error_message=None,
                ),
            )

    def update_config(self, payload: ModelConfigUpdate) -> ModelConfigRead:
        field_mapping = {
            'dialog_provider': 'DIALOG_PROVIDER',
            'dialog_base_url': 'DIALOG_BASE_URL',
            'dialog_model': 'DIALOG_MODEL',
            'dialog_reasoning_effort': 'DIALOG_REASONING_EFFORT',
            'dialog_api_key': 'DIALOG_API_KEY',
            'knowledge_build_provider': 'KNOWLEDGE_BUILD_PROVIDER',
            'knowledge_build_base_url': 'KNOWLEDGE_BUILD_BASE_URL',
            'knowledge_build_model': 'KNOWLEDGE_BUILD_MODEL',
            'knowledge_build_reasoning_effort': 'KNOWLEDGE_BUILD_REASONING_EFFORT',
            'knowledge_build_api_key': 'KNOWLEDGE_BUILD_API_KEY',
        }
        updates = {
            env_key: str(value).strip()
            for field_name, env_key in field_mapping.items()
            if (value := getattr(payload, field_name)) is not None
        }
        if not updates:
            return self.get_masked_config()
        self.env_store.update(updates)
        self.reload()
        return self.get_masked_config()


model_config_service = ModelConfigService()
