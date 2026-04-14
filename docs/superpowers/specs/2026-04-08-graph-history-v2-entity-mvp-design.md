# Graph History V2 Entity-History MVP 设计

日期：2026-04-08

关联文档：

- `docs/superpowers/specs/2026-04-06-graph-history-tool-and-overlay-lifecycle-design.md`
- `docs/superpowers/specs/2026-04-07-graph-history-v2-v3-design.md`
- `docs/superpowers/plans/2026-04-07-graph-history-v2-v3-implementation-plan.md`

## 背景

当前主工作区已经具备 V1 memory-history 的最小可用能力：

- `GraphHistoryTool`
- `GraphHistoryService`
- `target_type='memory'` 的 `timeline / compare / summarize`
- 对应 schema 与测试

但最新的 V2 / V3 设计中，V2 entity-history 与 V3 relation/topic-history 仍未在主工作区落地。

本设计文档的目标不是一次性把 V2 和 V3 全部实现，而是**先把 V2 entity-history 收敛成一个最小可用、边界清晰、可测试的第一阶段方案**，并明确说明这一阶段与后续 V3 的边界。

## 本阶段目标

本阶段只实现 **V2 entity-history MVP**，使系统能够通过显式工具调用回答以下类型的问题：

- “这个实体以前怎么变化的？”
- “这个概念最早是什么时候出现的？”
- “围绕某个实体，最近几次关键变化是什么？”

用户入口保持为：

- `graph_history_tool(target_type='entity', ...)`

输出仍然复用既有的三种 mode：

- `timeline`
- `compare`
- `summarize`

## 不在本阶段范围内

本阶段明确不做以下内容：

1. 不实现 V3 relation/topic-history
2. 不实现 planner / composer / multi-hop orchestration
3. 不让 history 结果常驻注入默认问答 prompt
4. 不把默认 current-truth-only Q&A 改造成自动调用 history 的链路
5. 不追求复杂实体归一化、图推理级别的精确实体对齐

本阶段允许补充少量 **agent 路由描述与 tool schema 提示**，但不引入自动决策逻辑。

## 设计原则

### 1. 保持 current truth 与 history truth 的边界

继续遵守既有设计原则：

- 默认问答只看 current truth
- 历史能力必须通过显式 history tool 触发
- overlay 不承载历史趋势常驻内容

这意味着 V2 只增强 history mode，不反向污染默认问答路径。

### 2. 在 V1 结构上增量扩展，而不是重写

V2 不新造一套并行系统，而是在已有结构上扩展：

- `GraphHistoryTool`
- `GraphHistoryService`
- `Repository`
- `Schema`

这样可以最大化复用 V1 测试与已有行为，降低回归风险。

### 3. 先追求稳定、可测试，再追求智能

V2 第一阶段优先实现：

- 明确的实体解析
- 稳定的实体历史聚合
- 可预期的状态语义
- 聚焦的单元测试与服务测试

而不是在第一阶段就引入复杂推理、自动编排或 prompt 级魔法。

## 架构概览

本阶段的数据流如下：

`agent/tool -> GraphHistoryTool -> GraphHistoryService -> EntityResolver -> EntityAggregator -> GraphHistoryResult`

### 组件职责

#### GraphHistoryTool

职责：

- 保持薄封装
- 接收 `target_type / target_value / mode / question / constraints`
- 将请求透传到 `GraphHistoryService`

要求：

- 不在 tool 层实现业务聚合逻辑
- 不在 tool 层做复杂实体判断

#### GraphHistoryService

职责：

- 作为总调度入口
- 按 `target_type` 分流查询路径
- 组织最终 `GraphHistoryResult`

第一阶段的分流规则：

- `memory`：继续走现有 V1 路径
- `entity`：走 V2 resolver + aggregator 路径
- `relation_topic`：仍返回 `unsupported_target_type`

#### EntityResolver

职责：

- 将用户输入的 `target_value` 解析为可追踪的实体目标
- 输出实体命中结果或失败语义

