## Graph History V3 Minimal End-to-End Design

Date: 2026-04-09
Status: Draft for review

## 1. Goal

V3 extends graph history from the V2 entity-history MVP into a minimal end-to-end agent path that can answer relation-history, topic-history, and mixed current-plus-history questions.

The first V3 slice should design all three areas together:

1. relation/topic target resolution
2. history query planning
3. agent orchestration

But implementation should prioritize a single best-supported path:

- mixed questions that need both current state and historical change explanation

Example target questions:

- "A 和 B 现在是什么关系？之前怎么变成这样的？"
- "这个主题现在的情况是什么？最近是怎么演变的？"

## 2. Scope

### In scope

- Add a minimal `relation_topic` target path to graph history.
- Introduce a lightweight `HistoryQueryPlanner` that classifies questions into a small set of execution plans.
- Introduce a lightweight `GraphHistoryRelationTopicResolver` that resolves relation or topic targets from `target_value` and constraints.
- Extend agent orchestration so the agent can invoke `graph_history_tool` when a question requires history retrieval.
- Preserve the existing V2 memory/entity history behavior unchanged.

### Out of scope

- Broad natural-language understanding for arbitrary relation and topic phrasing.
- Multi-hop reasoning or multi-target decomposition.
- Large schema expansion for graph history results.
- Planner confidence scoring, retries, or dynamic multi-step replanning.
- Solving every relation-only and topic-only phrasing in the first version.

## 3. Chosen Approach

We will use a thin end-to-end approach.

That means all three V3 areas are designed together, but each is intentionally minimal:

- planner stays shallow
- resolver stays shallow
- orchestration adds only one main history branch

This approach is preferred over a planner-first or resolver-first sequence because the goal of V3 is not just lower-level capability. The goal is to prove the smallest complete user-visible path that lets the agent combine current retrieval with history evidence.

## 4. Primary User Path

The main path to optimize is:

1. user asks a mixed question
2. planner classifies it as `current_plus_history`
3. current retrieval obtains the present-state answer inputs
4. orchestration triggers `graph_history_tool`
5. graph history returns structured historical evidence
6. final answer composes current state plus historical evolution

This path should be better supported than relation-only or topic-only questions in the first V3 implementation.

Relation-only and topic-only questions are still in scope, but only at a minimum viable level.

## 5. Component Boundaries

### 5.1 `HistoryQueryPlanner`

Responsibility:

- classify the incoming question into one of three execution categories

Minimal output:

- `current_only`
- `history_only`
- `current_plus_history`

Rules for the first version:

- It does not perform deep semantic parsing.
- It does not decide detailed target structures.
- It only determines whether orchestration needs current retrieval, history retrieval, or both.

### 5.2 `GraphHistoryRelationTopicResolver`

Responsibility:

- resolve a `relation_topic` request into either a relation target or a topic target

Minimal output shape:

- relation target: source entity, target entity, optional relation type
- topic target: topic scope or normalized topic identity

Rules for the first version:

- The resolver accepts `target_value` plus optional `constraints`.
- If sufficient relation constraints are present, it resolves as `relation`.
- Otherwise it resolves as `topic`.
- Ambiguity should prefer warnings over introducing additional status codes in V3 phase 1.

### 5.3 Agent orchestration

Responsibility:

- use the planner output to decide whether to invoke history retrieval
- combine current retrieval output and history evidence in a single response path

Minimal orchestration addition:

- one new branch for history-aware execution
- if planner says history is needed, orchestration prepares and calls `graph_history_tool`
- final composition remains centralized in the agent response path

This keeps orchestration intentionally thin and avoids introducing a second complex control system.

## 6. Data Flow

The V3 minimal data flow is:

1. user question enters the agent
2. planner classifies the question as `current_only`, `history_only`, or `current_plus_history`
3. orchestration executes:
   - `current_only`: current retrieval path only
   - `history_only`: graph history path only
   - `current_plus_history`: current retrieval first, then graph history retrieval, then compose
