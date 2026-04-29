## 背景

- chat 页面需要拆出一个更小的前端修复 PR，只处理以下用户可见问题：
  - 无有效命中时不应展示“参考引用”
  - 最终回答完成后，思维链不能残留“处理中”
  - Markdown 编号列表、加粗和稀疏引用编号需要按正文稳定渲染

## 拆分范围

- 只包含前端 chat 渲染和状态收尾：
  - `frontend/src/components/chat/ChatMessageList.tsx`
  - `frontend/src/components/chat/ThinkingProcess.tsx`
  - `frontend/src/hooks/useChat.ts`
  - 对应前端测试
- 不包含 layered protocol、tool block、startup lazy loading、后端 worker/graph/startup 改动

## 实现

- `ChatMessageList` 改为“正文引用驱动”的引用展示：
  - 只有正文存在 `[n]` 标记，或 `sentenceCitations` 明确引用时才显示参考引用
  - 引用区保留原始编号，不再重排成连续编号
- `AssistantContent` 收紧句子模式：
  - 只有“不是 Markdown 且存在句子级引用”才走句子渲染
  - 带编号列表、加粗等格式的回答统一走 Markdown 渲染
- `useChat` 在流式结束和失败时统一收尾 timeline：
  - 按 `id` 覆盖时间线最新状态
  - 遗留 `started` 在完成时改为 `done`
  - 遗留 `started` 在失败时改为 `error`
- `ThinkingProcess` 对非 active 的历史消息不再把 `started` 渲染成 current

## 验证

- `npm test -- --run src/components/chat/ChatMessageList.test.tsx src/hooks/useChat.test.tsx`
- `npm run build`

## 结果

- 小 PR 可以独立解释为“chat 渲染与状态收尾修复”
- 不再把无关的 startup / protocol / worker 改动混进同一个评审面
