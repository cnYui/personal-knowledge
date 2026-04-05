# Warning Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the project-owned FastAPI lifecycle deprecation warnings and eliminate or narrowly suppress the third-party `graphiti-core` Pydantic warning while keeping focused backend tests passing.

**Architecture:** Replace `FastAPI.on_event()` startup/shutdown hooks in `backend/app/main.py` with a single async lifespan context manager that preserves existing startup and shutdown sequencing. Then evaluate whether `graphiti-core` can be safely upgraded; if not, add a narrowly targeted pytest warning filter for the known third-party warning only.

**Tech Stack:** Python 3.12, FastAPI, pytest, Pydantic v2, graphiti-core, PowerShell, pip

---

### File Map

**Modify:**
- `backend/app/main.py` — replace deprecated FastAPI lifecycle hooks with lifespan.
- `backend/requirements.txt` — optionally bump `graphiti-core` if a safe version exists.
- `backend/pytest.ini` — add a narrowly scoped warning filter only if dependency upgrade cannot safely remove the warning.

**Verify:**
- `backend/tests/workers/test_graphiti_ingest_worker.py`
- `backend/tests/services/test_graph_retrieval_tool.py`
- `backend/tests/repositories/test_memory_graph_episode_repository.py`
- `backend/tests/test_models.py`

### Task 1: Replace deprecated FastAPI lifecycle hooks with lifespan

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/workers/test_graphiti_ingest_worker.py`

- [ ] **Step 1: Snapshot the current warning baseline**

Run:

```powershell
Set-Location 'd:\CodeWorkSpace\personal-knowledge-base\backend'; python -m pytest tests/workers/test_graphiti_ingest_worker.py tests/services/test_graph_retrieval_tool.py tests/repositories/test_memory_graph_episode_repository.py tests/test_models.py -q
```

Expected:

- Tests pass.
- Warning output includes FastAPI `on_event` deprecation warnings from `backend/app/main.py`.

- [ ] **Step 2: Write the lifespan-based replacement in `backend/app/main.py`**

Replace the current `FastAPI(...)` app construction and `@app.on_event()` handlers with this structure:

```python
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app import dependencies
from app.core.database import SessionLocal, init_db
from app.core.model_errors import ModelAPIError
from app.routers.chat import router as chat_router
from app.routers.daily_review import router as daily_review_router
from app.routers.graph import router as graph_router
from app.routers.memories import router as memories_router
from app.routers.prompts import router as prompts_router
from app.routers.settings import router as settings_router
from app.routers.text_optimization import router as text_router
from app.routers.uploads import router as uploads_router
from app.services.memory_service import MemoryService
from app.workers import GraphitiIngestWorker
from app.workers.title_generation_worker import title_generation_worker


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info('Application startup sequence started.')

    try:
        logger.info('Startup step 1/3: initializing GraphitiIngestWorker.')
        dependencies.graphiti_worker = GraphitiIngestWorker()
        await dependencies.graphiti_worker.start()
        logger.info('Startup step 1/3 complete: GraphitiIngestWorker started.')

        memory_service = MemoryService()
        db = SessionLocal()
        try:
            logger.info('Startup step 2/3: recovering pending graph ingestion tasks.')
            recovered_count = await memory_service.recover_pending_graph_tasks(db, dependencies.graphiti_worker)
            logger.info('Startup step 2/3 complete: recovered_count=%s', recovered_count)
        finally:
            db.close()

        logger.info('Startup step 3/3: starting title generation worker.')
        await title_generation_worker.start()
        logger.info('Startup step 3/3 complete: title generation worker started.')
        logger.info('Application startup complete, all startup stages succeeded.')

        yield
    finally:
        logger.info('Application shutdown sequence started.')

        if dependencies.graphiti_worker:
            try:
                logger.info('Shutdown step 1/2: stopping GraphitiIngestWorker.')
                await dependencies.graphiti_worker.stop()
                try:
                    await asyncio.wait_for(dependencies.graphiti_worker.queue.join(), timeout=30.0)
                    logger.info('Shutdown step 1/2 complete: Graphiti queue drained successfully.')
                except asyncio.TimeoutError:
                    logger.warning('Graphiti queue did not drain within timeout, forcing shutdown.')
            except Exception as error:
                logger.error('Shutdown step 1/2 failed while stopping GraphitiIngestWorker: %s', error, exc_info=True)

        try:
            logger.info('Shutdown step 2/2: stopping title generation worker.')
            await title_generation_worker.stop()
            logger.info('Shutdown step 2/2 complete: title generation worker stopped.')
        except Exception as error:
            logger.error('Shutdown step 2/2 failed while stopping title generation worker: %s', error, exc_info=True)

        logger.info('Application shutdown complete.')


