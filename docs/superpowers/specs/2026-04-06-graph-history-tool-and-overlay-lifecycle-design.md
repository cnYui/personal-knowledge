# Graph History Tool 与动态提示词生命周期设计

日期：2026-04-06

## 背景

当前系统已经具备以下基础能力：

- memory 可以被写入 Graphiti / Neo4j 时序知识图谱
- `memory_graph_episodes` 已经开始承担 memory 多版本、多 chunk episode 的映射职责
- 默认知识问答正在朝着“仅使用 latest/current truth”方向收敛
- 动态提示词 overlay 当前以 SQL 快照为主，尚未完全绑定到“当前有效知识”语义

随着编辑、删除、移出图谱、历史问答等需求出现，系统暴露出两个核心问题：

1. **当前有效知识与历史知识没有被明确分层**，导致默认问答、动态提示词、历史追溯之间边界模糊。
2. **历史能力还没有显式产品化**，虽然图谱保留了时间演化事实，但助手还缺少一个专门处理“历史变化/版本演化”问题的工具入口。

本设计旨在同时解决这两类问题：

- 建立 current truth 与 history truth 的统一语义
- 将 history mode 设计为显式工具 `graph_history_tool`
- 统一编辑 / 移出图谱 / 删除 对知识图谱、overlay、history tool 的影响
- 一次性写清第一版、第二版、第三版能力路线图，但当前实现只落第一版

## 目标

### 功能目标

- 默认问答继续只使用 current truth / latest knowledge。
- 新增显式历史工具 `graph_history_tool`，用于处理历史变化、版本演化、前后差异等问题。
- 第一版支持 memory-history 查询。
- 第二版支持 entity-history 查询。
- 第三版支持 relation/topic-history 与更强的多跳 Agentic RAG 编排。
- 动态提示词 overlay 只基于 current truth 生成，并在 current truth 变化时刷新。
- 明确编辑、移出图谱、删除三种动作的独立语义。

### 非目标

- 本阶段不实现第二版、第三版的全部代码。
- 本阶段不要求历史版本默认参与普通问答。
- 本阶段不要求 Graphiti 历史 episode 物理删除完整落地。
- 本阶段不引入“历史趋势”常驻 overlay。

## 核心设计原则

1. **默认回答只看 current truth**：历史知识不应污染默认问答。
2. **历史能力按需调用**：历史问题通过显式工具触发，而非常驻人格注入。
3. **SQL 定义当前有效版本**：`memory_graph_episodes.is_latest` 是当前生效版本的业务判定依据。
4. **Graphiti 保留时间演化事实**：Graphiti / Neo4j 负责承载历史 episode 与时间语义。
5. **编辑、移出图谱、删除语义分离**：三者必须对 current truth、history truth、overlay、history tool 产生不同影响。
6. **接口先统一、能力分阶段扩展**：第一版只实现 memory-history，但接口从一开始就为 entity / relation-topic 预留。

## 术语定义

### Current Truth

当前有效知识。用于默认问答、默认图检索、动态提示词 overlay。

一条知识只有在满足以下条件时才属于 current truth：

- memory 未被删除
- memory 未被移出图谱
- memory 图谱状态可用
- 关联 episode 属于 `memory_graph_episodes.is_latest = true`

### History Truth

历史演化知识。用于版本追溯、时间线分析、历史比较、调试和审计。

history truth 来自：

- Graphiti / Neo4j 中保留的历史 episode
- PostgreSQL 中的版本记录、reference_time、latest 切换轨迹

### Overlay

系统动态提示词增量层。它只表达**当前仍然有效的知识摘要**，不表达历史知识。

### History Mode

助手面对“变化、演化、之前、版本、最早、后来如何改变”等问题时进入的显式历史分析路径。

## 总体架构

系统分为两条主路径：

### 1. Current Mode

用于回答“现在是什么”。

- 使用 `graph_retrieval_tool`
- 只检索 current truth
- overlay 只基于 current truth 生成

### 2. History Mode

用于回答“以前是什么、怎么变化的、版本之间有什么不同”。

- 使用 `graph_history_tool`
- 查询 history truth
- 输出结构化 timeline / comparison / summary 证据
- 由主助手组织最终自然语言回答

这两条路径并存，但不能互相污染。

## 为什么需要 Graph History Tool

如果系统默认只看 latest，那么 Graphiti 的时间能力仍然有价值，但价值不体现在“所有回答都带历史”，而体现在：

- 历史追溯
- 版本比较
- 时间线分析
- 多跳演化推理
- 调试与审计

因此历史能力不应写死在默认检索链路里，而应显式产品化为一个工具。

推荐新增工具：

- `graph_retrieval_tool`：当前事实检索
- `graph_history_tool`：历史事实检索

主助手根据问题意图决定调用哪一个，或组合调用两者。

## `graph_history_tool` 设计

### 工具职责

`graph_history_tool` 不直接产出最终自然语言，而是返回结构化历史证据：

