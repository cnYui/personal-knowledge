# Agentic RAG V2 升级设计稿

## 目标

将 `personal-knowledge-base` 当前的 Agentic RAG 升级到 [agentic-rag-flow-v2.md](/d:/CodeWorkSpace/ragflow/docs/agentic-rag-flow-v2.md) 所描述的融合式流程，同时保证 `MVP` 阶段的改动足够安全：

- 不修改对外 API
- 不修改响应结构
- 不修改前端消费方式
- 先做最小风险的内部升级

本次升级分为三个版本：

1. `MVP`
2. `V2`
3. `V3`

## 当前现状

当前系统已经具备几个关键能力：

- `AgentKnowledgeProfileService.compose_system_prompt()` 已经能将知识画像 overlay 注入到 Agent 提示词中。
- `AgentNode` 已经支持：
  - `graph_retrieval_tool`
  - `graph_history_tool`
  - `ToolLoopEngine`
  - `direct_general_answer`
  - `kb_grounded_answer`
  - `kb_plus_general_answer`
- `ChatService` 已经具备统一的 citation 和 trace 后处理能力。

但当前聊天画布仍然是：

- `Begin -> Agent -> Message`

系统还没有一个显式的、与目标 `v2` 流程一致的“前置证据探测（pre-retrieval probe）”阶段。

## 目标形态

最终目标流程如下：

1. 标准化用户问题
2. 拼接知识画像 overlay
3. 执行一轮轻量前置检索 probe
4. 根据 probe 结果分支：
   - `no_hit` 或 `weak_hit`：再尝试一次检索改写，如果仍然弱命中则直接降级回答
   - `insufficient`：进入多轮 tool loop
   - `sufficient`：直接基于证据回答
5. 统一输出 citation 和 trace

核心原则如下：

- overlay 负责导航
- probe 负责判断
- tool loop 负责补充
- 最终是否 grounded 由真实证据决定

## 版本规划

## 第一版：MVP

### 目标

以最小的内部改动接入 `overlay + pre-retrieval probe + 三段式决策`。

### 范围

保持所有对外行为不变：

- 不修改 API 路由
- 不修改响应字段
- 不修改前端协议
- 不修改 `chat_agentic_rag.json`

只修改内部编排逻辑，主要涉及：

- [agent_node.py](/d:/CodeWorkSpace/personal-knowledge-base/backend/app/workflow/nodes/agent_node.py)
- 如有必要，对 [agent_prompts.py](/d:/CodeWorkSpace/personal-knowledge-base/backend/app/services/agent_prompts.py) 做少量补充
- 补充或更新 Agent 执行与 trace 相关测试

### MVP 运行流程

在 `AgentNode.execute()` 中执行以下步骤：

1. 标准化问题
2. 提炼 focus points
3. 拼接带有知识画像 overlay 的 system prompt
4. 使用 `graph_retrieval_tool` 先执行一轮 pre-retrieval probe
5. 对 probe 结果进行分类：
   - `no_hit`
   - `insufficient`
   - `sufficient`
6. 如果是 `no_hit`，则基于 focus points 再重试一次 probe
7. 根据结果分支：
   - 如果重试后仍然 `no_hit`，则走 `direct_general_answer`
   - 如果为 `sufficient`，则走 `kb_grounded_answer`
   - 如果为 `insufficient`，则进入现有 `ToolLoopEngine`
8. 如果 tool loop 执行后仍然证据不足，则走 `kb_plus_general_answer`
9. 后续继续走现有 citation 和 trace 输出流程

### MVP 的判定规则

为了控制风险，`MVP` 阶段直接复用现有 `GraphRetrievalResult` 语义：

- `sufficient`
  - `has_enough_evidence == True`

- `no_hit`
  - 没有 references，或
  - `retrieved_edge_count <= 0`，或
  - `context` 为空或极短，且 `has_enough_evidence == False`

- `insufficient`
  - 有一定证据存在
  - 但 `has_enough_evidence == False`

这样可以避免在 `MVP` 阶段引入新的 retrieval schema 设计。

### MVP 需要新增的内部方法

建议在 `AgentNode` 中新增以下内部方法：

- `_run_probe(query, canvas, group_id) -> GraphRetrievalResult`
- `_classify_probe_result(result) -> str`
- `_retry_probe_with_focus_points(query, focus_points, canvas, group_id) -> GraphRetrievalResult`
- `_answer_from_grounded_probe(query, retrieval_result) -> str`
- 少量辅助方法，用于发出 probe 阶段的 timeline 事件

这些方法的目标是让 `execute()` 保持清晰，避免 probe 逻辑和 tool loop 逻辑完全揉在一起。

### MVP 的 Trace 与 Timeline

为 trace 和 runtime timeline 增加明确的 probe 语义：

- `probe_retrieve`
- `probe_retry`
- `probe_grounded`
- `enter_tool_loop`

