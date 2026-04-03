from fastapi import APIRouter

from app.schemas.settings import ModelConfigRead, ModelConfigUpdate
from app.services.model_config_service import model_config_service

router = APIRouter(prefix='/api/settings', tags=['settings'])


@router.get('/model-config', response_model=ModelConfigRead)
def get_model_config() -> ModelConfigRead:
    return model_config_service.get_masked_config()


@router.put('/model-config', response_model=ModelConfigRead)
def update_model_config(payload: ModelConfigUpdate) -> ModelConfigRead:
    return model_config_service.update_config(payload)
