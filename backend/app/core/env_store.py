from __future__ import annotations

from pathlib import Path


class EnvStore:
    """Simple line-preserving .env reader/writer for local project settings."""

    def __init__(self, env_path: str | Path) -> None:
        self.env_path = Path(env_path)

    def read(self) -> dict[str, str]:
        if not self.env_path.exists():
            return {}

        values: dict[str, str] = {}
        for line in self.env_path.read_text(encoding='utf-8').splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip()
        return values

    def update(self, updates: dict[str, str]) -> None:
        normalized_updates = {key: str(value) for key, value in updates.items()}
        existing_lines: list[str] = []
        if self.env_path.exists():
            existing_lines = self.env_path.read_text(encoding='utf-8').splitlines()

        updated_lines: list[str] = []
        touched_keys: set[str] = set()

        for line in existing_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or '=' not in line:
                updated_lines.append(line)
                continue

            key, _ = line.split('=', 1)
            normalized_key = key.strip()
            if normalized_key in normalized_updates:
                updated_lines.append(f'{normalized_key}={normalized_updates[normalized_key]}')
                touched_keys.add(normalized_key)
            else:
                updated_lines.append(line)

        missing_keys = [key for key in normalized_updates if key not in touched_keys]
        if missing_keys and updated_lines and updated_lines[-1].strip():
            updated_lines.append('')

        for key in missing_keys:
            updated_lines.append(f'{key}={normalized_updates[key]}')

        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        self.env_path.write_text('\n'.join(updated_lines).rstrip() + '\n', encoding='utf-8')
