# Chat 分层消息协议与工具卡片设计

## 背景

当前个人知识库的聊天流式输出已经具备 `timeline`、`trace`、`content`、`done` 事件。前端会把 `timeline` 和 `trace` 挂到 assistant message 上，再由 `ThinkingProcess` 渲染结构化思考过程；正文内容继续由 Markdown 渲染。

这次需求是吸收 `poco-claw` 项目中消息输出的一个优点：`tool_use` 和 `tool_result` 在聊天正文中组成内联工具卡片，同时保留个人知识库现有的结构化思考面板，不把模型原始 thinking/reasoning 文本作为前端思考过程展示。

## 目标

1. SSE 协议显式分层：正文层负责用户可读回答和工具卡片，过程观测层负责思考过程与 agent 执行轨迹。
2. `tool_use` 和 `tool_result` 组成内联卡片，展示在 assistant 消息正文中，并保持与 Markdown 正文的顺序关系。
3. `content` 事件继续只表达 Markdown 文本片段，前端不从 `thinking` 或 `reasoning` 字段拼正文。
4. “思考过程”区域只消费 `timeline` 和 `trace`，不直出 raw thinking 文本。
5. 后端如果未来拿到模型原始 thinking/reasoning 文本，可以保留为后端调试字段，但不得进入前端 message 渲染模型。

## 非目标

1. 不迁移 `poco-claw` 的完整 executor、callback、tool execution 落库体系。
2. 不把个人知识库的聊天消息整体改成 `poco-claw` 的消息模型。
3. 不在前端展示模型原始 thinking/reasoning 文本。
4. 不改变当前引用、句级引用、citation section 的语义。
5. 不要求第一阶段把历史 localStorage 消息全部重写为新结构，只需要兼容读取。

## 协议设计

SSE 事件分为两层。

正文层事件：

```json
{"type":"content","content":"Markdown 文本增量"}
{"type":"tool_use","content":{"id":"tool-1","name":"knowledge_graph_search","input":{"query":"..."},"title":"检索知识图谱","order":20}}
{"type":"tool_result","content":{"tool_use_id":"tool-1","status":"done","output":{"summary":"命中 8 条证据"},"is_error":false,"order":21}}
```

过程观测层事件：

```json
{"type":"timeline","content":{"id":"tool-round-1","title":"检索第 1 轮","detail":"正在检索知识图谱","status":"running","order":20}}
{"type":"trace","content":{"final_action":"kb_grounded_answer","tool_loop":{"tool_steps":[]}}}
```

现有事件继续保留：

```json
{"type":"references","content":[]}
{"type":"citation_section","content":[]}
{"type":"sentence_citations","content":[]}
{"type":"done"}
{"type":"error","message":"..."}
```

约束：

1. `content` 只允许表达最终回答正文或正文增量，不承载工具输入输出，也不承载 thinking/reasoning。
2. `tool_use.id` 必须稳定，`tool_result.tool_use_id` 必须指向对应 `tool_use.id`。
3. `order` 用于保持正文层 block 顺序；同一工具调用的 `tool_result` 应在对应 `tool_use` 之后。
4. `timeline` 可描述工具执行进度，但前端不能用 `timeline` 反推工具卡片；工具卡片只由 `tool_use/tool_result` 事件驱动。
5. `trace` 是完整或阶段性 agent 轨迹快照，允许覆盖更新。

## 前端数据模型

assistant message 新增正文 block 列表，和过程观测字段分离：

```ts
type ChatContentBlock =
  | { type: 'markdown'; id: string; text: string; order: number }
  | { type: 'tool_use'; id: string; name: string; input: Record<string, unknown>; title?: string; order: number }
  | { type: 'tool_result'; id: string; tool_use_id: string; status: 'running' | 'done' | 'error'; output?: unknown; is_error?: boolean; order: number }

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  contentBlocks?: ChatContentBlock[]
  timeline?: ChatTimelineEvent[]
  agentTrace?: AgentTrace | null
  isStreaming?: boolean
}
```

兼容策略：

1. 旧消息只有 `content: string` 时，继续按纯 Markdown 渲染。
2. 新消息优先渲染 `contentBlocks`；如果不存在，则回退渲染 `content`。
3. 流式 `content` 事件到达时，追加或合并到当前最后一个 `markdown` block，同时继续维护 `content` 字符串用于兼容 localStorage 和复制逻辑。
4. `tool_use/tool_result` 到达时写入 `contentBlocks`，并按 `order` 排序渲染。
5. `timeline/agentTrace` 不进入 `contentBlocks`，继续传给 `ThinkingProcess`。

