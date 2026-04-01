# RAGFlow Style Multi-Hop Agent Design

## Background

The current `personal-knowledge-base` chat flow already has several RAGFlow-inspired pieces:

- `Canvas`
- `AgentNode`
- `ToolLoopEngine`
- `ReferenceStore`
- `CitationPostProcessor`

However, the current runtime is still a hybrid design rather than a true RAGFlow-style multi-hop agent.

Today, the chat path mixes three decision styles:

1. local keyword shortcuts such as `CHITCHAT_PREFIXES`
2. an explicit planner that emits `direct / retrieve / decompose`
3. a partial tool loop used only after planner routing

This means the system is not yet using the same core mechanism as RAGFlow, where the agent itself decides in each round whether to call tools again, rewrite the query, continue searching, or stop and answer.

The goal of this project is to remove the current hybrid routing and replace it with a single, RAGFlow-style execution model:

- one `AgentNode`
- one tool: `graph_retrieval_tool`
- one tool loop
- one shared evidence pool
- one citation post-processing step

## Problem Statement

The current implementation differs from RAGFlow in several important ways:

1. It performs local keyword-based short-circuiting before the model sees the query.
2. It uses an explicit planning JSON layer instead of letting the model decide tool use round by round.
3. Multi-step retrieval for complex questions is currently pre-planned by code, not dynamically produced by the agent loop.
4. The UI trace partially reflects planner logic instead of true tool-loop reasoning.

This leads to several issues:

- some inputs, such as `你好`, never enter a genuine agent decision loop
- the runtime feels rule-driven rather than agent-driven
- the current flow is harder to compare directly with RAGFlow
- future expansion to additional tools would inherit planner-oriented technical debt

## Goal

Refactor the current chat workflow into a true RAGFlow-style multi-hop agent while keeping the existing `Canvas`, `ReferenceStore`, and citation architecture.

The new runtime should:

- remove local keyword-based routing as the main control mechanism
- remove the explicit `direct / retrieve / decompose` planner JSON layer
- let the model decide, inside the tool loop, whether to:
  - answer directly
  - call `graph_retrieval_tool`
  - call `graph_retrieval_tool` again with a revised query
  - stop and produce a final answer
- continue writing all retrieval evidence into `ReferenceStore`
- continue performing answer-final citation post-processing from the evidence pool
- keep the chat workflow running through `Canvas`

## Non-Goals

This project does not aim to:

- add more tools beyond `graph_retrieval_tool`
- build a visual workflow editor
- add MCP tool integration
- add multi-agent delegation
- implement sentence-level citation alignment
- redesign the entire chat UI

Those can be revisited later, but they are intentionally out of scope for this refactor.

## Target Architecture

The new architecture should be:

```text
User input
-> ChatService
-> CanvasFactory
-> Canvas.run()
-> BeginNode
-> AgentNode
-> ToolLoopEngine
-> graph_retrieval_tool (0..N times)
-> ReferenceStore accumulation
-> final answer
-> CitationPostProcessor
-> MessageNode
```

Key principle:

The system should have only one main decision-maker for multi-hop behavior: the agent inside the tool loop.

## Behavioral Model

### Current Flow

The current flow is effectively:

```text
input
-> local keyword shortcut
-> optional planner
-> optional retrieval / optional decomposition
-> answer
```

### New Flow

The new flow should be:

```text
input
-> agent prompt + history
-> tool loop round 1
-> optional retrieval
-> optional retrieval again
-> optional retrieval again
-> final answer
-> citation post-process
```

No separate planner JSON route should remain in the main path.

## Component Decisions

### 1. Canvas

`Canvas` remains the runtime container and does not need architectural replacement.

It continues to be responsible for:

- workflow execution order
- node lifecycle
- runtime context
- event streaming
- shared `ReferenceStore`

### 2. AgentNode

`AgentNode` becomes significantly simpler in structure and more important in role.

It should:

- build the system prompt and message history
- bind the single available tool: `graph_retrieval_tool`
- invoke `ToolLoopEngine`
- inspect the final loop result
- package answer, references, and trace

It should no longer:

- perform `CHITCHAT_PREFIXES` routing
- perform `FORCE_KB_TRIGGER_PHRASES` routing as a primary branch
- call `_plan_question()`
- execute explicit `direct / retrieve / decompose` branches
- manually merge decomposition results as its main strategy

### 3. ToolLoopEngine

`ToolLoopEngine` becomes the primary execution core for agent behavior.

It must fully own:

- sending conversation history to the LLM
- detecting tool calls
- executing `graph_retrieval_tool`
- appending tool results back into history
- repeating across rounds
- stopping when the model no longer asks for tools
- enforcing `max_rounds`

This is the closest equivalent to RAGFlow's multi-round chat-with-tools loop.

### 4. graph_retrieval_tool

The first version keeps only this single tool.

Responsibilities:

- run graph retrieval
- return structured retrieval results
- write evidence into `ReferenceStore`

The tool is both:

- the retrieval mechanism
- the evidence ingestion path into the shared store

