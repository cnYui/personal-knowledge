from __future__ import annotations

import json
from dataclasses import dataclass, field
from inspect import isawaitable
from typing import Any, Callable


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
        event_callback: Callable[[dict[str, Any]], None] | None = None,
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
                if event_callback is not None:
                    query = str(arguments.get('query') or '').strip()
                    detail = query and f'使用查询“{query}”发起知识图谱检索。' or '发起知识图谱检索。'
                    event_callback(
                        {
                            'type': 'timeline',
                            'id': f'tool-round-{round_index + 1}',
                            'kind': 'retrieval',
                            'title': f'检索第 {round_index + 1} 轮',
                            'detail': detail,
                            'status': 'started',
                        }
                    )
                try:
                    result = await self._call_tool(tool_impl, arguments)
                    step.result = result
                    self._append_tool_history(history, tool_call=tool_call, result=result)
                    if event_callback is not None:
                        retrieved_edge_count = result.get('retrieved_edge_count') if isinstance(result, dict) else None
                        has_enough_evidence = result.get('has_enough_evidence') if isinstance(result, dict) else None
                        empty_reason = result.get('empty_reason') if isinstance(result, dict) else None
                        query = str(arguments.get('query') or '').strip()
                        detail = query and f'使用查询“{query}”发起知识图谱检索。' or '发起知识图谱检索。'
                        if retrieved_edge_count is not None:
                            detail = detail.rstrip('。') + f' 命中 {retrieved_edge_count} 条图谱证据。'
                        if has_enough_evidence is True:
                            detail += ' 当前证据已足够。'
                        elif has_enough_evidence is False and empty_reason:
                            detail += f' 当前证据仍不足：{empty_reason}'
                        elif has_enough_evidence is False:
                            detail += ' 当前证据仍不足。'
                        preview_items: list[str] = []
                        preview_total = 0
                        if isinstance(result, dict):
                            references = result.get('references')
                            if isinstance(references, list):
                                preview_total = len(references)
                                for reference in references[:3]:
                                    if isinstance(reference, dict):
                                        preview = (
                                            reference.get('fact')
                                            or reference.get('summary')
                                            or reference.get('name')
                                            or reference.get('type')
                                        )
                                        if preview:
                                            preview_items.append(str(preview))
                        event_callback(
                            {
                                'type': 'timeline',
                                'id': f'tool-round-{round_index + 1}',
                                'kind': 'retrieval',
                                'title': f'检索第 {round_index + 1} 轮',
                                'detail': detail,
                                'status': 'done',
                                'preview_items': preview_items,
                                'preview_total': preview_total,
                            }
                        )
                except Exception as exc:
                    step.error = str(exc)
                    self._append_tool_history(history, tool_call=tool_call, result={'error': str(exc)})
                    if event_callback is not None:
                        event_callback(
                            {
                                'type': 'timeline',
                                'id': f'tool-round-{round_index + 1}',
                                'kind': 'retrieval',
                                'title': f'检索第 {round_index + 1} 轮',
                                'detail': f'检索执行失败：{exc}',
                                'status': 'error',
                            }
                        )
                steps.append(step)

        return ToolLoopResult(
            answer='',
            history=history,
            rounds_used=self.max_rounds,
            steps=steps,
            exceeded_max_rounds=True,
        )
