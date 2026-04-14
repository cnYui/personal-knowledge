# Graph History V2/V3 Mainline Port Design

## Background

The main workspace currently contains a V1 graph history implementation centered on `memory` targets. A separate worktree, `.worktrees/graph-history-v2-v3/`, contains in-progress V2/V3 code for entity history, relation/topic history, planner-based orchestration, and related tests, but those changes have not been merged into the main workspace.

The goal of this design is to bring the missing V2 and V3 minimal functionality into the main workspace by selectively porting and adapting the worktree implementation instead of rebuilding from scratch.

## Scope

This design covers two phases implemented in order:

1. **V2 completion**
   - Extend graph history schema for entity targets and richer statuses
   - Add entity resolver and entity aggregator services
   - Extend repositories with entity-oriented lookup helpers
   - Extend `GraphHistoryService` with entity timeline / compare / summarize support
   - Expose `graph_history_tool` in agent tool schemas
   - Add service and tool tests for entity history

2. **V3 minimal end-to-end**
   - Add history query planner for `current_only`, `history_only`, and `current_plus_history`
   - Add relation/topic resolver
   - Extend `GraphHistoryService` with minimal `relation_topic` support
   - Wire `graph_history_tool` into agent orchestration and canvas factory
   - Add orchestration and service tests for minimal V3 behavior

Out of scope for this pass:

- Richer V3 composer layers beyond minimal end-to-end support
- Extra schema fields such as `turning_points`, `confidence`, or `evidence_groups` unless required to keep compatibility with the minimal design
- Unrelated refactors outside graph history and agent orchestration

## Approach Options

### Option A — Selective port from worktree with adaptation (**recommended**)

Copy the proven V2/V3 building blocks from `.worktrees/graph-history-v2-v3/` into the main workspace, then adapt imports, interfaces, and tests to match the current mainline state.

**Pros**
- Fastest path to a working result
- Reuses already explored implementation ideas
- Lowest product risk because tests already exist in the worktree

**Cons**
- Requires careful diff review to avoid bringing in unfinished behavior
- Mainline and worktree differences may still require local fixes

### Option B — Rebuild from mainline using specs only

Implement everything directly from the design docs without using worktree code.

**Pros**
- Maximum control over code shape
- Can be cleaner in theory

**Cons**
- Slowest path
- Highest regression risk
- Duplicates work already present in the worktree

### Option C — Port only V2 now, defer V3 to a later cycle

Ship entity history first, then separately design and port V3 minimal.

**Pros**
- Lower immediate scope
- Easier verification

**Cons**
- Does not satisfy the current request to complete both missing areas
- Leaves agent orchestration incomplete

## Recommended Architecture

### Phase 1: V2 entity history

#### Schema

Update `backend/app/schemas/agent.py` so that:

- `GraphHistoryResolvedTarget` can represent both memory and entity targets
- `GraphHistoryResult.status` includes entity-related states such as `ambiguous_target` and `insufficient_evidence`
- Existing V1 memory behavior remains backward compatible

#### Repository helpers

Extend repository helpers needed by entity history:

- `MemoryRepository`
  - list memory ids by entity keyword
  - list memory references by entity keyword
  - list memory rows by entity keyword
- `MemoryGraphEpisodeRepository`
  - list versions across multiple memories
  - count grouped versions across multiple memories

#### Services

Add:

- `GraphHistoryEntityResolver`
  - resolves canonical entity names and aliases
  - returns `ok`, `not_found`, or `ambiguous_target`
- `GraphHistoryEntityAggregator`
  - collects entity-related events across memories and versions
  - supports counting and top-k truncation

Extend `GraphHistoryService` to route `entity` queries through those services and return:

- timeline results
- compare results
- summarize results
- entity-specific status transitions

#### Tool and workflow exposure

Keep `GraphHistoryTool` thin, but update its contract and ensure agent schemas expose it as a callable tool.

### Phase 2: V3 minimal

#### Query planning

Add `HistoryQueryPlanner` with minimal intent classification:

- `current_only`
- `history_only`
- `current_plus_history`

This planner is heuristic and intentionally lightweight.

#### Relation/topic resolution

