# 模型运行时网关抽象

日期：2026-04-27

## 背景

设置页已经允许用户修改模型厂商、API URL、模型名、推理强度和 API Key。新的风险点不是前端页面调用地址，而是后端多处业务代码直接拼装模型运行时：

- `AsyncOpenAI(api_key, base_url)`
- `model`
- `reasoning_effort`
- Graphiti `LLMConfig`
- provider 维度的错误归一化

这些逻辑分散在 chat 对话和 memories 入图链路中。后续只要 API 配置字段或兼容策略变化，就容易出现一个流程已适配、另一个流程遗漏的问题。

## 目标

- 把模型 API 配置变化收敛到统一运行时网关
- chat 流程只声明使用 `dialog`
- memories 入图流程只声明使用 `knowledge_build`
- 业务层不再重复处理 API Key 占位、base URL、模型名、推理强度和 provider 错误映射
- 保持现有页面 API endpoint 不变

## 非目标

- 不重写 chat canvas 或 Graphiti 入图流程
- 不新增第二套设置接口
- 不改变前端请求路径
- 不引入厂商硬编码能力分支

## 设计

新增或扩展 `backend/app/services/model_client_runtime.py`，作为模型运行时网关。

核心对象：

- `ModelRuntimePurpose`：`dialog` 或 `knowledge_build`
- `ModelRuntime`：封装当前用途的 `provider/base_url/model/reasoning_effort/client/version`
- `ModelRuntimeGateway`：根据用途读取 `ModelConfigService`，构建和缓存运行时

核心能力：

- `get_runtime("dialog")`
- `get_runtime("knowledge_build")`
- `ModelRuntime.completion_extra()`：统一返回可透传给 chat completion 的高级参数
- `ModelRuntime.map_error(error)`：统一使用 provider 归一化模型错误
- `ModelRuntimeGateway.build_graphiti_llm_config("knowledge_build", max_tokens=2048)`：统一生成 Graphiti 所需 `LLMConfig`

## 调用边界

chat 相关服务：

- `KnowledgeGraphService`
- `CitationPostProcessor`
- `TitleGenerator`
- `TextOptimizer`
- `AgentNode`

都从 `dialog` runtime 取 `client/model/reasoning_effort`。

memories 入图相关服务：

- `GraphitiClient`
- `StepFunLLMClient`

都从 `knowledge_build` runtime 或统一生成的 Graphiti `LLMConfig` 取配置。

## 取舍

- 网关只做 OpenAI 兼容协议的运行时抽象，不在这里判断厂商能力。
- 如果某个模型不支持 `reasoning_effort`，仍由真实模型调用返回错误，再通过统一错误归一化展示。
- Graphiti 的 SDK client 仍由 `GraphitiClient` 持有，因为它还绑定 Neo4j、embedder 和 cross encoder，不适合放进通用模型网关。

## 验证

- 新增 `ModelRuntimeGateway` 单元测试，覆盖 dialog/knowledge_build 两种用途、空 API Key 占位、推理强度透传和错误 provider 映射。
- 回归 chat stream 和 memories add-to-graph 路由测试。
- 回归设置页模型配置测试。

## 实现记录

已新增 `backend/app/services/model_client_runtime.py` 的运行时网关能力：

- `resolve_openai_compatible_api_key`
- `create_openai_compatible_client`
- `ModelRuntime`
- `ModelRuntimeGateway`
- `model_runtime_gateway` 全局实例

业务迁移结果：

- `KnowledgeGraphService` 使用 `dialog` runtime 生成知识库回答。
- `CitationPostProcessor` 使用 `dialog` runtime 做句子引用对齐。
- `TitleGenerator` 使用 `dialog` runtime 生成记忆标题。
- `TextOptimizer` 使用 `dialog` runtime 做文本优化。
- `AgentKnowledgeProfileRefreshService` 使用 `dialog` runtime 生成知识画像。
- `GraphitiClient` 使用 `knowledge_build` runtime 构造 Graphiti LLM 和 reranker 配置。
- `StepFunLLMClient` 统一使用 `create_openai_compatible_client`，不再单独处理空 Key 占位。

当前后端业务层不再直接调用 `get_dialog_config()`、`get_knowledge_build_config()` 或 `map_model_api_error()`；这些细节只保留在 `ModelRuntimeGateway` 和 `ModelConfigService` 边界内。

## 后续约束

新增模型调用时不要在业务服务中直接读取 `.env` 或 `ModelConfigService` 的具体字段。应先明确用途：

- 用户对话、标题、文本优化、引用整理、知识画像：使用 `dialog`
- 图谱入库、Graphiti 抽取、Graphiti reranker：使用 `knowledge_build`

然后通过 `ModelRuntimeGateway` 获取 runtime 或 Graphiti `LLMConfig`。

## 实施记录

已新增 `backend/app/services/model_client_runtime.py` 作为统一模型运行时网关。

抽象后的关键方法：

- `create_openai_compatible_client(api_key, base_url)`
- `resolve_openai_compatible_api_key(api_key)`
- `ModelRuntimeGateway.get_runtime('dialog')`
- `ModelRuntimeGateway.get_runtime('knowledge_build')`
- `ModelRuntime.completion_extra()`
- `ModelRuntime.map_error(error)`
- `ModelRuntimeGateway.build_graphiti_llm_config('knowledge_build')`

已迁移的 chat 侧调用点：

- `KnowledgeGraphService`
- `CitationPostProcessor`
- `AgentKnowledgeProfileRefreshService`
- `TitleGenerator`
- `TextOptimizer`
- `AgentNode`

已迁移的 memories 入图侧调用点：

- `GraphitiClient`
- `StepFunLLMClient`

迁移后，业务流程不再直接关心 API Key 占位、base URL、模型名、provider 错误映射和高级 completion 参数。后续如果设置页新增模型参数，优先改 `ModelRuntime.completion_extra()` 和相关运行时构造逻辑。
