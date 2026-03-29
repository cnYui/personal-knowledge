from pathlib import Path
from uuid import uuid4


def save_upload(upload_dir: str, filename: str, content: bytes) -> str:
    target_dir = Path(upload_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{uuid4()}-{filename}"
    target_path.write_bytes(content)
    return str(target_path)
