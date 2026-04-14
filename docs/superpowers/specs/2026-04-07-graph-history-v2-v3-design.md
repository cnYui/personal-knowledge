# Graph History V2 / V3 扩展设计

日期：2026-04-07

关联文档：

- `docs/superpowers/specs/2026-04-06-graph-history-tool-and-overlay-lifecycle-design.md`
- `docs/superpowers/plans/2026-04-06-graph-history-v1-implementation-plan.md`

## 背景与目的

2026-04-06 的设计文档已经定义了 graph history 的整体方向：

- 默认问答只看 current truth / latest knowledge
- 历史能力通过显式工具 `graph_history_tool` 触发
- 第一版先支持 memory-history
- 后续再推进 entity-history 与 relation/topic-history

本设计文档不重复定义 V1 的整体语义，而是专门回答两个问题：

1. **主工作区中如何承接已经在 worktree 验证过的 V1 memory-history MVP**
2. **V2 / V3 应如何在不污染 current mode 的前提下继续扩展 history mode**

本文档的目标是把“已批准的 V1 迁回边界”和“未来 V2 / V3 路线”拆开描述，避免把已实现能力、待迁移能力、未来设计混写在同一份文档里。

## 当前结论

### 主工作区当前状态

当前主工作区尚未具备完整的 V1 memory-history 能力，主要表现为：

- `backend/app/services/agent_tools/__init__.py` 仅导出 `GraphRetrievalTool`
- 主工作区缺少 `GraphHistoryService`
- 主工作区缺少 `graph_history_tool`
- 主工作区缺少 graph history 对应 schema 与测试

### 已验证的上游实现来源

已在隔离 worktree `.worktrees/graph-history-v1` 中完成并验证过以下 V1 资产：

- `GraphHistoryService`
- `GraphHistoryTool`
- 对应 schema 结构
- `test_graph_history_service.py`
- `test_graph_history_tool.py`

因此，主工作区下一步的最低风险动作不是重做 V1，而是**将 worktree 中已验证通过的 V1 原样迁回主工作区**。

## 已批准的 V1 迁回边界

本节记录已经确认的迁回范围，作为后续实施边界。

### 目标

仅将 worktree 中已经验证通过的 memory-history MVP 迁回主工作区，不扩 scope。

### 包含内容

1. 在 `backend/app/schemas/agent.py` 补齐以下模型：
   - `GraphHistoryQuery`
   - `GraphHistoryResult`
   - `GraphHistoryResolvedTarget`
   - `GraphHistoryTimelineItem`
   - `GraphHistoryComparisonItem`
2. 新增 `backend/app/services/graph_history_service.py`
3. 新增 `backend/app/services/agent_tools/graph_history_tool.py`
4. 更新 `backend/app/services/agent_tools/__init__.py`，导出 `GraphHistoryTool`
5. 迁回测试：
   - `backend/tests/services/test_graph_history_service.py`
   - `backend/tests/services/test_graph_history_tool.py`

### 不包含内容

- 不在这一步接入 `entity-history`
- 不在这一步接入 `relation/topic-history`
- 不在这一步扩展 agent prompt / tool routing
- 不在这一步重构 current truth / overlay 链路
- 不在这一步补强复杂 diff、实体归一化、跨 memory 聚合

### 验证标准

- 先运行聚焦 pytest，确保迁回后的行为与 worktree 中已验证行为一致
- 重点覆盖：
  - `timeline`
  - `compare`
  - `summarize`
  - `not_found`
  - `unsupported_target_type`
  - `insufficient_history`

## V2 设计：Entity History

### 目标

V2 解决的问题是：**系统不仅能回答“这条 memory 怎么变过”，还要能回答“某个实体在图谱里是如何演化的”。**

典型问题包括：

- “这个实体以前怎么变化的？”
- “这个概念最早是什么时候出现的？”
- “围绕某个实体，最近几个版本有哪些关键变化？”

### V2 的核心挑战

V1 的查询目标是单个 `memory_id`，目标清晰、索引稳定；V2 的目标变成“实体”，复杂度明显上升：

1. **实体解析问题**：用户输入的名称未必是图谱里的规范名
2. **别名问题**：同一实体可能有多个别名
3. **歧义问题**：同名实体可能指向不同语义对象
4. **聚合问题**：一个实体可能跨多个 memories / versions / episodes 演化
5. **证据边界问题**：哪些变化算实体本身变化，哪些只是上下文变化

因此，V2 不能只是把 `target_type` 从 `memory` 改成 `entity`，而需要增加一层显式的实体解析与聚合流程。

### 建议的 V2 架构

在保留 Tool / Service / Repository / Data Source 四层结构的基础上，V2 增加三类能力。

#### 1. Entity Resolver

