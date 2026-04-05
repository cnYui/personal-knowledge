## Warning Cleanup Design

### Goal

Reduce the current backend test warning output as much as safely possible by:

1. Removing project-owned FastAPI deprecation warnings.
2. Attempting to remove the third-party `graphiti-core` Pydantic deprecation warning through a safe dependency upgrade.
3. Falling back to narrowly scoped pytest warning filtering only if the third-party warning cannot be safely removed.

### Current Warning Sources

#### 1. FastAPI lifecycle deprecation warnings

Current source:

- `backend/app/main.py`
- `@app.on_event('startup')`
- `@app.on_event('shutdown')`

Reason:

Newer FastAPI versions prefer the `lifespan` API over `on_event` handlers.

Impact:

- Produces four warnings during the current targeted test run.
- Project-owned and should be fixed in code rather than suppressed.

#### 2. Pydantic deprecation warning from `graphiti-core`

Current source:

- Installed dependency: `graphiti-core==0.28.2`
- Warning references class-based Pydantic `Config`, deprecated in Pydantic v2.

Reason:

The dependency appears to still use Pydantic v1-style configuration in at least one model.

Impact:

- Produces one warning during test execution.
- Originates from a third-party package, so it should be handled cautiously.

### Proposed Approach

#### Step 1: Replace FastAPI event handlers with lifespan

Refactor `backend/app/main.py` so startup and shutdown work move into a single async lifespan context manager.

Requirements:

- Preserve existing startup ordering:
  1. Start `GraphitiIngestWorker`
  2. Recover pending graph ingestion tasks
  3. Start `title_generation_worker`
- Preserve existing shutdown ordering:
  1. Stop `GraphitiIngestWorker`
  2. Wait for queue drain with timeout and warning behavior
  3. Stop `title_generation_worker`
- Preserve existing logging behavior and error reporting as closely as practical.

Expected result:

- FastAPI deprecation warnings disappear without changing runtime behavior.

#### Step 2: Check for a safe `graphiti-core` upgrade path

Inspect available package versions and, if a newer compatible version is available, upgrade `graphiti-core` in `backend/requirements.txt`.

Upgrade criteria:

- No broad dependency churn unless required.
- Existing focused tests continue to pass.
- The Pydantic warning disappears or is reduced.

Expected result:

- If upstream has already fixed the deprecated Pydantic usage, the warning is removed cleanly.

#### Step 3: Fallback to targeted pytest filtering if upgrade is not safe

If no safe upgrade path is available, add a precise `filterwarnings` entry in `backend/pytest.ini` that suppresses only the known third-party deprecation warning.

Requirements:

- Do not suppress all deprecation warnings globally.
- Match the known source/message narrowly enough that new project warnings remain visible.

Expected result:

- Test output is clean while preserving useful warning visibility for project code.

### Verification Plan

Run the current focused regression command:

`python -m pytest tests/workers/test_graphiti_ingest_worker.py tests/services/test_graph_retrieval_tool.py tests/repositories/test_memory_graph_episode_repository.py tests/test_models.py -q`

Success criteria:

- All tests pass.
- FastAPI `on_event` warnings are gone.
- `graphiti-core` warning is either removed by upgrade or narrowly filtered if no safe upgrade exists.

### Scope Boundaries

Included:

- `backend/app/main.py`
- `backend/requirements.txt`
- `backend/pytest.ini`
- Verification of current focused backend tests

Excluded:

- Broad dependency upgrades unrelated to warning cleanup
- Refactors outside lifecycle handling and warning management
- Suppressing unrelated warnings