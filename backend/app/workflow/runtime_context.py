from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RuntimeContext:
    query: str = ''
    history: list[dict[str, Any]] = field(default_factory=list)
    files: list[Any] = field(default_factory=list)
    user_id: str | None = None
    globals: dict[str, Any] = field(default_factory=dict)
    node_outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.globals.setdefault('sys.query', self.query)
        self.globals.setdefault('sys.history', self.history)
        self.globals.setdefault('sys.files', self.files)
        self.globals.setdefault('sys.user_id', self.user_id)
        self.globals.setdefault(
            'sys.date',
            datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        )

    def set_query(self, query: str) -> None:
        self.query = query
        self.globals['sys.query'] = query

    def set_files(self, files: list[Any]) -> None:
        self.files = files
        self.globals['sys.files'] = files

    def set_user_id(self, user_id: str | None) -> None:
        self.user_id = user_id
        self.globals['sys.user_id'] = user_id

    def append_history(self, role: str, content: Any) -> None:
        item = {'role': role, 'content': content}
        self.history.append(item)
        self.globals['sys.history'] = self.history

    def set_global(self, key: str, value: Any) -> None:
        self.globals[key] = value

    def get_global(self, key: str, default: Any = None) -> Any:
        return self.globals.get(key, default)

    def set_node_output(self, node_id: str, output: Any) -> None:
        self.node_outputs[node_id] = output

    def get_node_output(self, node_id: str, default: Any = None) -> Any:
        return self.node_outputs.get(node_id, default)

    def snapshot(self) -> dict[str, Any]:
        return {
            'query': self.query,
            'history': list(self.history),
            'files': list(self.files),
            'user_id': self.user_id,
            'globals': dict(self.globals),
            'node_outputs': dict(self.node_outputs),
            'metadata': dict(self.metadata),
        }