### 5. ReferenceStore

`ReferenceStore` remains a global evidence pool for the current workflow execution.

Every retrieval round must merge its results into the store.

This ensures:

- earlier retrieval rounds are not lost
- later rounds can add additional evidence
- final citation can reflect the full retrieval session, not only the last tool call

### 6. CitationPostProcessor

Citation continues to happen after the final answer is produced.

This should stay aligned with the current direction and with RAGFlow:

- retrieve first
- accumulate evidence
- answer
- then cite from the evidence pool

## Prompt Strategy

The current planner prompts should be replaced by one main agent prompt focused on tool usage.

The new prompt should tell the model:

- you are a knowledge assistant
- you have one tool: `graph_retrieval_tool`
- decide yourself whether retrieval is needed
- if retrieval is useful, call the tool
- if evidence is insufficient, you may call it again with a better query
- stop when evidence is sufficient or no further retrieval is useful
- if you finally answer without enough evidence, explicitly mark the answer as a general-model supplement

The key difference from the current design is that the model is no longer asked to output a route plan. It is asked to act.

## Trace and Observability

Trace should move away from planner-first semantics and become tool-loop-first semantics.

The trace should emphasize:

- round number
- whether a tool was called
- tool arguments
- retrieval result summary
- whether evidence appears sufficient
- why the agent stopped
- whether the final answer is grounded or fallback

The frontend thinking panel should ultimately reflect this runtime shape instead of planner stages.

## Error Handling

The refactor must preserve the current structured error behavior:

- model API key missing
- model auth failure
- quota exhaustion
- provider/network failure

Additionally:

- tool loop failures must be traceable
- hitting `max_rounds` must produce a controlled final state
- the system must never fail because planner JSON parsing failed, since planner JSON no longer exists in the main path

## Migration Plan

### P0

The first milestone must deliver a real RAGFlow-style single-tool multi-hop agent.

P0 includes:

1. Remove local keyword short-circuiting from the main agent path.
2. Remove explicit planner JSON routing from the main agent path.
3. Refactor `AgentNode` to use only tool-loop-driven decision making.
4. Strengthen `ToolLoopEngine` to become the primary multi-hop runtime.
5. Keep `ReferenceStore` accumulation across all retrieval rounds.
6. Keep citation post-processing after final answer generation.
7. Update trace so it reflects actual loop rounds instead of planner branches.
8. Verify the following scenarios:
   - greeting or identity question can still be answered naturally
   - single-fact knowledge question can trigger one retrieval round
   - harder question can trigger multiple retrieval rounds
   - evidence-insufficient case can fall back with explicit wording

### P1

P1 focuses on quality and UX after the runtime is correct.

P1 includes:

1. Tune the main agent prompt for better stopping behavior.
2. Improve retrieval query rewrite quality through tool-loop behavior.
3. Make the frontend thinking panel align with true retrieval rounds.
4. Show richer evidence summaries per round.
5. Prepare the tool registry structure for future second-tool expansion.

## Files Expected to Change

Primary files expected in P0:

- `backend/app/workflow/nodes/agent_node.py`
- `backend/app/workflow/engine/tool_loop.py`
- `backend/app/services/agent_prompts.py`
- `backend/app/services/chat_service.py`
- `backend/app/workflow/engine/citation_postprocessor.py`
- `backend/tests/workflow/nodes/test_agent_node.py`
- `backend/tests/workflow/engine/test_tool_loop.py`
- `backend/tests/test_chat_api.py`
- `frontend/src/components/chat/ChatMessageList.tsx`

Files expected to remain structurally intact:

- `backend/app/workflow/canvas.py`
- `backend/app/workflow/runtime_context.py`
- `backend/app/workflow/reference_store.py`
- `backend/app/workflow/canvas_factory.py`

## Acceptance Criteria

The refactor is successful when all of the following are true:

1. The chat flow no longer depends on `CHITCHAT_PREFIXES` for its primary routing behavior.
2. The chat flow no longer depends on planner JSON route output.
3. `AgentNode` uses `ToolLoopEngine` as the main control path.
4. The model can call `graph_retrieval_tool` multiple times across rounds.
5. Every retrieval round contributes evidence to `ReferenceStore`.
6. Citation still happens after final answer generation and uses the shared evidence pool.
7. The UI trace matches actual loop behavior rather than planner branches.
8. Existing chat, graph, and settings functionality remains operational.

## Risks

1. Removing planner control may initially make behavior less predictable.
2. Prompt quality becomes more important because the model must decide when to stop.
3. Poorly tuned prompts may cause over-retrieval or under-retrieval.
4. Existing trace UI may temporarily feel less polished during the transition.

These are acceptable for P0 because the runtime model itself is the primary objective.

## Recommendation

Proceed with a strict P0 refactor that removes the current hybrid routing and restores a single, tool-loop-driven agent execution path.

This gives the project the closest practical match to RAGFlow's multi-hop behavior while preserving the Canvas-based runtime and the evidence/citation architecture already built in this repository.
