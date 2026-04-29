# Chat 分层消息协议剩余实现规格

## 审阅结论

原设计要求 `content/tool_use/tool_result` 作为聊天正文层，`timeline/trace` 作为过程观测层。当前项目只完成了 `timeline/trace/content` 的基础流式展示，没有实现 `tool_use/tool_result` 内联工具卡片。

这份文档重新收敛剩余需求：补齐工具事件协议、前端正文 block 模型、内联工具卡片渲染、后端 tool loop 工具事件输出。已存在的结构化思考过程不重写。

## 当前已实现

1. 后端 `/api/chat/stream` 已输出 `timeline`、`trace`、`references`、`citation_section`、`sentence_citations`、`content`、`done`、`error`。
2. 前端 `sendChatMessageStream` 已解析 `timeline`、`trace`、引用、正文和错误。
3. `useChat` 已把 `timeline` 和 `agentTrace` 写入 assistant message。
4. `ThinkingProcess` 已基于 `timeline/trace` 渲染结构化思考过程。
5. `ChatMessageList` 已继续把 assistant 正文作为 Markdown 或句级引用文本渲染。

## 当前未实现

1. `ChatMessage` 没有 `contentBlocks`。
2. 前端没有 `ChatContentBlock`、`ChatToolUseEvent`、`ChatToolResultEvent` 类型。
3. `sendChatMessageStream` 不识别 `tool_use/tool_result`。
4. `useChat` 没有把 Markdown 增量和工具事件写入 `contentBlocks`。
5. 没有 `ToolCallBlock` 或 `AssistantContentBlocks` 渲染入口。
6. `ChatMessageList` 没有从 `contentBlocks` 渲染工具卡片。
7. `ToolLoopEngine` 只发 `timeline` runtime event，不发 `tool_use/tool_result`。
8. `ChatService.rag_stream` 只转发 runtime `timeline`，不会把工具事件转成 SSE。

## 新增问题

结合当前页面表现，还要把下面 3 个问题纳入同一轮收口：

1. 无命中时仍展示“参考引用”。
原因：probe 阶段写入的 `reference_store` 可能被后续 `citation_result` 和 `references` 继续暴露，即使最终答案是 `direct_general_answer` 或明确表示“没有找到相关信息”。

2. 思考过程在正文已经输出完成后仍停留在“处理中”。
原因：`probe-retrieval`、`probe-retrieval-retry` 这类 timeline 事件目前只发 `started`，没有配对 `done/error`，前端只能一直显示当前步骤未结束。

3. Markdown 渲染错误。
原因：`AssistantContent` 的 Markdown 判定漏掉了有序列表和强调语法，带引用时会错误进入句子模式，导致 `1.`、`**加粗**` 等语法以原文本显示。

## 目标

1. 有工具调用时，assistant 正文中按事件顺序显示内联工具卡片和 Markdown 回答。
2. 没有工具调用时，assistant 正文仍按现有 Markdown/句级引用逻辑显示。
3. “思考过程”继续只消费 `timeline/trace`。
4. `content` 只保存 Markdown 正文，不混入工具输入、工具结果、thinking 或 reasoning。
5. 旧 localStorage 消息没有 `contentBlocks` 时仍可正常打开。
6. 如果最终没有图谱证据支撑答案，不展示参考引用。
7. 所有会显示“处理中”的 timeline 步骤都必须有明确结束态。
8. 带 Markdown 语法的回答必须继续走 Markdown 渲染，即使同时存在 references 或 sentence citations。

## 协议

正文层 SSE：

```json
{"type":"content","content":"Markdown 文本增量"}
{"type":"tool_use","content":{"id":"tool-1","name":"graph_retrieval_tool","input":{"query":"向量空间"},"title":"检索知识图谱","order":3}}
{"type":"tool_result","content":{"tool_use_id":"tool-1","status":"done","output":{"summary":"命中 2 条证据"},"is_error":false,"order":5}}
```

过程观测层 SSE：

```json
{"type":"timeline","content":{"id":"tool-round-1","kind":"retrieval","title":"检索第 1 轮","detail":"正在检索知识图谱","status":"started","order":4}}
{"type":"trace","content":{"final_action":"kb_grounded_answer","tool_loop":{"tool_steps":[]}}}
```

约束：

1. `tool_use.content.id` 使用底层工具调用 id，必须稳定。
2. `tool_result.content.tool_use_id` 必须指向对应 `tool_use.content.id`。
3. `order` 由 `ChatService.rag_stream` 统一分配，用于正文 block 和过程事件的相对排序。
4. 工具卡片只能由 `tool_use/tool_result` 生成，不能从 `timeline` 反推。
5. 未知 SSE 事件继续忽略，不中断当前回答。
6. `direct_general_answer` 或无有效图谱证据时，`references/citation_section/sentence_citations` 必须全部为空。
7. `timeline` 中任何 `started` 状态的可见步骤都必须在同一轮回答中收到 `done` 或 `error`。

