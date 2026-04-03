from app.core.model_errors import ModelAPIError, map_model_api_error, missing_api_key_error


def test_missing_api_key_error_returns_user_facing_payload():
    error = missing_api_key_error(provider='deepseek', purpose='对话模型')

    assert error.error_code == 'MODEL_API_KEY_MISSING'
    assert error.status_code == 400
    assert error.provider == 'deepseek'
    assert error.retryable is False
    assert '尚未配置 API Key' in error.message


def test_map_model_api_error_detects_quota_exhaustion():
    source_error = Exception('402 insufficient quota for this account')

    error = map_model_api_error(source_error, provider='deepseek')

    assert isinstance(error, ModelAPIError)
    assert error.error_code == 'MODEL_API_QUOTA_EXCEEDED'
    assert error.status_code == 402
    assert error.provider == 'deepseek'
    assert error.retryable is False


def test_map_model_api_error_detects_network_failure():
    source_error = Exception('connection timeout while reaching upstream')

    error = map_model_api_error(source_error, provider='deepseek')

    assert error.error_code == 'MODEL_API_NETWORK_ERROR'
    assert error.status_code == 503
    assert error.retryable is True
