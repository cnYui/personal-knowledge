from fastapi import APIRouter

from app.schemas.settings import AgentKnowledgeProfileRead, ModelConfigRead, ModelConfigUpdate
from app.services.agent_knowledge_profile_service import agent_knowledge_profile_service
from app.services.model_config_service import model_config_service

router = APIRouter(prefix='/api/settings', tags=['settings'])


def _build_model_config_read() -> ModelConfigRead:
    profile = agent_knowledge_profile_service.get_latest_snapshot()
    knowledge_profile = AgentKnowledgeProfileRead(
        available=profile is not None,
        status=profile.status if profile is not None else 'missing',
        major_topics=profile.major_topics if profile is not None else [],
        high_frequency_entities=profile.high_frequency_entities if profile is not None else [],
        high_frequency_relations=profile.high_frequency_relations if profile is not None else [],
        recent_focuses=profile.recent_focuses if profile is not None else [],
        rendered_overlay=profile.rendered_overlay if profile is not None else '',
        updated_at=profile.updated_at if profile is not None else None,
        error_message=profile.error_message if profile is not None else None,
    )
    masked = model_config_service.get_masked_config()
    return ModelConfigRead(
        dialog=masked.dialog,
        knowledge_build=masked.knowledge_build,
        knowledge_profile=knowledge_profile,
    )


@router.get('/model-config', response_model=ModelConfigRead)
def get_model_config() -> ModelConfigRead:
    return _build_model_config_read()


@router.put('/model-config', response_model=ModelConfigRead)
def update_model_config(payload: ModelConfigUpdate) -> ModelConfigRead:
    model_config_service.update_config(payload)
    return _build_model_config_read()