Add `GraphHistoryRelationTopicResolver` to map `relation_topic` requests into a conservative resolved target with warnings where needed. This pass favors safe minimal behavior over broad inference.

#### Service routing

Extend `GraphHistoryService` with a `relation_topic` branch that returns minimal structured history output and warnings when evidence is weak.

#### Agent orchestration

Update `AgentNode` to:

- expose both retrieval and history tools
- use the planner to decide when history is needed
- support `current_only`, `history_only`, and `current_plus_history` behavior
- preserve existing retrieval-first behavior for non-history questions

Update `CanvasFactory` to inject `graph_history_tool` into agent nodes.

## Data Flow

### V2 entity flow

1. Agent or service receives `graph_history_tool(target_type='entity', ...)`
2. `GraphHistoryService` calls `GraphHistoryEntityResolver`
3. Resolver returns canonical entity info or an error state
4. Aggregator gathers matching memory/version events
5. Service maps aggregated events into timeline/compare/summarize output
6. Tool returns structured result to caller

### V3 minimal flow

1. Agent receives user query
2. Planner classifies query as current-only, history-only, or mixed
3. Agent calls graph retrieval, graph history, or both depending on the plan
4. Agent composes final answer using current evidence, history evidence, or both

## Error Handling

The implementation must preserve explicit structured statuses rather than hiding failures inside free-form text.

### V2 statuses

- `not_found`
- `ambiguous_target`
- `insufficient_history`
- `insufficient_evidence`
- `unsupported_target_type`
- `ok`

### V3 minimal behavior

- weak relation/topic queries may still return structured results with warnings
- unsupported combinations should fail conservatively
- planner misclassification should degrade to existing retrieval behavior rather than crash

## Testing Strategy

### V2 tests

- entity resolver unit tests
- entity aggregator unit tests
- graph history service tests for entity timeline/compare/summarize and error states
- graph history tool passthrough tests

### V3 tests

- planner unit tests
- relation/topic resolver unit tests
- graph history service tests for relation/topic routing
- workflow orchestration tests for planner-driven tool usage

### Verification target

Run focused backend tests for graph history services, tools, and workflow orchestration. Fix any integration mismatches introduced by the port.

## File Plan

### Files to update

- `backend/app/schemas/agent.py`
- `backend/app/repositories/memory_repository.py`
- `backend/app/repositories/memory_graph_episode_repository.py`
- `backend/app/services/graph_history_service.py`
- `backend/app/services/agent_tools/graph_history_tool.py`
- `backend/app/workflow/nodes/agent_node.py`
- `backend/app/workflow/canvas_factory.py`
- `backend/tests/services/test_graph_history_service.py`
- `backend/tests/services/test_graph_history_tool.py`

### Files to add

- `backend/app/services/graph_history_entity_resolver.py`
- `backend/app/services/graph_history_entity_aggregator.py`
- `backend/app/services/graph_history_relation_topic_resolver.py`
- `backend/app/services/history_query_planner.py`
- `backend/tests/services/test_graph_history_entity_resolver.py`
- `backend/tests/services/test_graph_history_entity_aggregator.py`
- `backend/tests/services/test_graph_history_relation_topic_resolver.py`
- `backend/tests/services/test_history_query_planner.py`
- `backend/tests/workflow/test_agent_history_orchestration.py`

## Risks and Mitigations

### Risk: worktree code is incomplete

Mitigation: treat worktree as a source of building blocks, not as a blind copy target. Keep behavior limited to the documented minimal scope and verify with tests.

### Risk: agent orchestration changes could regress existing graph retrieval behavior

Mitigation: preserve current retrieval path as the default and add history behavior behind planner decisions and explicit tool schemas.

### Risk: schema expansion could break existing clients

Mitigation: only add fields and status values; avoid removing or renaming existing fields.

## Success Criteria

The work is complete when:

1. Main workspace supports `memory`, `entity`, and minimal `relation_topic` graph history queries.
2. Agent workflow can expose and use `graph_history_tool` in the main workspace.
3. Planner-driven minimal mixed current/history flow is covered by tests.
4. Focused graph history tests pass in the main workspace.