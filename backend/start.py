"""Legacy-compatible startup wrapper for the FastAPI backend.

The real application entrypoint is ``app.main:app``.
This script intentionally mirrors the documented uvicorn command so local
development does not accidentally fall back to the old SQLite bootstrap path.
"""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    os.environ.setdefault("PYTHONPATH", os.getcwd())
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