职责：将用户给出的 `target_value` 解析为业务上可追踪的实体目标。

建议输出：

- `canonical_name`
- `matched_alias`
- `entity_id`（若系统内已有稳定主键）
- `match_confidence`
- `disambiguation_candidates`

它要负责以下语义：

- 完全匹配：直接命中实体
- alias 命中：通过别名归一化到实体
- 多候选冲突：返回歧义候选，不直接编造历史
- 未命中：返回 `not_found`

#### 2. Entity History Aggregator

职责：把一个实体关联到的 memories / versions / episodes 聚合为“实体历史视角”的证据集。

建议聚合顺序：

1. 解析实体
2. 找到与实体相关的 memory 集合
3. 沿 memory 追踪版本与 episode
4. 按时间与版本重组事件序列
5. 产出 timeline / compare / summarize 所需的结构化结果

这一步的重点不是完整复刻图数据库推理，而是先建立稳定、可测试的 SQL + 图补证据的聚合层。

#### 3. Entity Comparison / Summary Builder

职责：把聚合后的事件转换为结构化输出。

V2 仍复用三种 mode：

- `timeline`
- `compare`
- `summarize`

但输出会比 V1 更复杂，因为比较对象可能不再是“单 memory 的相邻版本”，而是“围绕实体的一组变化事件”。

### V2 的工具契约扩展

#### 输入扩展

保留现有输入结构：

- `target_type`
- `target_value`
- `mode`
- `question`
- `constraints`

V2 新增约束建议：

- `entity_match_mode`: `exact | alias | fuzzy`
- `time_range`
- `top_k_events`
- `include_related_memories`
- `disambiguation_policy`: `fail | top1 | return_candidates`

#### 输出扩展

建议在 `resolved_target` 中新增面向实体的字段：

- `entity_id`
- `canonical_name`
- `matched_alias`
- `candidate_count`

建议在 `evidence` 中明确记录：

- 命中的 memories
- 涉及的 versions
- episode / entity / relation 的补充证据

### V2 的状态语义

在 V1 状态基础上，V2 增加两类更细的错误语义：

- `ambiguous_target`：目标存在多个高置信候选，无法安全收敛到单实体
- `insufficient_evidence`：实体存在，但可聚合出的历史证据不足以形成可靠答案

说明：

- `not_found` 表示实体压根没有命中
- `insufficient_history` 表示命中实体，但历史版本数量不足以支撑比较
- `insufficient_evidence` 表示命中实体，但可用证据碎片化或缺失，无法稳定组织为高质量结果

### V2 的 Agent 调用策略

当用户问题明显是“实体演化”时，应优先使用：

- `graph_history_tool(target_type='entity', ...)`

当用户问题同时问“当前是什么”和“以前怎么变过”时，应允许 agent 组合：

1. `graph_retrieval_tool` 查询 current truth
2. `graph_history_tool` 查询 history truth
3. 主助手将 current 与 history 组织为最终答案

此处仍要遵守原始原则：**历史模式不能反向污染默认问答链路**。

### V2 的测试建议

至少覆盖以下场景：

1. 实体精确命中
2. alias 命中
3. 同名歧义
4. 命中实体但无足够历史
5. timeline 聚合成功
6. compare 结果生成成功
7. summarize 结果生成成功
8. current retrieval + history retrieval 组合问答的编排测试

## V3 设计：Relation / Topic History + 多跳 Agentic RAG

### 目标

V3 解决的问题是：**系统不仅能追踪单个 memory 或实体，还能追踪关系与主题在一段时间内如何变化，并与 current retrieval 形成多跳编排。**

典型问题包括：

- “X 和 Y 的关系如何变化？”
- “某个主题在一段时间里的关注度如何变化？”
- “当前结论与历史演化之间有什么关键转折点？”

### V3 的新增复杂度

与 V2 相比，V3 不再只是“找目标 -> 聚合版本”，而是需要先定义聚合单元：

1. **relation-history**：围绕实体对与关系类型的时间演化
2. **topic-history**：围绕一组语义相近的证据进行主题级时间线聚合
3. **current + history 的多跳编排**：先找当前结论，再找历史转折，再比较两者差异

### V3 的建议架构

#### 1. Relation/Topic Resolver

职责：把用户问题解析成更明确的历史分析目标。

例如：

- relation：`source entity + relation type + target entity`
- topic：`topic query + semantic cluster / tag / concept neighborhood`

该层的关键不是一次性解决所有自然语言理解问题，而是提供一个足够稳定的中间表示，供 history service 消费。

#### 2. History Query Planner

这是 V3 相比 V2 新增的核心层。

职责：根据问题类型，决定需要执行哪些查询步骤，以及查询顺序。

例如：