第一阶段支持以下语义：

- exact match
- alias match
- ambiguous target
- not found

第一阶段不要求：

- 复杂 fuzzy ranking
- 跨图谱 schema 推理
- 高级语义消歧

#### EntityAggregator

职责：

- 从实体名称出发找到相关 memories
- 聚合对应 versions / episodes
- 生成可供 `timeline / compare / summarize` 使用的事件序列

聚合原则：

1. 先基于实体关键词或别名找到候选 memories
2. 再沿 memory 聚合版本与 episode 信息
3. 再按时间或版本顺序整理事件
4. 最终产出稳定、结构化的事件列表

第一阶段聚焦“可用且稳定”的 SQL/Repository 聚合，不追求完整图数据库关系推理。

## Schema 扩展

### GraphHistoryQuery

保留现有结构：

- `target_type`
- `target_value`
- `mode`
- `question`
- `constraints`

第一阶段在 `constraints` 中正式支持以下 entity-history 参数：

- `entity_match_mode`: `exact | alias | fuzzy`
- `top_k_events`: `int`
- `include_related_memories`: `bool`
- `disambiguation_policy`: `fail | top1 | return_candidates`
- `time_range`: 可选时间范围对象或可序列化结构

其中第一阶段的默认安全策略为：

- 若未明确配置，歧义目标按 `fail` 处理

### GraphHistoryResolvedTarget

在现有 memory 字段基础上，新增 entity 相关字段：

- `entity_id`
- `canonical_name`
- `matched_alias`
- `candidate_count`

这些字段用于表达：

- 最终解析命中的实体
- 命中时使用了哪个 alias
- 遇到歧义时有多少候选

### GraphHistoryResult

在现有结果结构上补充以下状态：

- `ambiguous_target`
- `insufficient_evidence`

第一阶段暂不引入 V3 才需要的：

- `turning_points`
- `confidence`
- `evidence_groups`

原因是这些字段主要服务 relation/topic-history 与 current/history 编排，不属于 V2 entity-history MVP 的必要组成。

## 状态语义

第一阶段统一使用以下状态定义：

### `ok`

实体解析成功，且能生成符合 mode 要求的历史结果。

### `not_found`

用户给定目标没有命中任何可追踪实体。

### `ambiguous_target`

用户目标命中了多个高置信候选，系统不会自动猜测最终实体。

第一阶段默认策略是安全失败，而不是强行选择 top1。

### `insufficient_history`

实体命中了，也找到了历史事件，但不足以支撑 `compare` 这类需要版本差异的结果。

例如：

- 只找到一个事件
- 缺少可比较的相邻版本

### `insufficient_evidence`

实体命中了，但聚合到的证据不足以形成稳定、高质量结果。

例如：

- 命中了实体名称，但相关 memories 几乎没有可用 episode/version
- 数据碎片化严重，无法组成可靠的 timeline / summarize

### `unsupported_target_type`

用于保留当前 V1/V2 阶段边界；当请求 `relation_topic` 时继续返回该状态。

### `error`

系统执行异常或不可预期错误。

## 三种 mode 的输出规则

### timeline

返回按时间或版本排序的实体历史事件列表。

每个 timeline item 至少应体现：

- 版本号或事件序号
- 时间信息
- 是否最新
- 摘要信息

### compare

比较规则在第一阶段收敛为：

- 默认比较“最新可比较事件”与“上一个可比较事件”
- 若不足两个可比较事件，则返回 `insufficient_history`

这样可以避免第一阶段就引入复杂 baseline 策略。

### summarize

输出面向实体演化的简短总结，并可附带精简的 timeline / comparison 证据。

总结重点是：

- 该实体关联到多少历史事件
- 最近一次变化发生在何时或何版本
- 若能识别，则补充关键演化方向

## Agent 路由描述

本阶段只补充 **agent 层的描述性能力**，不引入自动 orchestration。

允许增加的内容包括：