app = FastAPI(title='Personal Knowledge Base API', lifespan=lifespan)
```

Important implementation notes:

- Keep `init_db()` at module import time exactly as it is unless it blocks the change.
- Keep all existing routers, middleware, and exception handlers unchanged.
- Preserve the current startup/shutdown order and log messages as closely as possible.

- [ ] **Step 3: Run the focused tests after the lifespan refactor**

Run:

```powershell
Set-Location 'd:\CodeWorkSpace\personal-knowledge-base\backend'; python -m pytest tests/workers/test_graphiti_ingest_worker.py tests/services/test_graph_retrieval_tool.py tests/repositories/test_memory_graph_episode_repository.py tests/test_models.py -q
```

Expected:

- Tests still pass.
- FastAPI `on_event` deprecation warnings disappear.
- One remaining warning may still come from `graphiti-core`.

- [ ] **Step 4: Commit the lifecycle warning cleanup**

```bash
git add backend/app/main.py
git commit -m "refactor: replace fastapi event hooks with lifespan"
```

### Task 2: Attempt safe `graphiti-core` upgrade to remove the Pydantic warning

**Files:**
- Modify: `backend/requirements.txt`
- Verify: current virtual environment packages and targeted tests

- [ ] **Step 1: Inspect available `graphiti-core` versions**

Run:

```powershell
Set-Location 'd:\CodeWorkSpace\personal-knowledge-base\backend'; python -m pip index versions graphiti-core
```

Expected:

- Output lists available versions newer than or equal to `0.28.2`.

- [ ] **Step 2: If a newer version exists, update `backend/requirements.txt` minimally**

Change only this line if a newer safe candidate exists:

```text
graphiti-core==0.28.2
```

to:

```text
graphiti-core==<chosen_version>
```

Selection rules:

- Prefer the latest patch/minor version that does not require unrelated package churn.
- Do not change other dependency pins in the same step.

- [ ] **Step 3: Install the chosen version and verify import/test behavior**

Run:

```powershell
Set-Location 'd:\CodeWorkSpace\personal-knowledge-base\backend'; python -m pip install -r requirements.txt
```

Then run:

```powershell
Set-Location 'd:\CodeWorkSpace\personal-knowledge-base\backend'; python -m pytest tests/workers/test_graphiti_ingest_worker.py tests/services/test_graph_retrieval_tool.py tests/repositories/test_memory_graph_episode_repository.py tests/test_models.py -q
```

Expected:

- Installation succeeds without forcing unrelated major downgrades/upgrades.
- Tests pass.
- The `graphiti-core` Pydantic deprecation warning disappears if upstream fixed it.

- [ ] **Step 4: Commit the dependency upgrade if it removes the warning safely**

```bash
git add backend/requirements.txt
git commit -m "chore: upgrade graphiti-core to reduce deprecation warnings"
```

### Task 3: Add narrow pytest filtering if the third-party warning remains

**Files:**
- Modify: `backend/pytest.ini`
- Test: same focused pytest command

- [ ] **Step 1: Capture the exact remaining warning text after Task 2**

Run:

```powershell
Set-Location 'd:\CodeWorkSpace\personal-knowledge-base\backend'; python -m pytest tests/workers/test_graphiti_ingest_worker.py tests/services/test_graph_retrieval_tool.py tests/repositories/test_memory_graph_episode_repository.py tests/test_models.py -q
```

Expected:

- Only the third-party `graphiti_core.driver.search_interface.search_interface.py:22` Pydantic deprecation warning remains.

- [ ] **Step 2: Add a narrow warning filter to `backend/pytest.ini`**

Append a `filterwarnings` section like this, adjusting the regex only if the actual warning text differs:

```ini
[pytest]
markers =
    asyncio: marks tests that use asyncio (requires pytest-asyncio)
    integration: marks tests as integration tests (deselect with '-m "not integration"')
filterwarnings =
    ignore:Support for class-based `config` is deprecated, use ConfigDict instead\.:pydantic.warnings.PydanticDeprecatedSince20:graphiti_core\.driver\.search_interface\.search_interface
```

Requirements:

- Keep the existing markers unchanged.
- Filter only the known `graphiti-core` warning.
- Do not suppress all `DeprecationWarning` or all `PydanticDeprecatedSince20` warnings globally.

- [ ] **Step 3: Re-run the focused tests to verify warning output is clean**

Run:

```powershell
Set-Location 'd:\CodeWorkSpace\personal-knowledge-base\backend'; python -m pytest tests/workers/test_graphiti_ingest_worker.py tests/services/test_graph_retrieval_tool.py tests/repositories/test_memory_graph_episode_repository.py tests/test_models.py -q
```

Expected:

- Tests pass.
- Warning summary is empty, or at minimum no longer includes the known `graphiti-core` Pydantic warning.

- [ ] **Step 4: Commit the fallback warning filter if it was needed**

```bash
git add backend/pytest.ini
git commit -m "test: filter known third-party pydantic deprecation warning"
```

### Task 4: Final verification and handoff

**Files:**
- Verify only

- [ ] **Step 1: Run final regression verification**

Run:

```powershell
Set-Location 'd:\CodeWorkSpace\personal-knowledge-base\backend'; python -m pytest tests/workers/test_graphiti_ingest_worker.py tests/services/test_graph_retrieval_tool.py tests/repositories/test_memory_graph_episode_repository.py tests/test_models.py -q
```

Expected:

- All tests pass.
- No FastAPI lifecycle warnings remain.
- No visible `graphiti-core` Pydantic warning remains after either upgrade or targeted filtering.

- [ ] **Step 2: Inspect the final diff before handoff**

Run:

```bash
git diff -- backend/app/main.py backend/requirements.txt backend/pytest.ini docs/superpowers/specs/2026-04-05-warning-cleanup-design.md docs/superpowers/plans/2026-04-05-warning-cleanup-implementation-plan.md
```

Expected:

- Diff only contains lifecycle cleanup, optional dependency pin change, optional narrow warning filter, and documentation.

- [ ] **Step 3: Summarize the chosen path and any remaining caveats**

Include in handoff:

- Whether `graphiti-core` was upgraded or filtered.
- Final warning count from the focused pytest command.
- Any remaining risk if the third-party dependency warning was filtered rather than fixed upstream.