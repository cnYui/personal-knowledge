"""Prompt configuration API endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.prompt import PromptConfig, PromptConfigUpdate
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