- “X 和 Y 现在是什么关系？” -> current retrieval 优先
- “X 和 Y 以前是什么关系？” -> history retrieval 优先
- “当前结论与历史关键转折点有什么差异？” -> current retrieval + history retrieval + compare 三段式编排

建议 planner 只输出结构化执行计划，不直接生成自然语言。

#### 3. Multi-hop Evidence Composer

职责：把 current truth 与 history truth 的证据统一组织成可消费的结构。

它需要处理：

- 不同工具返回结构的对齐
- 相互冲突证据的标记
- 关键转折点抽取
- 最终可解释 evidence 包装

### V3 的工具边界

V3 仍建议保留两个工具，而不是把一切能力合并成一个超级工具：

- `graph_retrieval_tool`：当前事实
- `graph_history_tool`：历史事实

多跳编排应由 agent 或 planner 层完成，而不是让 `graph_history_tool` 同时承担：

- 当前检索
- 历史检索
- 差异推理
- 最终自然语言生成

这样做的原因：

1. 工具职责更清晰
2. 测试更容易分层
3. 后续替换某一层实现时影响更小

### V3 的 schema / contract 扩展建议

`target_type` 扩展为：

- `memory`
- `entity`
- `relation_topic`

建议在 `constraints` 中增加：

- `relation_type`
- `source_entity`
- `target_entity`
- `topic_scope`
- `turning_point_k`
- `comparison_baseline`

建议在输出中增加：

- `turning_points`
- `confidence`
- `evidence_groups`

其中：

- `turning_points` 用于表达关键转折
- `evidence_groups` 用于把 current / history / comparison 证据分组

### V3 的 Agent 调用策略

#### 单工具场景

- 只问当前事实：调用 `graph_retrieval_tool`
- 只问历史演化：调用 `graph_history_tool`

#### 双工具编排场景

当问题同时涉及“当前结论 + 历史变化 + 差异解释”时，采用以下顺序：

1. 当前检索：确认 current truth
2. 历史检索：拉取 history truth
3. 差异组装：提取关键变化与转折点
4. 最终回答：由主助手完成自然语言组织

这使得系统可以回答更强的问题，而不会把历史证据常驻注入默认系统提示词中。

### V3 的风险

1. **关系解析风险**：自然语言中的关系类型未必与图谱 schema 一一对应
2. **主题聚合风险**：topic 边界可能过宽或过窄
3. **Planner 复杂度风险**：如果让 planner 承担过多策略，会迅速膨胀
4. **证据冲突风险**：current truth 与 history truth 可能出现显著不一致，需要明确展示而不是偷偷抹平

### V3 的测试建议

至少覆盖以下场景：

1. relation-history timeline 成功
2. relation-history compare 成功
3. topic-history summarize 成功
4. current + history + compare 三段式编排成功
5. turning point 提取成功
6. 冲突证据被正确标记

## Overlay / Current Truth 边界要求

本扩展设计继续继承 V1 原则：

- overlay 只服务 current truth
- history tool 只服务 history truth
- history 结果不常驻注入 system prompt

V2 / V3 可以增强历史追溯能力，但不改变以下原则：

1. 默认问答继续只看 latest / current knowledge
2. 历史能力必须按需调用
3. overlay 不承载历史趋势常驻内容

这能保证系统在增强能力的同时，仍保持默认问答的稳定性与可预期性。

## 推荐落地顺序

### 阶段 1：迁回 V1 到主工作区

- 迁回 schema
- 迁回 `GraphHistoryService`
- 迁回 `GraphHistoryTool`
- 迁回导出与测试
- 跑聚焦验证

### 阶段 2：实现 V2 的最小可用 entity-history

- 实现 entity resolver
- 实现 entity history aggregator
- 扩展 `graph_history_tool` 的 `target_type=entity`
- 增加歧义与证据不足测试

### 阶段 3：实现 V3 的最小可用 relation/topic-history

- 定义 relation/topic 中间表示
- 增加 history query planner
- 接通 current + history 的多跳编排
- 增加 turning point / evidence group 输出

## 最终结论

graph history 的后续演进应保持一个清晰原则：

- **V1**：先把单 memory 的历史查询稳定落地
- **V2**：把历史能力扩展到实体级演化
- **V3**：把历史能力扩展到关系 / 主题级演化，并支持与 current retrieval 的多跳编排

同时，系统必须始终维持 current mode 与 history mode 的边界：

- 当前事实由 `graph_retrieval_tool` 提供
- 历史事实由 `graph_history_tool` 提供
- overlay 只总结 current truth
- 历史能力按需触发，而不是默认污染所有问答

这条路线既能承接已经完成的 V1 memory-history MVP，也为后续 entity-history、relation/topic-history 和更强 Agentic RAG 编排留出可持续扩展的架构空间。