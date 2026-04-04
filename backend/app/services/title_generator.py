"""
Title generation service using StepFun API.

Generates concise titles for memory content using LLM.
"""

import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.model_errors import map_model_api_error, missing_api_key_error
from app.services.model_config_service import ModelConfigService, model_config_service

logger = logging.getLogger(__name__)


class TitleGenerator:
    """Service for generating memory titles using StepFun API."""

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
            logger.error(
                'TitleGenerator client initialization failed: missing dialog API key for provider=%s',
                config.provider,
            )
            raise missing_api_key_error(provider=config.provider, purpose='对话模型')

        logger.info(
            'Refreshing TitleGenerator client: provider=%s, model=%s, base_url=%s',
            config.provider,
            config.model,
            config.base_url,
        )
        try:
            self.client = AsyncOpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
            )
            self.model = config.model
            self._runtime_signature = signature
        except Exception as error:
            logger.error('TitleGenerator client initialization failed: %s', error, exc_info=True)
            raise

    async def generate_title(self, content: str) -> Optional[str]:
        """
        Generate a concise title for the given content.

        Args:
            content: The memory content to generate a title for

        Returns:
            Generated title string, or None if generation fails
        """
        try:
            self._ensure_client()
            # Truncate content if too long (keep first 500 characters)
            truncated_content = content[:500] if len(content) > 500 else content

            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            'role': 'system',
                            'content': '你是一个专业的标题生成助手。根据用户提供的内容,生成一个简洁、准确的标题(不超过30个字)。只返回标题文本,不要有任何其他内容。',
                        },
                        {
                            'role': 'user',
                            'content': f'请为以下内容生成一个简洁的标题:\n\n{truncated_content}',
                        },
                    ],
                    temperature=0.7,
                    max_tokens=50,
                )
            except Exception as error:
                provider = self.model_config_service.get_dialog_config().provider
                raise map_model_api_error(error, provider=provider) from error

            title = response.choices[0].message.content
            if title:
                # Clean up the title
                title = title.strip().strip('"').strip("'")
                # Limit to 255 characters (database constraint)
                title = title[:255]
                logger.info(f'Generated title: {title}')
                return title

            return None

        except Exception as e:
            logger.error(f'Failed to generate title: {e}')
            raise
