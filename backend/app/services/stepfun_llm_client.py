"""
StepFun LLM Client for Graphiti.

This client adapts StepFun's OpenAI-compatible API to work with Graphiti's
LLM client interface. StepFun uses standard chat.completions API instead of
the responses.parse API used by OpenAI's reasoning models.
"""

import json
import logging
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from graphiti_core.llm_client.config import LLMConfig, ModelSize
from graphiti_core.llm_client.openai_base_client import BaseOpenAIClient
from graphiti_core.prompts.models import Message

logger = logging.getLogger(__name__)


class StepFunLLMClient(BaseOpenAIClient):
    """
    StepFun LLM Client for Graphiti integration.

    This client uses StepFun's standard chat.completions API with JSON mode
    instead of OpenAI's responses.parse API.
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        cache: bool = False,
    ):
        """Initialize StepFun LLM client."""
        if config is None:
            config = LLMConfig()

        # Use max_tokens from config, or default to a safe value for step-1-8k
        max_tokens = config.max_tokens if config.max_tokens else 2048

        super().__init__(config, cache, max_tokens, reasoning=None, verbosity=None)

        self.client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)
        logger.info(
            f'StepFunLLMClient initialized with base_url={config.base_url}, '
            f'max_tokens={max_tokens}'
        )

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int | None = None,
        model_size: ModelSize = ModelSize.medium,
    ) -> tuple[dict[str, Any], int, int]:
        """
        Override to force using self.max_tokens when max_tokens is not provided.

        This ensures StepFun's token limits are respected even when graphiti
        internal calls don't specify max_tokens.
        """
        # Force use of self.max_tokens if max_tokens is not explicitly provided
        # or if it exceeds our configured limit
        if max_tokens is None or max_tokens > self.max_tokens:
            max_tokens = self.max_tokens
            logger.debug(f'Using configured max_tokens: {max_tokens}')

        return await super()._generate_response(messages, response_model, max_tokens, model_size)

    async def _create_structured_completion(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        temperature: float | None,
        max_tokens: int,
        response_model: type[BaseModel],
        reasoning: str | None = None,
        verbosity: str | None = None,
    ):
        """
        Create a structured completion using StepFun's chat.completions API.

        StepFun uses standard OpenAI-compatible API with JSON mode, not responses.parse.
        """
        # Add system message to request JSON output matching the response model
        schema = response_model.model_json_schema()
        json_instruction = (
            f'You must respond with valid JSON matching this schema: {json.dumps(schema)}. '
            f'Do not include any text outside the JSON object.'
        )

        # Prepend JSON instruction to messages
        enhanced_messages = [
            {'role': 'system', 'content': json_instruction},
            *messages,
        ]

        # Call StepFun API with JSON mode
        response = await self.client.chat.completions.create(
            model=model,
            messages=enhanced_messages,  # type: ignore
            temperature=temperature if temperature is not None else 0.7,
            max_tokens=max_tokens,
            response_format={'type': 'json_object'},
        )

        # Parse the JSON response into the response model
        content = response.choices[0].message.content
        if not content:
            raise ValueError('Empty response from StepFun API')

        try:
            parsed_data = json.loads(content)
            parsed_object = response_model.model_validate(parsed_data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f'Failed to parse StepFun response: {content}')
            raise ValueError(f'Invalid JSON response from StepFun: {e}') from e

        # Create a mock response object that matches OpenAI's response format
        # This allows BaseOpenAIClient to process it correctly
        class MockResponse:
            def __init__(self, parsed_obj: BaseModel, usage: Any):
                # Store the parsed object as JSON string for compatibility
                self.output_text = parsed_obj.model_dump_json()
                self.usage = usage

            def model_dump(self):
                return {'output_text': self.output_text, 'usage': self.usage}

        return MockResponse(parsed_object, response.usage)

    async def _create_completion(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        temperature: float | None,
        max_tokens: int,
        response_model: type[BaseModel] | None = None,
        reasoning: str | None = None,
        verbosity: str | None = None,
    ):
        """Create a regular completion with JSON format."""
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature if temperature is not None else 0.7,
            max_tokens=max_tokens,
            response_format={'type': 'json_object'},
        )
