from fastapi.testclient import TestClient

import app.routers.settings as settings_router
from app.main import app
from app.schemas.settings import ModelConfigRead, ModelConfigUpdate, RuntimeModelConfigStatus, ApiKeyFieldStatus


def _build_response(dialog_mask: str, build_mask: str) -> ModelConfigRead:
    return ModelConfigRead(
        dialog=RuntimeModelConfigStatus(
            provider='deepseek',
            base_url='https://api.deepseek.com/v1',
            model='deepseek-chat',
            api_key=ApiKeyFieldStatus(configured=bool(dialog_mask), masked_value=dialog_mask),
        ),
        knowledge_build=RuntimeModelConfigStatus(
            provider='deepseek',
            base_url='https://api.deepseek.com/v1',
            model='deepseek-chat',
            api_key=ApiKeyFieldStatus(configured=bool(build_mask), masked_value=build_mask),
        ),
    )


def test_get_model_config_returns_masked_runtime_config(monkeypatch):
    def fake_get_masked_config():
        return _build_response('dial****1234', 'buil****5678')

    monkeypatch.setattr(settings_router.model_config_service, 'get_masked_config', fake_get_masked_config)
    client = TestClient(app)

    response = client.get('/api/settings/model-config')

    assert response.status_code == 200
    assert response.json() == {
        'dialog': {
            'provider': 'deepseek',
            'base_url': 'https://api.deepseek.com/v1',
            'model': 'deepseek-chat',
            'api_key': {'configured': True, 'masked_value': 'dial****1234'},
        },
        'knowledge_build': {
            'provider': 'deepseek',
            'base_url': 'https://api.deepseek.com/v1',
            'model': 'deepseek-chat',
            'api_key': {'configured': True, 'masked_value': 'buil****5678'},
        },
    }


def test_put_model_config_updates_and_returns_masked_runtime_config(monkeypatch):
    call_log = []

    def fake_update_config(payload: ModelConfigUpdate):
        call_log.append(payload)
        return _build_response('dial****4321', 'buil****8765')

    monkeypatch.setattr(settings_router.model_config_service, 'update_config', fake_update_config)
    client = TestClient(app)

    response = client.put(
        '/api/settings/model-config',
        json={
            'dialog_api_key': 'dialog-secret-4321',
            'knowledge_build_api_key': 'build-secret-8765',
        },
    )

    assert response.status_code == 200
    assert call_log == [
        ModelConfigUpdate(
            dialog_api_key='dialog-secret-4321',
            knowledge_build_api_key='build-secret-8765',
        )
    ]
    assert response.json()['dialog']['api_key']['masked_value'] == 'dial****4321'
    assert response.json()['knowledge_build']['api_key']['masked_value'] == 'buil****8765'
