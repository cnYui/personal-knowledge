# Agentic RAG V2 Upgrade Design

## Goal

Upgrade the current Agentic RAG in `personal-knowledge-base` toward the `v2` fusion flow defined in [agentic-rag-flow-v2.md](/d:/CodeWorkSpace/ragflow/docs/agentic-rag-flow-v2.md), while keeping the MVP safe:

- no external API changes
- no response schema changes
- no frontend consumption changes
- minimum-risk internal upgrade first

The upgrade will be delivered in three versions:

1. `MVP`
2. `V2`
3. `V3`

## Current State

The current system already has several strong building blocks:

- `AgentKnowledgeProfileService.compose_system_prompt()` injects knowledge profile overlay into the agent prompt.
- `AgentNode` already supports:
  - `graph_retrieval_tool`
  - `graph_history_tool`
  - `ToolLoopEngine`
  - `direct_general_answer`
  - `kb_grounded_answer`
  - `kb_plus_general_answer`
- `ChatService` already performs unified citation and trace postprocessing.

However, the current chat canvas is still:

- `Begin -> Agent -> Message`

and the system does not yet have an explicit first-step `pre-retrieval probe` decision phase matching the desired `v2` flow.

## Desired Target

The final target flow is:

1. normalize question
2. attach knowledge profile overlay
3. run one lightweight pre-retrieval probe
4. branch by probe result:
   - `no_hit` or `weak_hit` -> retry once -> direct fallback if still weak
   - `insufficient` -> enter multi-round tool loop
   - `sufficient` -> answer directly from evidence
5. unify citation and trace output

The key principle is:

- overlay guides
- probe judges
- tool loop supplements
- real evidence decides groundedness

## Version Plan

## Version 1: MVP

### Objective

Add the `overlay + pre-retrieval probe + three-way decision` flow with the smallest possible internal change set.

### Scope

Keep all external behavior stable:

- do not change API routes
- do not change response payload shape
- do not change frontend protocol
- do not change `chat_agentic_rag.json`

Only change internal orchestration inside:

- [agent_node.py](/d:/CodeWorkSpace/personal-knowledge-base/backend/app/workflow/nodes/agent_node.py)
- optionally minor prompt additions in [agent_prompts.py](/d:/CodeWorkSpace/personal-knowledge-base/backend/app/services/agent_prompts.py)
- tests for agent execution and trace behavior

### MVP Runtime Flow

Inside `AgentNode.execute()`:

1. normalize query
2. extract focus points
3. compose system prompt with knowledge profile overlay
4. run first pre-retrieval probe using `graph_retrieval_tool`
5. classify the probe result:
   - `no_hit`
   - `insufficient`
   - `sufficient`
6. if `no_hit`, retry probe once using focus-point rewritten query
7. branch:
   - if still `no_hit` after retry -> `direct_general_answer`
   - if `sufficient` -> `kb_grounded_answer`
   - if `insufficient` -> enter current `ToolLoopEngine`
8. if tool loop still cannot produce enough evidence -> `kb_plus_general_answer`
9. continue to the existing citation and trace output path

### MVP Classification Rules

To minimize risk, the MVP uses existing `GraphRetrievalResult` semantics:

- `sufficient`
  - `has_enough_evidence == True`

- `no_hit`
  - no references, or
  - `retrieved_edge_count <= 0`, or
  - empty/near-empty context while `has_enough_evidence == False`

- `insufficient`
  - some evidence exists
  - but `has_enough_evidence == False`

This avoids schema redesign in the MVP.

### MVP Internal Additions

Add internal helper methods to `AgentNode`:

- `_run_probe(query, canvas, group_id) -> GraphRetrievalResult`
- `_classify_probe_result(result) -> str`
- `_retry_probe_with_focus_points(query, focus_points, canvas, group_id) -> GraphRetrievalResult`
- `_answer_from_grounded_probe(query, retrieval_result) -> str`
- lightweight helper(s) for emitting probe timeline events

These methods should keep `execute()` readable and prevent probe logic from being mixed directly into tool-loop logic.

### MVP Trace and Timeline

Add explicit probe semantics to trace and runtime timeline:

- `probe_retrieve`
- `probe_retry`
- `probe_grounded`
- `enter_tool_loop`

Existing answer actions remain:

- `answer_directly`
- `answer_from_kb`
- `fallback_to_general_llm`

The frontend response format remains unchanged, but trace should now clearly show:

- initial evidence probe
- optional retry
- direct grounded answer vs tool loop vs fallback

### MVP Tests

Add or update tests to verify:

1. probe sufficient -> direct grounded answer
2. probe no hit -> retry no hit -> direct general answer
3. probe no hit -> retry insufficient -> enter tool loop
4. probe insufficient -> tool loop still insufficient -> `kb_plus_general_answer`
5. citation and fallback flags remain correct

Primary test focus:

- [test_agent_node.py](/d:/CodeWorkSpace/personal-knowledge-base/backend/tests/workflow/nodes/test_agent_node.py)

Secondary if needed:

- `ChatService` integration behavior

## Version 2

### Objective

Refactor the validated MVP probe logic into an explicit canvas node.

### Scope

Change the canvas structure from:

- `Begin -> Agent -> Message`

to:

- `Begin -> Retrieval -> Agent -> Message`

### V2 Changes

- strengthen [retrieval_node.py](/d:/CodeWorkSpace/personal-knowledge-base/backend/app/workflow/nodes/retrieval_node.py) into a true `pre-retrieval probe` node
- update [chat_agentic_rag.json](/d:/CodeWorkSpace/personal-knowledge-base/backend/app/workflow/templates/chat_agentic_rag.json)
- pass structured probe output into `AgentNode`
- let `AgentNode` consume probe results instead of probing by itself

### V2 Output Contract

The retrieval node should expose structured probe data such as:

- `hit`
- `evidence_strength`
- `retrieved_edge_count`
- `top_references`
- `probe_reason`

These can remain internal canvas variables at this stage and do not need to change public API payloads.

### V2 Benefits

- clearer node responsibility separation
- cleaner tests
- easier future A/B experiments
- architecture becomes closer to the documented `v2` flow

## Version 3

### Objective

Deliver the full fusion architecture with stronger evidence policy and cleaner long-term extensibility.

### V3 Changes

- upgrade overlay from plain prompt injection into a more explicit structured navigation layer
- improve probe scoring beyond simple boolean sufficiency
- add stronger query rewrite and focus-point decomposition rules
- support more explicit coordination between:
  - `graph_retrieval_tool`
  - `graph_history_tool`
  - optional future external tools
- unify evidence accumulation and final groundedness judgment across:
  - initial probe
  - tool-loop retrieval rounds
  - history tool results

### V3 Result

At V3, the system should behave like a complete fusion-style Agentic RAG:

- the model knows the likely shape of the knowledge base
- the system validates that belief through real evidence
- the tool loop supplements only when needed
- fallback remains honest and traceable

## Risks

### MVP Risks

- probe classification may be too coarse for some edge cases
- focus-point retry may occasionally underperform compared with a dedicated query rewrite model
- merging probe evidence and tool-loop evidence must avoid duplicate trace or duplicate references

### V2 Risks

- moving probe into a separate node may temporarily destabilize internal canvas variable flow
- node boundaries must remain simple, otherwise V2 becomes premature refactoring

### V3 Risks

- stronger routing logic can overcomplicate the agent if not kept evidence-first
- future tool expansion may blur the line between navigation hints and real evidence

## Decision Rules

To keep the system stable across all versions:

- real retrieval evidence always has higher priority than overlay hints
- overlay can influence whether to search and how to search
- overlay must never count as proof
- fallback text must remain explicit when evidence is insufficient

## Recommended Delivery Order

1. ship MVP first
2. verify behavior and regression safety
3. move to V2 only after MVP is stable
4. move to V3 only after V2 node boundaries are validated

## Success Criteria

### MVP Success

- no API contract changes
- no frontend breakage
- probe flow works
- direct/grounded/fallback branches are traceable

### V2 Success

- retrieval probe is a real node
- agent node becomes simpler
- canvas path reflects the architecture clearly

### V3 Success

- the system behaves like a complete fusion Agentic RAG
- evidence handling is explicit, reliable, and extensible

