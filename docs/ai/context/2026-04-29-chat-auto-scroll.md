# Chat 新消息自动滚动

## 背景

Chat 页面发送新消息后，消息会追加到列表底部。原先列表只渲染消息，不会主动滚动，用户发送后可能仍停留在旧位置，看不到刚刚发送的消息。

## 决策

- 自动滚动逻辑放在 `ChatMessageList` 内部，父页面不新增接口。
- 使用列表末尾的隐藏锚点作为滚动目标。
- 只在 `messages.length` 增加时触发滚动，初次渲染不滚动。
- 不监听消息内容变化，避免 assistant 流式输出时每个 token 都抢占用户阅读位置。
- 滚动参数使用 `behavior: 'smooth'`、`block: 'end'`、`inline: 'nearest'`。

## 验证

- 新增 `frontend/src/components/chat/ChatMessageList.test.tsx`。
- 覆盖初次渲染不滚动、新增消息后滚动到底部。
- 验证命令：`cd frontend && npm run test -- src/components/chat/ChatMessageList.test.tsx`。

## 构建排障

- 本地构建时 `SettingsPage` 的 `VisibilityOutlined`、`VisibilityOffOutlined`、`WarningAmberOutlined` 子路径导入触发 TS7016。
- 原因是当前锁定的 `@mui/icons-material@7.3.9` 对这三个图标只有 barrel 类型声明，子路径没有对应 `.d.ts`。
- 处理方式：这三个图标改为从 `@mui/icons-material` barrel 命名导入，不改变页面行为。
