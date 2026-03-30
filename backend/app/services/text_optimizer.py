"""
Text optimization service using StepFun API.

Optimizes user input text by cleaning, normalizing, and correcting terminology.
"""

import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.prompt_config_service import prompt_config_service

logger = logging.getLogger(__name__)


class TextOptimizer:
    """Service for optimizing text content using LLM."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = 'step-1-8k'

    async def optimize_text(self, text: str, custom_prompt: str | None = None) -> Optional[str]:
        """
        Optimize text content using LLM.

        Args:
            text: The original text to optimize
            custom_prompt: Optional custom system prompt (uses configured prompt if None)

        Returns:
            Optimized text string, or None if optimization fails
        """
        if not text or not text.strip():
            return text

        try:
            # Use custom prompt if provided, otherwise get from config
            system_prompt = custom_prompt or prompt_config_service.get_prompt('text_optimization')

            if not system_prompt:
                logger.error('No system prompt available for text optimization')
                return None

            logger.info('=== Text Optimization Debug ===')
            logger.info(f'System prompt length: {len(system_prompt)}')
            logger.info(f'System prompt preview (first 200 chars): {system_prompt[:200]}...')
            logger.info(f'System prompt preview (last 200 chars): ...{system_prompt[-200:]}')
            logger.info(f'Input text length: {len(text)}')
            logger.info(f'Input text preview: {text[:100]}...')

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': text},
                ],
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=2048,
            )

            optimized_text = response.choices[0].message.content
            if optimized_text:
                optimized_text = optimized_text.strip()
                
                # Post-process: Remove markdown if prompt requests it
                if 'markdown' in system_prompt.lower() and '去除' in system_prompt:
                    logger.info('Applying markdown removal post-processing')
                    optimized_text = self._remove_markdown(optimized_text)
                
                logger.info(f'Text optimized: {len(text)} -> {len(optimized_text)} chars')
                logger.info(f'Optimized text preview: {optimized_text[:200]}...')
                return optimized_text

            return None

        except Exception as e:
            logger.error(f'Failed to optimize text: {e}')
            return None

    def _remove_markdown(self, text: str) -> str:
        """Remove common markdown formatting from text."""
        import re
        
        # Remove bold/italic
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*(.+?)\*', r'\1', text)      # *italic*
        text = re.sub(r'__(.+?)__', r'\1', text)      # __bold__
        text = re.sub(r'_(.+?)_', r'\1', text)        # _italic_
        
        # Remove headers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`(.+?)`', r'\1', text)
        
        # Remove links
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        
        # Remove list markers
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        return text


# Global instance
text_optimizer = TextOptimizer()
