"""Text optimization API endpoints."""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.text_optimizer import text_optimizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/text', tags=['text'])


class TextOptimizationRequest(BaseModel):
    """Request model for text optimization."""

    text: str = Field(..., min_length=1, description='Text to optimize')


class TextOptimizationResponse(BaseModel):
    """Response model for text optimization."""

    optimized_text: str = Field(..., description='Optimized text')
    original_length: int = Field(..., description='Original text length')
    optimized_length: int = Field(..., description='Optimized text length')


@router.post('/optimize', response_model=TextOptimizationResponse)
async def optimize_text(request: TextOptimizationRequest):
    """
    Optimize text content using LLM.

    This endpoint cleans and normalizes text by:
    - Removing filler words and speech disfluencies
    - Normalizing punctuation and numbers
    - Correcting technical terminology
    """
    logger.info('API: Text optimization request received')
    logger.info(f'API: Original text length: {len(request.text)}')
    logger.info(f'API: Text preview: {request.text[:100]}...')
    
    optimized = await text_optimizer.optimize_text(request.text)

    if optimized is None:
        logger.warning('API: Optimization returned None, using original text')
        # If optimization fails, return original text
        optimized = request.text
    else:
        logger.info(f'API: Optimization successful, new length: {len(optimized)}')

    return TextOptimizationResponse(
        optimized_text=optimized,
        original_length=len(request.text),
        optimized_length=len(optimized),
    )