## 前端模型

新增正文 block：

```ts
export interface ChatMarkdownBlock {
  type: 'markdown'
  id: string
  text: string
  order: number
}

export interface ChatToolUseBlock {
  type: 'tool_use'
  id: string
  name: string
  input: Record<string, unknown>
  title?: string
  order: number
}

export interface ChatToolResultBlock {
  type: 'tool_result'
  id: string
  tool_use_id: string
  status: 'running' | 'done' | 'error'
  output?: unknown
  is_error?: boolean
  order: number
}

export type ChatContentBlock = ChatMarkdownBlock | ChatToolUseBlock | ChatToolResultBlock
export type ChatToolUseEvent = Omit<ChatToolUseBlock, 'type'>
export type ChatToolResultEvent = Omit<ChatToolResultBlock, 'type' | 'id'>
```

`ChatMessage` 新增：

```ts
contentBlocks?: ChatContentBlock[]
```

兼容规则：

1. `contentBlocks` 存在且非空时，assistant 正文优先按 block 渲染。
2. `contentBlocks` 不存在时，继续走现有 `AssistantContent`。
3. `content` 继续维护完整 Markdown 字符串，用于旧消息、localStorage、错误追加和未来复制功能。
4. 流式打字缓冲每次写入 `content` 时，同步写入或合并当前最后一个 Markdown block。
5. `AssistantContent` 的句子模式只适用于纯文本回答；一旦检测到 Markdown 结构，应强制走 `MarkdownContent`。

## 前端渲染

新增 `ToolCallBlock`：

1. 展示工具标题、工具名称、输入摘要、结果摘要。
2. 支持运行中、完成、失败三种状态。
3. 只有 `tool_use`、没有 `tool_result` 时显示运行中。
4. 先收到 `tool_result` 时显示降级工具卡片，标题为“工具调用”。

新增 `AssistantContentBlocks`：

1. Markdown block 使用现有 `MarkdownContent`。
2. `tool_use` 查找同 `id` 的 `tool_result` 并合并成一张卡片。
3. 独立 `tool_result` 降级渲染为未知工具卡片。
4. 引用列表仍由 `ChatMessageList` 现有 `CitationList` 渲染，不混入工具卡片。

## 后端输出

`ToolLoopEngine` 在每次工具调用中发 runtime event：

1. 工具开始前发 `tool_use`。
2. 工具成功后发 `tool_result`，`status='done'`。
3. 工具异常后发 `tool_result`，`status='error'`、`is_error=true`。
4. 原有 `timeline` 事件保留。
5. probe 类 timeline 事件必须显式补发 `done/error`。

`ChatService.rag_stream` 转发 runtime event：

1. `tool_use/tool_result` 转成 SSE 正文层事件。
2. `timeline` 继续转成过程观测层事件。
3. 工具事件转发后递增同一个 `timeline_order`，保证前端 block 和过程事件有稳定相对顺序。
4. 对 `direct_general_answer` 或无有效图谱证据的结果，统一把 `references/citation_section/sentence_citations` 收敛为空数组。

## 验收标准

1. 普通问答没有工具调用时，正文仍是纯 Markdown。
2. 工具调用发生时，assistant 正文中出现内联工具卡片。
3. 工具卡片能展示运行中、完成、失败状态。
4. “思考过程”仍只显示 `timeline/trace`。
5. 前端不显示 raw thinking/reasoning 原文。
6. 旧 localStorage 消息继续显示。
7. 引用、citation section、句级引用不回退。
8. 前后端测试和前端构建通过。
9. 答案明确表示“没有找到相关信息”时，页面不展示参考引用。
10. 正文完全输出后，思考过程不再保留“处理中”状态。
11. 带有序列表、加粗等 Markdown 的回答能正确渲染，不显示字面量 Markdown 标记。

## 需要覆盖的测试

1. `sendChatMessageStream` 解析 `tool_use/tool_result`。
2. `useSendChatMessage` 把 Markdown 增量和工具事件写入 `contentBlocks`。
3. `ChatMessageList` 在存在 `contentBlocks` 时渲染工具卡片，旧消息仍渲染 Markdown。
4. `ToolLoopEngine` 发出 `tool_use/tool_result` runtime event。
5. `/api/chat/stream` SSE body 包含 `tool_use/tool_result`。
6. `direct_general_answer` / `no_hit` 时，`references/citation_section/sentence_citations` 为空。
7. `probe-retrieval`、`probe-retrieval-retry` 等 timeline 事件有配对完成态。
8. 含有序列表和强调语法的回答在存在引用时仍走 Markdown 渲染。