- timeline
- comparison
- summary
- evidence
- warnings

这样做的目的：

- 方便与 `graph_retrieval_tool` 组合做多跳编排
- 降低工具与回答模板的耦合
- 便于测试与演进

### 建议输入结构

- `target_type`: `memory | entity | relation_topic`
- `target_value`: 查询目标
- `mode`: `timeline | compare | summarize`
- `question`: 用户原始问题
- `constraints`: 可选约束，例如 `version_from`、`version_to`、`time_range`、`top_k_events`

#### 第一版支持范围

- 仅保证 `target_type=memory` 可用
- 支持 `timeline / compare / summarize`
- `target_value` 优先使用 `memory_id`

### 建议输出结构

- `target_type`
- `target_value`
- `resolved_target`
- `mode`
- `status`
- `timeline`
- `comparisons`
- `summary`
- `evidence`
- `warnings`

#### `status` 建议值

- `ok`
- `not_found`
- `insufficient_history`
- `unsupported_target_type`
- `error`

#### `resolved_target` 建议字段

- `memory_id`
- `memory_title`
- `latest_version`
- `version_count`

#### `timeline` item 建议字段

- `version`
- `is_latest`
- `reference_time`
- `created_at`
- `episode_count`
- `summary_excerpt`

#### `comparisons` item 建议字段

- `from_version`
- `to_version`
- `change_summary`
- `added_points`
- `removed_points`
- `updated_points`

## 分层架构

推荐采用四层设计：

### 1. Tool 层：`graph_history_tool`

职责：

- 接收助手的工具调用参数
- 做基础参数校验
- 调用 history service
- 返回结构化结果

不负责：

- 复杂业务编排
- 复杂 SQL 细节
- 直接操作图数据库全部逻辑
- 生成最终自然语言

### 2. Service 层：`GraphHistoryService`

职责：

- 根据 `target_type` / `mode` 编排历史查询
- 组织 timeline / compare / summarize
- 处理证据不足、版本不足、目标不支持等业务语义

建议内部再拆为三个子能力：

- `TargetResolver`
- `TimelineBuilder`
- `ComparisonSummaryBuilder`

### 3. Repository 层

第一版至少依赖：

- `MemoryGraphEpisodeRepository`
- `MemoryRepository`

第二版以后可扩展：

- `EntityHistoryRepository` 或等价查询层

### 4. Data Source 层

- PostgreSQL：版本、latest、reference_time、memory 元信息
- Graphiti / Neo4j：历史 episode、图关系、补充证据

### 第一版的数据源原则

第一版 memory-history 查询应以 PostgreSQL 为主索引，以 Graphiti 为补充证据源。

原因：

- SQL 中 version/is_latest/reference_time 语义最稳定
- 第一版无需让图数据库承担全部历史版本主索引职责
- 更利于后续扩展 entity-history / relation-history

## Agent 调用策略

主助手应在系统提示中明确区分两类工具：

- `graph_retrieval_tool`：回答当前事实
- `graph_history_tool`：回答历史变化、版本演化、前后差异

### 调用 `graph_retrieval_tool` 的典型问题

- “Python 是什么？”
- “当前知识库里怎么看 Graphiti？”
- “现在这个概念和什么有关？”

### 调用 `graph_history_tool` 的典型问题

- “这条记忆改过几次？”
- “这个实体以前怎么变化的？”
- “当前版本和上一个版本有什么不同？”
- “这个关系是什么时候出现的？”

### 两者组合调用的典型问题

- “Python 现在是什么？它之前是怎么变化过来的？”
- “当前结论与历史版本有什么关键差异？”

## 版本路线图

本设计文档一次写清三阶段能力，但当前实现仅落第一版。

### 第一版：Memory History MVP

#### 目标

先让系统稳定回答“这条记忆怎么变过”。

#### 包含内容

- 新增 `graph_history_tool`
- 第一版仅支持 `target_type=memory`
- 支持 `timeline / compare / summarize`
- Agent 在识别到 memory-history 问题时调用该工具
- current truth 与 overlay 继续只看 latest

#### 不包含内容

- 通用 entity-history 聚合
- relation/topic-history 分析
- 历史趋势常驻 overlay

### 第二版：Entity History

#### 目标

支持回答“某个实体在图谱中如何演化”。

#### 包含内容

- `target_type=entity`
- 实体名归一化
- alias / 歧义处理
- 从 entity 关联到 memories / versions / episodes
- 输出实体时间线与变化摘要

#### 难点

- entity resolution
- 聚合粒度控制
- 同名实体歧义处理

### 第三版：Relation / Topic History + 强化 Agentic RAG

#### 目标

支持更高阶问题：

- “X 和 Y 的关系如何变化？”
- “某主题在一段时间里的关注度如何变化？”
- “当前结论与历史演化之间有什么关键转折点？”

#### 包含内容

- `target_type=relation_topic`
- relation/topic 时间线聚合
- current retrieval + history retrieval + compare 的多跳编排
- 更强的解释型回答