现有回答动作保持不变：

- `answer_directly`
- `answer_from_kb`
- `fallback_to_general_llm`

虽然前端响应结构不变，但 trace 中应该能够明确体现：

- 首轮证据探测
- 可选的 retry
- 直接 grounded 回答 / 进入 tool loop / fallback 三种路径

### MVP 测试

补充或更新以下测试场景：

1. probe 直接充分 -> 直接 grounded answer
2. probe 无命中 -> retry 后仍无命中 -> direct general answer
3. probe 无命中 -> retry 后证据不足 -> 进入 tool loop
4. probe 证据不足 -> tool loop 后仍不足 -> `kb_plus_general_answer`
5. citation 与 fallback 标记保持正确

主要测试文件：

- [test_agent_node.py](/d:/CodeWorkSpace/personal-knowledge-base/backend/tests/workflow/nodes/test_agent_node.py)

必要时再补：

- `ChatService` 的集成行为测试

## 第二版：V2

### 目标

将已经验证稳定的 probe 逻辑，从 `AgentNode` 中拆分为一个显式的 canvas 节点。

### 范围

将画布结构从：

- `Begin -> Agent -> Message`

调整为：

- `Begin -> Retrieval -> Agent -> Message`

### V2 的改动

- 强化 [retrieval_node.py](/d:/CodeWorkSpace/personal-knowledge-base/backend/app/workflow/nodes/retrieval_node.py)，使其成为真正的 `pre-retrieval probe` 节点
- 更新 [chat_agentic_rag.json](/d:/CodeWorkSpace/personal-knowledge-base/backend/app/workflow/templates/chat_agentic_rag.json)
- 将结构化 probe 输出传递给 `AgentNode`
- `AgentNode` 不再自己执行 probe，而是消费 probe 结果

### V2 的内部输出契约

`RetrievalNode` 应输出以下结构化 probe 信息：

- `hit`
- `evidence_strength`
- `retrieved_edge_count`
- `top_references`
- `probe_reason`

这些内容在 `V2` 阶段仍然可以只作为内部 canvas 变量使用，不需要暴露给外部 API。

### V2 的收益

- 节点职责边界更清晰
- 测试更容易分层
- 更适合后续做 A/B 对比实验
- 架构更接近文档里定义的 `v2` 流程

## 第三版：V3

### 目标

完成融合式 Agentic RAG 的最终形态，让系统在证据判断和长期可扩展性上更稳定。

### V3 的改动

- 将 overlay 从“纯文本提示词注入”升级为更明确的结构化导航层
- 将 probe 从简单布尔判断升级为更强的证据强度评分
- 增强 query rewrite 和 focus-point decomposition 机制
- 更明确地区分和协调：
  - `graph_retrieval_tool`
  - `graph_history_tool`
  - 未来可能接入的外部工具
- 统一以下几类证据的累计和 groundedness 裁决：
  - 首轮 probe 证据
  - tool-loop 多轮检索证据
  - history tool 返回证据

### V3 的结果

到了 `V3`，系统应具备完整的融合式 Agentic RAG 能力：

- 模型知道知识库大概包含什么
- 系统会用真实检索证据验证这种判断
- tool loop 只在需要时补充证据
- fallback 始终保持诚实、可追踪

## 风险

### MVP 风险

- probe 的分类规则可能对少数边缘场景过于粗糙
- 用 focus points 做 retry，效果有时可能不如专门的 query rewrite 模型
- probe 证据与 tool-loop 证据合并时，需要避免 trace 或 reference 重复

### V2 风险

- probe 拆到单独节点后，可能短期影响 canvas 内部变量传递稳定性
- 如果节点边界设计过复杂，`V2` 可能会变成“过早重构”

### V3 风险

- 更强的路由逻辑如果不坚持 evidence-first，可能让 Agent 变复杂
- 工具扩展后，如果边界不清，导航提示和真实证据容易混淆

## 决策规则

为了保证三个版本都稳定演进，必须坚持以下规则：

- 真实检索证据的优先级永远高于 overlay 提示
- overlay 只能影响“是否检索”与“如何检索”
- overlay 不能被视为证据本身
- 当证据不足时，fallback 提示必须保持明确

## 推荐交付顺序

1. 先交付 `MVP`
2. 验证行为稳定且无回归
3. 仅在 `MVP` 稳定后再推进 `V2`
4. 仅在 `V2` 节点边界稳定后再推进 `V3`

## 成功标准

### MVP 成功标准

- 不修改 API 契约
- 不影响前端
- probe 流程正常工作
- direct / grounded / fallback 三种路径可追踪

### V2 成功标准

- retrieval probe 成为真实节点
- agent node 逻辑明显简化
- canvas 路径更贴近设计稿

### V3 成功标准

- 系统具备完整的融合式 Agentic RAG 行为
- 证据处理清晰、可靠、可扩展

