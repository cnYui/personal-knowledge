"""
Title generation service using StepFun API.

Generates concise titles for memory content using LLM.
"""

import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class TitleGenerator:
    """Service for generating memory titles using StepFun API."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = 'step-1-8k'  # StepFun model

    async def generate_title(self, content: str) -> Optional[str]:
        """
        Generate a concise title for the given content.

        Args:
            content: The memory content to generate a title for

        Returns:
            Generated title string, or None if generation fails
        """
        try:
            # Truncate content if too long (keep first 500 characters)
            truncated_content = content[:500] if len(content) > 500 else content

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
            return None
