# 设置页接入公网转发模型配置

日期：2026-04-25

## 背景

当前设置页虽然已经有 `/api/settings/model-config` 这条统一配置链路，但前后端只允许编辑两套 API Key：

- 对话模型 API Key
- 知识库构建 API Key

这导致一个根本问题没有解决：

- 只改 Key，不能切换 `provider`
- 只改 Key，不能切换 `base_url`
- 只改 Key，不能切换 `model`
- 只改 Key，不能切换 `reasoning_effort`

对于“接入自定义公网转发接口”这类需求，现有设计不够用，只能靠手改 `.env` 兜底，设置页本身并不具备完整配置能力。

## 目标

- 让设置页可以完整编辑运行时模型配置
- 继续复用现有 `/api/settings/model-config` 接口与 `.env` 热更新能力
- 提供“公网转发配置”预设，减少重复输入
- 让 `gpt-5.4 + xhigh` 成为可见且可保存的设置项
- 不把真实密钥写进文档和示例文件

## 非目标

- 不新增第二套独立设置接口
- 不把真实 API Key 写进前端源码
- 不改变现有 hooks 对外接口

## 设计决策

### 1. 扩展现有 model-config，而不是旁路新增接口

后端 `ModelConfigService` 已经能从 `.env` 读取完整的：

- `provider`
- `base_url`
- `model`
- `reasoning_effort`
- `api_key`

因此问题不在运行时能力，而在更新 schema 和设置页能力被人为收窄。最小正确方案是把更新接口补全，而不是再造一套“自定义 API 设置”。

### 2. API Key 采用“默认保留，显式清空”语义

一旦设置页允许同时编辑 `provider/base_url/model`，如果继续沿用“输入框留空即清空 Key”，就会造成误清空：

- 用户只想改 `base_url`
- 由于拿不到明文 Key，编辑框天然是空的
- 一保存就把原 Key 覆盖成空值

所以需要改成：

- 留空：保持当前 Key 不变
- 明确点击清空：才写回空字符串
- 输入新值：替换当前 Key

### 3. 公网转发预设只写非敏感默认项

预设应该提供：

- provider 默认值
- base URL 默认值
- model 默认值
- reasoning_effort 默认值

真实 Key 只落在本地环境变量中，由后端返回掩码状态给前端展示，避免把密钥打进前端 bundle。

## 环境变量策略

为了兼容本地直跑和 Docker：

- `backend/.env` 作为本地后端运行时配置源
- 根目录 `.env` 作为 Docker Compose 默认注入源
- `.env.example` 与 `backend/.env.example` 只保留占位符，不写真实密钥

本次默认预设：

- provider：`cliproxyapi`
- base URL：`https://api.aaccx.pw/v1`
- model：`gpt-5.4`
- reasoning_effort：`xhigh`

## 风险与取舍

- 如果把真实 Key 写入受版本控制的环境文件，后续误提交会泄漏密钥
- 这次按用户明确要求更新本地环境文件，但文档和示例文件必须继续脱敏
- 预设默认 model 只做“可直接运行”的起点，后续允许用户在设置页继续修改
- 本地 SDK 类型定义未包含 `xhigh`，但运行时接口已可接受，因此后端需要按“字符串透传”处理推理强度

## 下一阶段设置页交互设计

用户希望普通用户可以“选模型厂商 + 填 API Key”直接使用，同时高级用户可以接自己的代理地址或本地 OpenAI 兼容服务。

### 核心判断

`provider` 不应该被设计成硬编码能力开关。真正决定一次模型调用是否可用的是：

- `base_url`
- `api_key`
- `model`
- `reasoning_effort`
- 服务是否兼容 OpenAI Chat Completions 协议

所以设置页里的“模型厂商”应该是预设模板，而不是运行时强绑定分支。

### 推荐交互

设置页每一套运行时配置保留这些字段：

- 模型厂商：下拉框
- API URL：输入框，选择厂商后自动填默认值，但允许用户修改
- 模型名称：输入框，选择厂商后自动填推荐模型，但允许用户修改
- API Key：输入框，云厂商通常填写，本地服务允许留空
- 推理强度：高级设置，下拉选 `默认 / minimal / low / medium / high / xhigh`

厂商下拉建议内置：

- `openai`
- `deepseek`
- `api-121`
- `local-openai-compatible`
- `custom`