## 渲染设计

聊天消息渲染拆成两个稳定入口。

过程观测入口：

1. `ThinkingProcess` 只接收 `timelineEvents`、`trace`、`active`。
2. 继续保留现有 placeholder 动画、折叠展开、从 `trace.tool_loop.tool_steps` 回退构造时间线的能力。
3. 不新增 raw thinking 文本展示分支。

正文入口：

1. Markdown block 使用现有 `MarkdownContent` 渲染。
2. `tool_use + tool_result` 合并为一张工具卡片，参考 `poco-claw` 的内联卡片体验：展示工具名称、输入摘要、执行状态、结果摘要、错误状态。
3. 如果只有 `tool_use` 还没有 `tool_result`，卡片显示运行中状态。
4. 如果先收到 `tool_result`，前端允许暂存，并在对应 `tool_use` 到达后合并；超时或缺失时展示降级卡片。

## 后端职责

后端流式服务负责把 agent 运行过程拆成两类事件。

1. 生成最终回答时，只通过 `content` 发 Markdown。
2. 工具开始执行时发 `tool_use`，工具完成或失败时发 `tool_result`。
3. agent 执行过程中的可解释进度继续发 `timeline`。
4. agent 完整轨迹或阶段性轨迹继续发 `trace`。
5. 如果底层模型或运行时返回 raw thinking/reasoning，后端允许在日志或调试结构中保留，但不得通过 `content`、`tool_use`、`tool_result`、`timeline` 直接下发原文。

## 错误处理

1. 工具执行失败时发 `tool_result`，其中 `status` 为 `error`，`is_error` 为 `true`。
2. 工具失败不一定终止整轮回答；是否终止由后端继续通过 `timeline`、`trace` 和最终 `content/error` 表达。
3. 整体请求失败继续使用现有 `error` 事件，前端结束流式状态并保留已收到的 timeline 和工具卡片。
4. 前端解析未知 SSE 事件时忽略，并保留 console warning，避免破坏旧客户端。

## 迁移策略

第一阶段：协议与前端兼容层

1. 定义 `ChatContentBlock` 类型。
2. 扩展 `sendChatMessageStream`，识别 `tool_use` 和 `tool_result`。
3. 扩展 `useChat`，把正文层事件写入 `contentBlocks`，同时维护旧 `content` 字符串。
4. 新增工具卡片渲染组件，并在 `ChatMessageList` 中接入。

第二阶段：后端工具事件输出

1. 在 agent/tool loop 执行点补发 `tool_use/tool_result`。
2. 保持现有 `timeline/trace/content` 事件不变。
3. 为工具错误、空结果、部分结果补齐统一 result summary。

第三阶段：历史兼容和清理

1. 保留旧 localStorage 消息读取。
2. 确认所有新 assistant 消息都能从 `contentBlocks` 渲染。
3. 复制、清空、错误重试等消息操作优先使用 Markdown 正文，工具卡片不混入纯文本正文。

## 验收标准

1. 普通问答没有工具调用时，用户看到的正文仍是纯 Markdown。
2. 有工具调用时，聊天正文中能按顺序看到工具卡片和 Markdown 回答。
3. 工具卡片能展示运行中、完成、失败三类状态。
4. “思考过程”区域只展示 `timeline/trace` 结构化过程。
5. 前端不会展示 raw thinking/reasoning 原文。
6. 旧 localStorage 聊天记录仍能打开并显示。
7. 后端仍能发送现有 `references`、`citation_section`、`sentence_citations`，引用展示不回退。
8. SSE 解析遇到未知事件不会中断当前回答。

## 需要覆盖的测试

1. `sendChatMessageStream` 能解析 `tool_use/tool_result/content/timeline/trace/done/error`。
2. `useChat` 能把 Markdown 增量合并进 `contentBlocks` 和旧 `content`。
3. 工具 result 先于 use 到达时，最终能正确合并。
4. 旧 `content: string` 消息仍走 Markdown 渲染。
5. `ThinkingProcess` 不依赖正文 block，仍只由 `timeline/trace` 驱动。

## 相关文件

现有前端流式消费入口：

`frontend/src/services/chatApi.ts`

现有消息状态更新入口：

`frontend/src/hooks/useChat.ts`

现有结构化思考过程组件：

`frontend/src/components/chat/ThinkingProcess.tsx`

现有后端 SSE 事件源：

`backend/app/services/chat_service.py`
