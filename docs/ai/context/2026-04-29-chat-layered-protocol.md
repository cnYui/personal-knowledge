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
