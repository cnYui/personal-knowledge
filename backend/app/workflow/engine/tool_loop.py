from __future__ import annotations

import json
from dataclasses import dataclass, field
from inspect import isawaitable
from typing import Any


@dataclass
class ToolLoopStep:
    round_index: int
    tool_name: str
    arguments: dict[str, Any]
    result: Any = None
    error: str | None = None


@dataclass
class ToolLoopResult:
    answer: str
    history: list[dict[str, Any]]
    rounds_used: int
    steps: list[ToolLoopStep] = field(default_factory=list)
    exceeded_max_rounds: bool = False


class ToolLoopEngine:
    def __init__(self, llm_client: Any, *, max_rounds: int = 5, model: str = 'step-1-8k') -> None:
        self.llm_client = llm_client
        self.max_rounds = max_rounds
        self.model = model

    async def _create_completion(
        self,
        *,
        history: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
        completion_kwargs: dict[str, Any],
    ) -> Any:
        response = self.llm_client.chat.completions.create(
            model=self.model,
            messages=history,
            tools=tool_schemas,
            tool_choice='auto',
            **completion_kwargs,
        )
        if isawaitable(response):
            response = await response
        return response

    async def _call_tool(self, tool_impl: Any, arguments: dict[str, Any]) -> Any:
        if hasattr(tool_impl, 'run'):
            result = tool_impl.run(**arguments)
        else:
            result = tool_impl(**arguments)
        if isawaitable(result):
            result = await result
        return result

    def _append_tool_history(
        self,
        history: list[dict[str, Any]],
        *,
        tool_call: Any,
        result: Any,
    ) -> None:
        history.append(
            {
                'role': 'assistant',
                'tool_calls': [
                    {
                        'id': tool_call.id,
                        'type': 'function',
                        'function': {
                            'name': tool_call.function.name,
                            'arguments': tool_call.function.arguments,
                        },
                    }
                ],
            }
        )
        if isinstance(result, dict):
            content = json.dumps(result, ensure_ascii=False)
        else:
            content = str(result)
        history.append(
            {
                'role': 'tool',
                'tool_call_id': tool_call.id,
                'content': content,
            }
        )

    async def run(
        self,
        *,
        messages: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
        tool_registry: dict[str, Any],
        system_prompt: str | None = None,
        completion_kwargs: dict[str, Any] | None = None,
    ) -> ToolLoopResult:
        history = [*messages]
        if system_prompt and (not history or history[0].get('role') != 'system'):
            history.insert(0, {'role': 'system', 'content': system_prompt})

        completion_kwargs = completion_kwargs or {}
        steps: list[ToolLoopStep] = []

        for round_index in range(self.max_rounds + 1):
            response = await self._create_completion(
                history=history,
                tool_schemas=tool_schemas,
                completion_kwargs=completion_kwargs,
            )
            message = response.choices[0].message
            tool_calls = getattr(message, 'tool_calls', None) or []

            if not tool_calls:
                return ToolLoopResult(
                    answer=str(getattr(message, 'content', '') or ''),
                    history=history,
                    rounds_used=round_index,
                    steps=steps,
                )

            if round_index >= self.max_rounds:
                return ToolLoopResult(
                    answer='',
                    history=history,
                    rounds_used=round_index,
                    steps=steps,
                    exceeded_max_rounds=True,
                )

            for tool_call in tool_calls:
                try:
                    arguments = json.loads(tool_call.function.arguments or '{}')
                except json.JSONDecodeError:
                    arguments = {}

                tool_name = tool_call.function.name
                tool_impl = tool_registry[tool_name]
                step = ToolLoopStep(
                    round_index=round_index,
                    tool_name=tool_name,
                    arguments=arguments,
                )
                try:
                    result = await self._call_tool(tool_impl, arguments)
                    step.result = result
                    self._append_tool_history(history, tool_call=tool_call, result=result)
                except Exception as exc:
                    step.error = str(exc)
                    self._append_tool_history(history, tool_call=tool_call, result={'error': str(exc)})
                steps.append(step)

        return ToolLoopResult(
            answer='',
            history=history,
            rounds_used=self.max_rounds,
            steps=steps,
            exceeded_max_rounds=True,
        )