## 编辑 / 移出图谱 / 删除 的统一语义

这三种动作必须被明确区分。

### 1. 编辑 memory

定义：旧 current 失效，history 保留，等待新版本重新入图。

影响：

- 旧 latest 退出 current truth
- overlay 刷新后移除旧摘要
- history tool 仍可查看旧版本
- 新版本重新入图成功后才重新进入 current truth

### 2. 移出图谱

定义：memory 保留，但退出 current truth。

影响：

- 默认问答不再使用它
- overlay 刷新后剔除相关摘要
- history tool 仍可回答它曾经的版本历史
- 未来可以再次重新加入图谱

### 3. 删除 memory

定义：业务上彻底删除该 memory。

影响：

- 立即退出 current truth
- overlay 刷新并剔除相关摘要
- 第一版可允许底层 Graphiti 历史物理暂留
- 但业务层与普通 history tool 查询不再暴露它

### 三者对比

| 动作 | memory 保留 | current truth 保留 | history truth 保留 | overlay 保留 | 可重新加入 |
| --- | --- | --- | --- | --- | --- |
| 编辑 | 是 | 否 | 是 | 否，直到新版本成功 | 是 |
| 移出图谱 | 是 | 否 | 是 | 否 | 是 |
| 删除 memory | 否 | 否 | 第一版底层可暂留，业务不可达 | 否 | 否 |

## Overlay 生命周期设计

### 核心定义

overlay 只摘要 current truth，不摘要 history truth。

也就是：

`overlay = summarize(current_valid_graph_knowledge)`

而不是：

`overlay = summarize(all_graph_history)`

### overlay 的有效数据条件

- memory 未被删除
- memory 未被移出图谱
- 图谱状态可用
- 对应 episode 为 latest

### overlay 的刷新触发器

只要 current truth 变化，就必须刷新 overlay。包括但不限于：

1. 首次入图成功
2. 新版本重新入图成功
3. 编辑导致 current truth 失效
4. 移出图谱成功
5. 删除 memory 成功
6. 批量 current truth 变化完成后的一次聚合刷新

### overlay 与 history tool 的边界

- overlay 只服务默认问答
- history tool 只服务历史追溯
- history tool 的结果不应常驻注入 system prompt
- 历史信息应按需调用，而不是持续污染默认人格

### overlay 的最终判定规则

只要 current valid graph knowledge 为空，overlay 就必须为空。

这保证以下行为成立：

- 图里没有有效数据时 overlay 为空
- 导入知识成功后 overlay 出现
- 移出图谱后 overlay 收缩或消失
- 删除 memory 后 overlay 收缩或消失
- 编辑但未重新入图时，不再沿用旧知识摘要
- 编辑并重建成功后，overlay 切换为新摘要

## 第一版建议实现范围

### 包含

- `graph_history_tool` 工具壳
- `GraphHistoryService`
- memory-history 的 timeline / compare / summarize
- current truth 与 overlay 的严格绑定
- 编辑 / 移出图谱 / 删除 对 overlay 与 current truth 的统一触发逻辑

### 不包含

- entity-history 完整实现
- relation/topic-history 完整实现
- Graphiti 历史 episode 物理删除
- 历史趋势 overlay
- 复杂的多实体历史可视化

## 风险与注意事项

1. **目标解析风险**：第二版 entity-history 会涉及实体归一化与歧义问题。
2. **版本差异提取风险**：第一版 compare 可能只能先提供较粗粒度差异摘要。
3. **删除语义风险**：若业务删除与底层物理删除同时推进，可能增加一致性复杂度。
4. **overlay 一致性风险**：刷新触发若遗漏，会再次出现“图已清空但 overlay 仍存在”的问题。
5. **工具边界风险**：若让 history tool 直接承担全部图检索与自然语言生成，后期会难以维护。

## 推荐落地顺序

1. 统一 current truth / history truth / overlay 语义
2. 设计 `graph_history_tool` 输入输出 schema
3. 实现 `GraphHistoryService` 的 memory-history MVP
4. 接入主助手工具调用策略
5. 补齐编辑 / 移出图谱 / 删除 对 overlay 的刷新逻辑
6. 增加测试覆盖
7. 第一版上线验证后，再参考本设计推进第二版 entity-history

## 最终结论

本设计的核心不是让历史知识默认参与所有回答，而是把系统升级为一个**双层语义的知识助手**：

- **Current Mode** 负责回答现在
- **History Mode / `graph_history_tool`** 负责回答变化

其中：

- PostgreSQL 负责声明哪个版本当前生效
- Graphiti 负责保存知识如何随时间演化
- overlay 只摘要当前有效知识
- 历史能力通过显式工具按需触发

这样既能保证默认助手稳定、干净、可预期，又能为你后续想做的“实体历史图谱变化、多跳 Agentic RAG 推理”留出清晰且可持续扩展的架构路径。