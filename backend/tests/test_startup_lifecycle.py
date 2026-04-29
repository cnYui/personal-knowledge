from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app import dependencies
from app import main as main_module


@pytest.mark.anyio
async def test_lifespan_must_start_graphiti_worker_after_recovery_and_title_worker(monkeypatch):
    events: list[str] = []

    class FakeDb:
        def close(self):
            events.append('db_close')

    class FakeMemoryService:
        async def recover_pending_graph_tasks(self, db, worker):
            events.append('recover_pending')
            assert isinstance(db, FakeDb)
            assert worker is fake_worker
            return 0

    class FakeWorker:
        def __init__(self):
            self.running = False
            self.queue = SimpleNamespace(join=AsyncMock(return_value=None))

        async def start(self):
            events.append('graphiti_start')
            self.running = True

        async def stop(self):
            events.append('graphiti_stop')
            self.running = False

    fake_worker = FakeWorker()

    async def fake_title_start():
        events.append('title_start')

    async def fake_title_stop():
        events.append('title_stop')

    monkeypatch.setattr(main_module, 'GraphitiIngestWorker', lambda: fake_worker)
    monkeypatch.setattr(main_module, 'MemoryService', lambda: FakeMemoryService())
    monkeypatch.setattr(main_module, 'SessionLocal', lambda: FakeDb())
    monkeypatch.setattr(
        main_module,
        'title_generation_worker',
        SimpleNamespace(start=fake_title_start, stop=fake_title_stop),
    )
    dependencies.graphiti_worker = None

    async with main_module.lifespan(main_module.app):
        assert dependencies.graphiti_worker is fake_worker

    assert events[:3] == ['recover_pending', 'db_close', 'title_start']
    assert 'graphiti_start' in events[3:]