### 预设行为

选择厂商时只做字段填充，不锁死字段编辑：

- `openai`：填 `https://api.openai.com/v1` 和推荐模型
- `deepseek`：填 `https://api.deepseek.com/v1` 和推荐模型
- `api-121`：填 `https://api.aaccx.pw/v1`、`gpt-5.4`、`xhigh`
- `local-openai-compatible`：填 `http://localhost:1234/v1`，API Key 不强制
- `custom`：保留当前输入，用户完全自定义

### 推理强度设计

`reasoning_effort` 是模型调用参数，不是厂商属性。

因此：

- 放在高级设置里
- 默认值为空，表示后端不传该字段
- 用户选择具体值时，后端透传给模型接口
- 不按厂商隐藏 `xhigh`，因为代理接口也可能支持
- 如果模型不支持，由“测试连接”或实际调用错误给出明确提示

### API Key 设计

API Key 不应该对所有场景强制必填：

- 云厂商和公网代理通常需要 Key
- 本地 OpenAI 兼容服务可能不需要 Key，或接受任意占位值

保存语义继续沿用当前决策：

- 留空：保留当前 Key
- 输入新值：替换 Key
- 显式清空：清空 Key

后端运行时也需要配合这个语义：

- 不在客户端初始化阶段因为空 Key 中止
- 空 Key 使用 `not-needed` 作为 OpenAI 兼容客户端占位值
- 云端厂商如果确实需要鉴权，由上游接口返回 401/403，再经现有错误归一化提示用户

### 建议补充能力

后续应该增加“测试连接”按钮，测试当前组合是否可用：

- `GET /models` 是否可访问
- `chat.completions` 是否能返回内容
- 选择了 `reasoning_effort` 时，该参数是否被服务接受
- 需要 JSON 输出的知识库构建链路是否支持 `response_format`

这个能力能避免用户保存了看似完整但实际不可调用的配置。

## 2026-04-25 API 调用验证

本次补充确认了设置页模型配置变更后，两个核心页面的 API 调用仍然正常。

### memories 页面知识图谱提取

前端调用链：

- `frontend/src/services/memoryGateway.ts`
- `temporalGraphGateway.addToKnowledgeGraph(memory)`
- `POST /api/memories/{memory.id}/add-to-graph`

后端路由：

- `backend/app/routers/memories.py`
- `add_memory_to_graph`
- `MemoryService.add_to_graph`
- `GraphitiIngestWorker.enqueue(memory_id)`

验证结果：

- 路由级测试使用内存 SQLite 和 mock worker，避免污染真实知识库
- 创建 memory 返回 `201`
- 调用 add-to-graph 返回 `202`
- 返回 `graph_status=pending`
- worker enqueue 调用 1 次
- 前端 service 测试已断言入图按钮使用 `/api/memories/{id}/add-to-graph`

结论：memories 页面的“加入知识图谱/提取”API 契约正常；完整图谱写入依赖真实 Graphiti、Neo4j 和模型服务，本次未造测试知识写入真实图谱，避免污染用户数据。

### chat 页面对话

前端调用链：

- `frontend/src/services/chatApi.ts`
- `sendChatMessageStream`
- `POST /api/chat/stream`
- SSE 事件：`timeline / trace / references / citation_section / sentence_citations / content / done`

后端路由：

- `backend/app/routers/chat.py`
- `rag_stream`
- `ChatService.rag_stream`

验证结果：

- 路由级测试返回 `200`
- `content-type` 为 `text/event-stream`
- SSE 中包含 `timeline`
- SSE 中包含 `content`
- SSE 中包含 `done`
- 真实运行后端 `POST http://127.0.0.1:8000/api/chat/stream` 返回 `200`
- 真实运行后端 SSE 无 `error` event，并返回 `timeline / trace / references / content / done`

结论：chat 页面实际对话 API 调用正常，当前运行配置已能走到公网转发模型。

### 测试维护

原先 `backend/tests/test_memories_graph.py` 和 `backend/tests/test_chat_api.py` 使用 `with TestClient(app)`，会触发 FastAPI lifespan，进而启动真实 Graphiti/title worker，导致本地路由级测试可能卡住。

已调整为直接创建 `TestClient(app)` 并手动关闭，不进入 lifespan。这样测试只验证路由、payload 和响应契约，不启动真实后台 worker。
