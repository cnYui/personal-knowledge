"""Prompt configuration API endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.prompt import (
    ComposedPromptResponse,
    KnowledgeProfileResponse,
    PromptConfig,
    PromptConfigUpdate,
)
from app.services.agent_knowledge_profile_service import agent_knowledge_profile_service
from app.services.agent_prompts import STRICT_AGENT_SYSTEM_PROMPT
from app.services.prompt_config_service import prompt_config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/prompts', tags=['prompts'])


@router.get('', response_model=dict[str, PromptConfig])
async def get_all_prompts():
    """Get all prompt configurations."""
    logger.info('API: Getting all prompts')
    prompts_data = prompt_config_service.get_all_prompts()
    logger.info(f'API: Returning {len(prompts_data)} prompts')

    return {
        key: PromptConfig(
            key=key, content=data['content'], description=data['description']
        )
        for key, data in prompts_data.items()
    }


@router.get('/knowledge-profile', response_model=KnowledgeProfileResponse)
async def get_knowledge_profile():
    """Get the current knowledge profile that augments the system prompt.
    
    This profile is automatically generated from the knowledge graph and
    recent memories, and is used to enhance the agent's awareness of
    available knowledge topics.
    """
    logger.info('API: Getting knowledge profile')
    snapshot = agent_knowledge_profile_service.get_latest_snapshot()
    
    if snapshot is None:
        logger.info('API: No knowledge profile found')
        return KnowledgeProfileResponse(
            status='not_initialized',
            major_topics=[],
            high_frequency_entities=[],
            high_frequency_relations=[],
            recent_focuses=[],
            rendered_overlay='',
            updated_at=None,
            error_message=None,
        )
    
    logger.info(f'API: Returning knowledge profile, status={snapshot.status}')
    return KnowledgeProfileResponse(
        status=snapshot.status,
        major_topics=snapshot.major_topics,
        high_frequency_entities=snapshot.high_frequency_entities,
        high_frequency_relations=snapshot.high_frequency_relations,
        recent_focuses=snapshot.recent_focuses,
        rendered_overlay=snapshot.rendered_overlay,
        updated_at=snapshot.updated_at,
        error_message=snapshot.error_message,
    )


@router.get('/composed-system-prompt', response_model=ComposedPromptResponse)
async def get_composed_system_prompt():
    """Get the fully composed system prompt including knowledge profile overlay.
    
    This shows how the base system prompt is combined with the dynamic
    knowledge profile to create the final prompt used by the agent.
    """
    logger.info('API: Getting composed system prompt')
    snapshot = agent_knowledge_profile_service.get_latest_ready_snapshot()
    
    base_prompt = STRICT_AGENT_SYSTEM_PROMPT
    overlay = snapshot.rendered_overlay if snapshot else ''
    composed = agent_knowledge_profile_service.compose_system_prompt(base_prompt)
    
    logger.info(f'API: Returning composed prompt, overlay_length={len(overlay)}')
    return ComposedPromptResponse(
        base_prompt=base_prompt,
        overlay=overlay,
        composed_prompt=composed,
        profile_status=snapshot.status if snapshot else None,
    )


@router.get('/{key}', response_model=PromptConfig)
async def get_prompt(key: str):
    """Get a specific prompt configuration."""
    logger.info(f'API: Getting prompt: {key}')
    content = prompt_config_service.get_prompt(key)

    if content is None:
        logger.warning(f'API: Prompt not found: {key}')
        raise HTTPException(status_code=404, detail=f'Prompt not found: {key}')

    prompts_data = prompt_config_service.get_all_prompts()
    description = prompts_data.get(key, {}).get('description', '')

    logger.info(f'API: Returning prompt {key}, length: {len(content)}')
    return PromptConfig(key=key, content=content, description=description)


@router.put('/{key}', response_model=PromptConfig)
async def update_prompt(key: str, payload: PromptConfigUpdate):
    """Update a prompt configuration."""
    logger.info(f'API: Updating prompt: {key}')
    logger.info(f'API: New content length: {len(payload.content)}')
    success = prompt_config_service.update_prompt(key, payload.content)

    if not success:
        logger.error(f'API: Failed to update prompt: {key}')
        raise HTTPException(
            status_code=400, detail=f'Failed to update prompt: {key}'
        )

    logger.info(f'API: Successfully updated prompt: {key}')
    return await get_prompt(key)


@router.post('/{key}/reset', response_model=PromptConfig)
async def reset_prompt(key: str):
    """Reset a prompt to its default value."""
    logger.info(f'API: Resetting prompt: {key}')
    success = prompt_config_service.reset_prompt(key)

    if not success:
        logger.error(f'API: Failed to reset prompt: {key}')
        raise HTTPException(status_code=400, detail=f'Failed to reset prompt: {key}')

    logger.info(f'API: Successfully reset prompt: {key}')
    return await get_prompt(key)