4. when history is needed, orchestration constructs a `graph_history_tool` call using:
   - `target_type = relation_topic`
   - `target_value`
   - `constraints`
5. `GraphHistoryTool` forwards the request into `GraphHistoryService`
6. `GraphHistoryService` uses `GraphHistoryRelationTopicResolver`
7. service returns a unified `GraphHistoryResult`
8. agent composes the final answer from current-state context plus history evidence

## 7. Result Contract and Error Handling

V3 phase 1 should continue using the existing unified result model rather than introducing a parallel schema.

Primary statuses used in this slice:

- `ok`
- `not_found`
- `insufficient_history`
- `insufficient_evidence`
- `unsupported_target_type`
- `error`

Design decision:

- do not add a dedicated ambiguity status for V3 phase 1
- ambiguous or weakly resolved situations should primarily surface through `warnings`

Rationale:

- This minimizes schema churn after V2.
- It keeps the first relation/topic slice compatible with the current tool and service result expectations.
- It avoids overfitting the contract before real usage patterns are observed.

## 8. Constraints Handling

The `constraints` field is the main bridge between orchestration and relation/topic history queries.

Expected first-phase usage:

- relation constraints:
  - `source_entity`
  - `target_entity`
  - `relation_type` (optional)
- topic constraints:
  - `topic_scope`

The first version should keep this dictionary shallow and explicit instead of introducing nested planning payloads.

## 9. Testing Strategy

V3 phase 1 testing should be layered.

### Unit tests

- `HistoryQueryPlanner`
  - mixed question -> `current_plus_history`
  - explicit history question -> `history_only`
  - present-state-only question -> `current_only`
- `GraphHistoryRelationTopicResolver`
  - relation constraints present -> relation target
  - no relation constraints -> topic target

### Service tests

- `GraphHistoryService` supports `relation_topic` target routing
- unsupported or insufficient inputs map cleanly into result statuses/warnings

### Tool tests

- `GraphHistoryTool` accepts `relation_topic`
- forwards constraints correctly

### Workflow/orchestration tests

- agent path invokes history retrieval when planner classifies `current_plus_history`
- final flow supports a mixed question path end-to-end at the orchestration level

## 10. Implementation Sequence

Recommended implementation order:

1. stabilize the existing prototype files into the chosen contracts
2. extend service/tool/schema support for `relation_topic` in the minimal shape
3. connect planner output into agent orchestration
4. add orchestration tests for the mixed path
5. verify that V2 memory/entity behavior remains unchanged

## 11. Risks and Mitigations

### Risk: planner becomes too smart too early

Mitigation:

- keep planner classification-only
- do not move target parsing into the planner

### Risk: resolver contract drifts from agent/tool expectations

Mitigation:

- keep all history outputs normalized through `GraphHistoryResult`
- keep constraints explicit and shallow

### Risk: orchestration duplicates logic from existing retrieval flow

Mitigation:

- add one minimal history-aware branch only
- reuse existing answer composition patterns where possible

### Risk: relation/topic ambiguity explodes schema complexity

Mitigation:

- use warnings first
- postpone dedicated ambiguity lifecycle until usage justifies it

## 12. Success Criteria

V3 phase 1 is successful when:

1. the agent can follow a mixed current-plus-history path for relation/topic questions
2. `relation_topic` requests flow through tool -> service -> resolver -> unified result model
3. planner, resolver, tool, service, and orchestration each have focused tests
4. existing V2 memory/entity behavior remains green

## 13. Summary

V3 phase 1 should not attempt a full semantic history system. It should prove one thin end-to-end path:

- classify the question simply
- resolve relation/topic simply
- invoke history retrieval only when needed
- compose current state plus historical evidence in one answer

This keeps the design aligned with the user's goal: design all three V3 areas together, but implement a single minimal usable chain first.