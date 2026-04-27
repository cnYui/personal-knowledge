from app.core.config import settings
from app.schemas.settings import ModelConfigUpdate
from app.services.model_config_service import ModelConfigService


def _snapshot_runtime_settings():
    field_names = (
        'dialog_provider',
        'dialog_api_key',
        'dialog_base_url',
        'dialog_model',
        'dialog_reasoning_effort',
        'knowledge_build_provider',
        'knowledge_build_api_key',
        'knowledge_build_base_url',
        'knowledge_build_model',
        'knowledge_build_reasoning_effort',
    )
    return {field_name: getattr(settings, field_name) for field_name in field_names}


def _restore_runtime_settings(snapshot: dict[str, str]):
    for field_name, value in snapshot.items():
        setattr(settings, field_name, value)


def test_model_config_service_reads_masked_config_from_env(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        'DIALOG_API_KEY=dialog-secret-1234\n'
        'DIALOG_REASONING_EFFORT=\n'
        'KNOWLEDGE_BUILD_API_KEY=build-secret-5678\n'
        'KNOWLEDGE_BUILD_REASONING_EFFORT=\n',
        encoding='utf-8',
    )

    original_settings = _snapshot_runtime_settings()
    try:
        service = ModelConfigService(env_path=env_path)
        config = service.get_masked_config()

        assert config.dialog.api_key.configured is True
        assert config.dialog.api_key.masked_value.startswith('dial')
        assert config.dialog.api_key.masked_value.endswith('1234')
        assert config.dialog.reasoning_effort == ''
        assert config.knowledge_build.api_key.configured is True
        assert config.knowledge_build.api_key.masked_value.endswith('5678')
        assert config.knowledge_build.reasoning_effort == ''
    finally:
        _restore_runtime_settings(original_settings)


def test_model_config_service_update_config_persists_and_bumps_runtime_version(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        'DIALOG_PROVIDER=openai\n'
        'DIALOG_BASE_URL=https://api.openai.com/v1\n'
        'DIALOG_MODEL=gpt-4o-mini\n'
        'DIALOG_REASONING_EFFORT=high\n'
        'KNOWLEDGE_BUILD_PROVIDER=openai\n'
        'KNOWLEDGE_BUILD_BASE_URL=https://api.openai.com/v1\n'
        'KNOWLEDGE_BUILD_MODEL=gpt-4o-mini\n'
        'KNOWLEDGE_BUILD_REASONING_EFFORT=medium\n',
        encoding='utf-8',
    )

    original_settings = _snapshot_runtime_settings()
    try:
        service = ModelConfigService(env_path=env_path)
        previous_version = service.version

        result = service.update_config(
            ModelConfigUpdate(
                dialog_api_key='dialog-hot-reload',
                knowledge_build_api_key='build-hot-reload',
            )
        )

        assert service.version == previous_version + 1
        assert service.get_dialog_config().api_key == 'dialog-hot-reload'
        assert service.get_knowledge_build_config().api_key == 'build-hot-reload'
        assert service.get_dialog_config().reasoning_effort == 'high'
        assert service.get_knowledge_build_config().reasoning_effort == 'medium'
        assert result.dialog.api_key.masked_value.endswith('load')
        env_content = env_path.read_text(encoding='utf-8')
        assert 'DIALOG_API_KEY=dialog-hot-reload' in env_content
        assert 'KNOWLEDGE_BUILD_API_KEY=build-hot-reload' in env_content
        # Saving API keys should not overwrite provider/base_url/model/reasoning settings.
        assert 'DIALOG_PROVIDER=openai' in env_content
        assert 'DIALOG_BASE_URL=https://api.openai.com/v1' in env_content
        assert 'DIALOG_MODEL=gpt-4o-mini' in env_content
        assert 'DIALOG_REASONING_EFFORT=high' in env_content
        assert 'KNOWLEDGE_BUILD_PROVIDER=openai' in env_content
        assert 'KNOWLEDGE_BUILD_BASE_URL=https://api.openai.com/v1' in env_content
        assert 'KNOWLEDGE_BUILD_MODEL=gpt-4o-mini' in env_content
        assert 'KNOWLEDGE_BUILD_REASONING_EFFORT=medium' in env_content
    finally:
        _restore_runtime_settings(original_settings)


def test_model_config_service_update_config_preserves_unspecified_keys(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        'DIALOG_API_KEY=dialog-existing\n'
        'KNOWLEDGE_BUILD_API_KEY=build-existing\n',
        encoding='utf-8',
    )

    original_settings = _snapshot_runtime_settings()
    try:
        service = ModelConfigService(env_path=env_path)
        service.update_config(ModelConfigUpdate(dialog_api_key='dialog-updated'))

        assert service.get_dialog_config().api_key == 'dialog-updated'
        assert service.get_knowledge_build_config().api_key == 'build-existing'
    finally:
        _restore_runtime_settings(original_settings)


def test_model_config_service_update_config_supports_full_runtime_fields(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text('', encoding='utf-8')

    original_settings = _snapshot_runtime_settings()
    try:
        service = ModelConfigService(env_path=env_path)

        service.update_config(
            ModelConfigUpdate(
                dialog_provider='cliproxyapi',
                dialog_base_url='https://api.aaccx.pw/v1',
                dialog_model='gpt-5.4',
                dialog_reasoning_effort='xhigh',
                dialog_api_key='dialog-proxy-key',
                knowledge_build_provider='cliproxyapi',
                knowledge_build_base_url='https://api.aaccx.pw/v1',
                knowledge_build_model='gpt-5.4',
                knowledge_build_reasoning_effort='xhigh',
                knowledge_build_api_key='build-proxy-key',
            )
        )

        dialog_config = service.get_dialog_config()
        knowledge_build_config = service.get_knowledge_build_config()

        assert dialog_config.provider == 'cliproxyapi'
        assert dialog_config.base_url == 'https://api.aaccx.pw/v1'
        assert dialog_config.model == 'gpt-5.4'
        assert dialog_config.reasoning_effort == 'xhigh'
        assert dialog_config.api_key == 'dialog-proxy-key'

        assert knowledge_build_config.provider == 'cliproxyapi'
        assert knowledge_build_config.base_url == 'https://api.aaccx.pw/v1'
        assert knowledge_build_config.model == 'gpt-5.4'
        assert knowledge_build_config.reasoning_effort == 'xhigh'
        assert knowledge_build_config.api_key == 'build-proxy-key'
    finally:
        _restore_runtime_settings(original_settings)
