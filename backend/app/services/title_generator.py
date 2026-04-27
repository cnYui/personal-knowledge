"""
Title generation service using StepFun API.

Generates concise titles for memory content using LLM.
"""

import logging
from typing import Optional

from openai import AsyncOpenAI

from app.services.model_client_runtime import ModelRuntimeGateway, model_runtime_gateway
from app.services.model_config_service import ModelConfigService, model_config_service

logger = logging.getLogger(__name__)


class TitleGenerator:
    """Service for generating memory titles using StepFun API."""

    def __init__(
        self,
        *,
        model_config_service_instance: ModelConfigService | None = None,
        model_runtime_gateway_instance: ModelRuntimeGateway | None = None,
    ):
        self.model_config_service = model_config_service_instance or model_config_service
        self.model_runtime_gateway = model_runtime_gateway_instance or (
            ModelRuntimeGateway(model_config_service_instance=self.model_config_service)
            if model_config_service_instance is not None
            else model_runtime_gateway
        )
        self.client: AsyncOpenAI | None = None
        self.model = 'deepseek-chat'
        self.reasoning_effort = ''
        self.completion_extra: dict[str, str] = {}
        self._runtime_signature: tuple[str, str, str, str, str, str, int] | None = None

    def _ensure_client(self) -> None:
        runtime = self.model_runtime_gateway.get_runtime('dialog')
        if self.client is not None and runtime.signature == self._runtime_signature:
            return

        logger.info(
            'Refreshing TitleGenerator client: provider=%s, model=%s, base_url=%s',
            runtime.provider,
            runtime.model,
            runtime.base_url,
        )
        try:
            self.client = runtime.client
            self.model = runtime.model
            self.reasoning_effort = runtime.reasoning_effort
            self.completion_extra = runtime.completion_extra()
            self._runtime_signature = runtime.signature
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
                    **self.completion_extra,
                )
            except Exception as error:
                raise self.model_runtime_gateway.get_runtime('dialog').map_error(error) from error

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
