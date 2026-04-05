# Bugfix Requirements Document

## Introduction

This document specifies the requirements for fixing a bug where thinking process data (timeline events and agent trace) disappears after the AI response completes streaming. The bug causes the ThinkingProcess component to lose all accumulated timeline events and trace data when the streaming message is finalized, resulting in an empty or placeholder display instead of showing the complete thinking process.

The root cause is in the `finalizeStreamingMessage()` function in `useChat.ts`, which updates the assistant message to set `isStreaming: false` but does not explicitly preserve the timeline and trace data that was accumulated during streaming.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN streaming completes and `finalizeStreamingMessage()` is called THEN the system loses timeline events and trace data from the assistant message

1.2 WHEN the assistant message is updated with `isStreaming: false` THEN the timeline and agentTrace properties become empty or undefined

1.3 WHEN ThinkingProcess component renders after streaming completes THEN it displays "思考完成" placeholder instead of the accumulated thinking process data

1.4 WHEN debug logs are checked after completion THEN they show `timelineEventsLength: 0, hasTrace: false` indicating data loss

### Expected Behavior (Correct)

2.1 WHEN streaming completes and `finalizeStreamingMessage()` is called THEN the system SHALL preserve all timeline events and trace data that were accumulated during streaming

2.2 WHEN the assistant message is updated with `isStreaming: false` THEN the timeline and agentTrace properties SHALL retain their accumulated values

2.3 WHEN ThinkingProcess component renders after streaming completes THEN it SHALL display the complete thinking process with all timeline events and trace data

2.4 WHEN messages are persisted to localStorage after streaming completes THEN they SHALL include the complete timeline and trace data

### Unchanged Behavior (Regression Prevention)

3.1 WHEN timeline events are received during streaming THEN the system SHALL CONTINUE TO update the assistant message with upserted timeline events

3.2 WHEN trace data is received during streaming THEN the system SHALL CONTINUE TO update the assistant message with the trace object

3.3 WHEN content chunks are received during streaming THEN the system SHALL CONTINUE TO append them to the message content with the typing animation

3.4 WHEN references are received during streaming THEN the system SHALL CONTINUE TO update the assistant message with the references array

3.5 WHEN an error occurs during streaming THEN the system SHALL CONTINUE TO handle it by stopping the stream and displaying an error message

3.6 WHEN messages are persisted during streaming THEN the system SHALL CONTINUE TO save them to localStorage and update the query cache
