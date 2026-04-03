"""
Text optimization service using StepFun API.

Optimizes user input text by cleaning, normalizing, and correcting terminology.
"""

import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.model_errors import map_model_api_error, missing_api_key_error
from app.services.model_config_service import ModelConfigService, model_config_service
from app.services.prompt_config_service import prompt_config_service

logger = logging.getLogger(__name__)


class TextOptimizer:
    """Service for optimizing text content using LLM."""

    def __init__(
        self,
        *,
        model_config_service_instance: ModelConfigService | None = None,
    ):
        self.model_config_service = model_config_service_instance or model_config_service
        self.client: AsyncOpenAI | None = None
        self.model = 'deepseek-chat'
        self._runtime_signature: tuple[str, str, str, int] | None = None

    def _ensure_client(self) -> None:
        config = self.model_config_service.get_dialog_config()
        signature = (
            config.provider,
            config.api_key,
            config.base_url,
            self.model_config_service.version,
        )
        if self.client is not None and signature == self._runtime_signature:
            return

        if not config.api_key:
            raise missing_api_key_error(provider=config.provider, purpose='对话模型')

        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.model = config.model
        self._runtime_signature = signature

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
            self._ensure_client()
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

            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': text},
                    ],
                    temperature=0.3,  # Lower temperature for more consistent output
                    max_tokens=2048,
                )
            except Exception as error:
                provider = self.model_config_service.get_dialog_config().provider
                raise map_model_api_error(error, provider=provider) from error

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
            raise

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
