# Chat 流式失败收尾上下文

## 背景

2026-04-29 在 `main` 分支排查 `chat` 页面“发出消息后没有完成知识图谱 agentic RAG 查询”的问题。

排查结论不是“没有进入检索”，而是“进入流式链路后，失败路径没有闭环”：

1. 后端日志确认请求已经进入 `/api/chat/stream`。
2. `GraphitiClient.search()` 已实际执行，说明知识图谱检索确实发生过。
3. 上游模型接口 `https://api.aaccx.pw/v1/chat/completions` 返回 `502 Bad Gateway` 时，`canvas.run()` 所在后台 task 抛错。
4. 该后台 task 的异常没有稳定回传到主 SSE 循环，导致前端停留在“正在理解你的问题”或退化为笼统 `network error`。

## 问题本质

当前 `chat` 流式链路的成功路径是明确的：

- `timeline/content/.../done`

但失败路径不是唯一出口：

- 有些异常能被 `rag_stream` 外层 `try/except` 变成 SSE `error`
- 有些异常发生在后台 producer task，只出现在日志中，前端收不到明确结束信号

这会造成前端状态机残缺：

1. `assistant.isStreaming` 可能无法正常结束
2. 聊天气泡可能没有明确失败文案
3. 用户无法判断是请求悬挂、知识库无结果，还是模型上游异常

## 本次设计决策

本轮需求只聚焦“失败时明确报错并正确结束流式会话”，不扩展到上游可用性治理。

范围包含：

1. 后端把主流程异常和后台 task 异常统一转换为结构化 SSE `error`
2. 前端在收到 `error` 后稳定结束 loading，并保留已有思考过程和已显示内容
3. assistant 消息本体优先展示后端归一化错误文案

范围不包含：

1. agentic RAG 检索策略调整
2. 上游 `502` 的重试/退避/降级设计
3. 全站统一错误中心

## 需求文档

正式设计文档：

- `docs/superpowers/specs/2026-04-29-chat-stream-error-closure-design.md`
