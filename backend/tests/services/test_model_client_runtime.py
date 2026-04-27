from app.services.model_client_runtime import (
    LOCAL_COMPATIBLE_PLACEHOLDER_API_KEY,
    ModelRuntimeGateway,
    resolve_openai_compatible_api_key,
)
from app.schemas.settings import ModelConfigUpdate
from app.services.model_config_service import ModelConfigService


class FakeOpenAIClient:
    def __init__(self, *, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url


def test_resolve_openai_compatible_api_key_preserves_configured_key():
    assert resolve_openai_compatible_api_key(' sk-real ') == 'sk-real'


def test_resolve_openai_compatible_api_key_uses_placeholder_for_local_service_without_key():
    assert resolve_openai_compatible_api_key('') == LOCAL_COMPATIBLE_PLACEHOLDER_API_KEY


def test_runtime_gateway_builds_dialog_runtime_from_config(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        'DIALOG_PROVIDER=cliproxyapi\n'
        'DIALOG_API_KEY=dialog-key\n'
        'DIALOG_BASE_URL=https://api.aaccx.pw/v1\n'
        'DIALOG_MODEL=gpt-5.4\n'
        'DIALOG_REASONING_EFFORT=xhigh\n',
        encoding='utf-8',
    )
    service = ModelConfigService(env_path=env_path)
    gateway = ModelRuntimeGateway(
        model_config_service_instance=service,
        client_factory=lambda *, api_key, base_url: FakeOpenAIClient(api_key=api_key, base_url=base_url),
    )

    runtime = gateway.get_runtime('dialog')

    assert runtime.provider == 'cliproxyapi'
    assert runtime.model == 'gpt-5.4'
    assert runtime.reasoning_effort == 'xhigh'
    assert runtime.client.api_key == 'dialog-key'
    assert runtime.client.base_url == 'https://api.aaccx.pw/v1'
    assert runtime.completion_extra() == {'reasoning_effort': 'xhigh'}


def test_runtime_gateway_refreshes_when_config_version_changes(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        'DIALOG_API_KEY=first-key\n'
        'DIALOG_BASE_URL=http://localhost:1234/v1\n'
        'DIALOG_MODEL=local-model\n',
        encoding='utf-8',
    )
    service = ModelConfigService(env_path=env_path)
    gateway = ModelRuntimeGateway(
        model_config_service_instance=service,
        client_factory=lambda *, api_key, base_url: FakeOpenAIClient(api_key=api_key, base_url=base_url),
    )

    first_runtime = gateway.get_runtime('dialog')
    service.update_config(ModelConfigUpdate(dialog_api_key='second-key', dialog_model='next-model'))
    second_runtime = gateway.get_runtime('dialog')

    assert first_runtime is not second_runtime
    assert second_runtime.client.api_key == 'second-key'
    assert second_runtime.model == 'next-model'


def test_runtime_gateway_uses_placeholder_for_empty_local_key(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        'KNOWLEDGE_BUILD_API_KEY=\n'
        'KNOWLEDGE_BUILD_BASE_URL=http://localhost:11434/v1\n'
        'KNOWLEDGE_BUILD_MODEL=qwen-local\n',
        encoding='utf-8',
    )
    service = ModelConfigService(env_path=env_path)
    gateway = ModelRuntimeGateway(
        model_config_service_instance=service,
        client_factory=lambda *, api_key, base_url: FakeOpenAIClient(api_key=api_key, base_url=base_url),
    )

    runtime = gateway.get_runtime('knowledge_build')

    assert runtime.client.api_key == LOCAL_COMPATIBLE_PLACEHOLDER_API_KEY
    assert runtime.model == 'qwen-local'


def test_runtime_gateway_builds_graphiti_llm_config(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        'KNOWLEDGE_BUILD_API_KEY=build-key\n'
        'KNOWLEDGE_BUILD_BASE_URL=https://api.aaccx.pw/v1\n'
        'KNOWLEDGE_BUILD_MODEL=gpt-5.4\n',
        encoding='utf-8',
    )
    service = ModelConfigService(env_path=env_path)
    gateway = ModelRuntimeGateway(model_config_service_instance=service)

    config = gateway.build_graphiti_llm_config('knowledge_build', max_tokens=2048)

    assert config.api_key == 'build-key'
    assert config.base_url == 'https://api.aaccx.pw/v1'
    assert config.model == 'gpt-5.4'
    assert config.small_model == 'gpt-5.4'
    assert config.max_tokens == 2048


def test_runtime_gateway_maps_errors_with_runtime_provider(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        'DIALOG_PROVIDER=cliproxyapi\n'
        'DIALOG_API_KEY=dialog-key\n',
        encoding='utf-8',
    )
    service = ModelConfigService(env_path=env_path)
    gateway = ModelRuntimeGateway(
        model_config_service_instance=service,
        client_factory=lambda *, api_key, base_url: FakeOpenAIClient(api_key=api_key, base_url=base_url),
    )

    runtime = gateway.get_runtime('dialog')
    mapped_error = runtime.map_error(Exception('401 invalid api key'))

    assert mapped_error.error_code == 'MODEL_API_AUTH_FAILED'
    assert mapped_error.provider == 'cliproxyapi'
