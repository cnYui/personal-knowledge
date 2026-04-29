# Chat 分层消息协议上下文

## 背景

2026-04-29 确认聊天输出改造采用“分层协议方案”。目标是吸收 `poco-claw` 的 `tool_use/tool_result` 内联工具卡片体验，同时保留个人知识库现有 `timeline/trace` 结构化思考过程。

正式需求与设计文档：

`docs/superpowers/specs/2026-04-29-chat-layered-protocol-design.md`

实现计划：

`docs/superpowers/plans/2026-04-29-chat-layered-protocol-implementation-plan.md`

## 决策

1. SSE 协议分为正文层和过程观测层。
2. 正文层包含 `content`、`tool_use`、`tool_result`。
3. 过程观测层包含 `timeline`、`trace`。
4. `content` 继续只作为 Markdown 正文，不混入工具结果和 thinking/reasoning。
5. `tool_use/tool_result` 在前端组成内联工具卡片。
6. “思考过程”只使用 `timeline/trace` 展示。
7. 如果后端未来拿到 raw thinking/reasoning 文本，可以保留作后端调试，但不能进入前端消息渲染。

## Tradeoff

选择分层协议而不是最小接入，是因为当前项目已经有 `timeline/trace` 的结构化思考过程基础。直接把所有事件塞进 `content` 或统一改成单一 block 模型，会让正文、工具执行、思考过程的边界重新混在一起。

分层方案改动面适中：需要扩展 SSE 事件、前端消息类型和工具卡片渲染，但不会推翻现有 `ThinkingProcess`，也不会破坏旧消息的纯 Markdown 兼容。

## 后续实现顺序

1. 先改前端类型和 SSE 消费层，支持 `contentBlocks` 与旧 `content` 并存。
2. 再新增工具卡片渲染组件，接入聊天消息列表。
3. 最后在后端 tool loop 输出 `tool_use/tool_result`，保持现有 `timeline/trace/content` 事件不变。

## 补充问题

这轮重新审阅后确认，剩余实现不能只补内联卡片，还要同时收口 3 个现存问题：

1. 无命中时仍展示参考引用。
根因：probe 阶段写入的 `reference_store` 会继续参与 `references/citation_section` 组装，即使最终答案已经降级为 `direct_general_answer`。

2. 思考过程停留在“处理中”。
根因：`probe-retrieval`、`probe-retrieval-retry` 这类 timeline 事件只发 `started`，没有对应 `done/error`。

3. Markdown 渲染错误。
根因：`ChatMessageList` 的 `looksLikeMarkdown` 判定漏掉有序列表和强调语法，导致带引用时错误走句子模式。

## 实现结果

1. 已补齐 `tool_use/tool_result` SSE 协议，前端新增 `contentBlocks`，并保留正文 `content` 的纯 Markdown 渲染路径。
2. 已新增内联工具卡片渲染：`tool_use` 展示调用中的工具状态，`tool_result` 负责把同一工具调用更新为完成或失败结果。
3. 已增加引用输出门禁：最终回答降级为 `direct_general_answer` 或没有有效证据时，`references`、`citation_section`、`sentence_citations` 会被收敛为空。
4. 已补齐 `probe-retrieval`、`probe-retrieval-retry` 的完成态事件，前端思考过程不再停留在“处理中”。
5. 已修复 Markdown 判定，补上有序列表、强调语法等识别，避免正文被错误按普通句子拆分渲染。

## 关键落地

1. 前端在 `frontend/src/services/chatApi.ts` 中消费 `tool_use/tool_result` 事件，并在 `frontend/src/hooks/useChat.ts` 里转成 `contentBlocks`。
2. 前端消息区新增 `frontend/src/components/chat/AssistantContentBlocks.tsx` 和 `frontend/src/components/chat/ToolCallBlock.tsx`，优先使用 block 流渲染 assistant 输出。
3. 后端在 `backend/app/workflow/engine/tool_loop.py` 为工具调用发出开始和完成事件，在 `backend/app/services/chat_service.py` 做 SSE 转发与引用收敛。
4. `backend/app/workflow/nodes/agent_node.py` 为 probe 相关 timeline 事件补全 `done/error`。

## 验证记录

已执行：

1. `cd frontend && npm run test -- src/services/chatApi.test.ts src/hooks/useChat.test.tsx src/components/chat/AssistantContentBlocks.test.tsx src/components/chat/ChatMessageList.test.tsx`
2. `cd frontend && npm run build`
3. `cd backend && pytest tests/workflow/engine/test_tool_loop.py tests/test_chat_api.py -q`

待补最终运行态验证：

1. 本地前端可访问性检查
2. 本地后端健康检查
