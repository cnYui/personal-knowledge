## 背景

- 用户在 chat 页面反馈 3 个前端问题：
  - 无有效命中时仍展示“参考引用”
  - 最终回答已经完成，但思维链里仍残留“处理中”
  - 某些历史消息或引用场景下，Markdown 列表和加粗被当成纯文本显示

## 根因

- 引用展示逻辑过宽：
  - `ChatMessageList` 只要 `references` 或 `citationSection` 非空就展示“参考引用”
  - 这会把“检索过但未真正被正文引用”的证据也展示出来
- 思维链状态机存在双重问题：
  - `useChat` 在流式完成时只结束 `isStreaming`，不会收尾仍为 `started` 的时间线节点
  - `ThinkingProcess` 对 `active=false` 的历史消息仍会把 `started` 视为 current，导致旧消息长期显示“处理中”
- Markdown 渲染入口选择不稳：
  - 旧逻辑在“非 Markdown + 有 references”时也会走句子渲染模式
  - 这会让带编号列表、加粗语法的历史消息被直接按纯文本输出

## 实现

- 前端 chat 渲染重写为“正文引用驱动”：
  - 仅当正文中出现 `[n]` 引用标记，或 `sentenceCitations` 明确给出引用索引时，才展示“参考引用”
  - 引用列表保留原始编号，不再按过滤后重新编号
- `AssistantContent` 收紧句子模式入口：
  - 只有“不是 Markdown 且存在句子级引用”才走句子渲染
  - 其余情况统一走 `MarkdownContent`
- `useChat` 收口时间线状态：
  - `upsertTimelineEvent` 改为按 `id` 覆盖最新状态，不再保留同一节点的多份 started/done 副本
  - 流式完成时把残留 `started` 节点统一改为 `done`
  - 流式失败时把残留 `started` 节点统一改为 `error`
- `ThinkingProcess` 增加视图层兜底：
  - 对 `active=false` 的消息，即使传入旧的 `started` 事件，也按已结束节点渲染，不再显示“处理中”

## 测试

- 前端：
  - `npm test -- --run src/components/chat/ChatMessageList.test.tsx src/hooks/useChat.test.tsx`
  - 新增覆盖：
    - 无句子级引用且正文无 `[n]` 标记时不展示参考引用
    - 消息结束后不再显示“处理中”
    - 流式完成时会收尾残留的 `started` 时间线节点
- 构建：
  - `npm run build`
- 后端回归：
  - `pytest backend/tests/test_chat_api.py backend/tests/workflow/engine/test_citation_postprocessor.py -q`

## 结果

- chat 页面现在只展示被正文真正引用到的证据
- 历史消息和新消息都不会再把已结束步骤渲染成“处理中”
- Markdown 列表、加粗等格式在 assistant 消息里优先按 Markdown 正常渲染