- 在 tool schema 中将 `target_type` 描述扩展为支持 `entity`
- 在 agent 提示或说明中补充：当用户明显在问“实体演化历史”时，可使用 `graph_history_tool(target_type='entity', ...)`

本阶段不做：

- 自动判断是否调用 history tool
- current retrieval 与 history retrieval 的自动串联
- history 结果注入默认常驻上下文

## Repository 层预期

为支持 EntityAggregator，允许在 repository 层补充最小必要 helper：

- `MemoryRepository`：提供基于实体关键词/别名检索 memory 的能力
- `MemoryGraphEpisodeRepository`：提供按 memory 集合聚合版本/时间信息的能力

原则：

- 聚合逻辑尽量沉到 repository/service
- workflow/agent 层不直接拼 SQL

## 测试策略

第一阶段至少覆盖以下测试：

### Resolver 测试

1. exact match 成功
2. alias match 成功
3. ambiguous target 返回正确状态与候选数
4. not found 返回正确状态

### Aggregator 测试

1. 能跨多个 memories 聚合实体事件
2. 能按预期顺序返回事件
3. 能遵守 `top_k_events`
4. 无匹配时返回空列表

### Service 测试

1. `target_type='entity'` 的 `timeline` 成功
2. `target_type='entity'` 的 `compare` 成功
3. `target_type='entity'` 的 `summarize` 成功
4. 歧义目标返回 `ambiguous_target`
5. 命中但证据不足返回 `insufficient_evidence`
6. 可解析但可比较事件不足时返回 `insufficient_history`
7. V1 memory-history 回归仍保持通过

### Tool / Contract 测试

1. `GraphHistoryTool` 能透传 entity constraints
2. tool schema / 描述允许 `entity`
3. `relation_topic` 在本阶段仍保持未实现边界

## 风险与取舍

### 风险 1：实体匹配过宽

若第一阶段只依赖关键词匹配，可能把上下文提及实体的 memory 也聚合进来。

取舍：

- 第一阶段接受一定召回偏宽
- 通过 resolver + top_k + 明确状态语义控制风险
- 后续再在 V2 增强版或 V3 中补强精度

### 风险 2：compare 语义不够强

实体历史往往不是单 memory 连续版本，直接比较可能比较粗糙。

取舍：

- 第一阶段统一采用“最新事件 vs 上一可比较事件”规则
- 先保证可解释，再考虑复杂比较基线

### 风险 3：agent 误用 history tool

如果 agent 描述写得过强，可能影响默认 current-truth-only 路径。

取舍：

- 只补描述，不补自动路由逻辑
- 把 history 明确保持在显式调用层

## 验收标准

满足以下条件即可视为 V2 entity-history 第一阶段完成：

1. `graph_history_tool(target_type='entity', ...)` 可返回有效结果
2. `timeline / compare / summarize` 三种 mode 都有明确、稳定的行为
3. `ambiguous_target` 与 `insufficient_evidence` 状态语义已落地
4. V1 memory-history 回归测试保持通过
5. 默认 current-truth-only Q&A 路径没有被改变
6. `relation_topic` 仍明确保持未实现边界

## 与后续 V3 的衔接

本设计刻意为后续 V3 留出边界，但不提前实现：

- `GraphHistoryService` 已具备 target-type 分流模式
- entity-history 的 resolver / aggregator 拆分，为 relation/topic resolver 与 planner/composer 留出了演进位置
- agent 侧只做轻提示，不做 orchestration，避免过早耦合

后续进入 V3 时，再继续引入：

- `relation_topic` resolver
- history query planner
- evidence composer
- current + history 多跳编排

## 最终结论

V2 第一阶段应当被定义为：**在不改变默认 current-truth-only 问答路径的前提下，为 `graph_history_tool` 增加稳定、可测试、显式触发的 entity-history 能力。**

它的核心不是“更智能地自动做一切”，而是：

- 明确实体解析
- 明确实体历史聚合
- 明确错误语义
- 明确与 V1、V3 的边界

这样既能尽快让 entity-history 可用，也不会把 current/history 的职责边界提前打乱。