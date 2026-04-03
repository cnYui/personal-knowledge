from app.core.config import settings
from app.schemas.settings import ModelConfigUpdate
from app.services.model_config_service import ModelConfigService


def test_model_config_service_reads_masked_config_from_env(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        'DIALOG_API_KEY=dialog-secret-1234\n'
        'KNOWLEDGE_BUILD_API_KEY=build-secret-5678\n',
        encoding='utf-8',
    )

    original_dialog = settings.dialog_api_key
    original_build = settings.knowledge_build_api_key
    try:
        service = ModelConfigService(env_path=env_path)
        config = service.get_masked_config()

        assert config.dialog.api_key.configured is True
        assert config.dialog.api_key.masked_value.startswith('dial')
        assert config.dialog.api_key.masked_value.endswith('1234')
        assert config.knowledge_build.api_key.configured is True
        assert config.knowledge_build.api_key.masked_value.endswith('5678')
    finally:
        settings.dialog_api_key = original_dialog
        settings.knowledge_build_api_key = original_build


def test_model_config_service_update_config_persists_and_bumps_runtime_version(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text('', encoding='utf-8')

    original_dialog = settings.dialog_api_key
    original_build = settings.knowledge_build_api_key
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
        assert result.dialog.api_key.masked_value.endswith('load')
        assert 'DIALOG_API_KEY=dialog-hot-reload' in env_path.read_text(encoding='utf-8')
        assert 'DIALOG_PROVIDER=deepseek' in env_path.read_text(encoding='utf-8')
        assert 'DIALOG_BASE_URL=https://api.deepseek.com/v1' in env_path.read_text(encoding='utf-8')
        assert 'DIALOG_MODEL=deepseek-chat' in env_path.read_text(encoding='utf-8')
        assert 'KNOWLEDGE_BUILD_API_KEY=build-hot-reload' in env_path.read_text(encoding='utf-8')
        assert 'KNOWLEDGE_BUILD_PROVIDER=deepseek' in env_path.read_text(encoding='utf-8')
        assert 'KNOWLEDGE_BUILD_BASE_URL=https://api.deepseek.com/v1' in env_path.read_text(encoding='utf-8')
        assert 'KNOWLEDGE_BUILD_MODEL=deepseek-chat' in env_path.read_text(encoding='utf-8')
    finally:
        settings.dialog_api_key = original_dialog
        settings.knowledge_build_api_key = original_build


def test_model_config_service_update_config_preserves_unspecified_keys(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        'DIALOG_API_KEY=dialog-existing\n'
        'KNOWLEDGE_BUILD_API_KEY=build-existing\n',
        encoding='utf-8',
    )

    service = ModelConfigService(env_path=env_path)
    service.update_config(ModelConfigUpdate(dialog_api_key='dialog-updated'))

    assert service.get_dialog_config().api_key == 'dialog-updated'
    assert service.get_knowledge_build_config().api_key == 'build-existing'
