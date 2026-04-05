# Graphiti 最新版本优先检索与多 Episode 建模设计

日期：2026-04-05

## 背景

当前系统已经把 memory 作为 Graphiti episode 写入时序知识图谱，并在查询时基于 Graphiti 返回的边和实体构造回答上下文。但现有实现存在两个问题：

1. `memories.graph_episode_uuid` 只能保存一个 episode uuid，无法准确表达长文本分 chunk 入图后的一对多关系，也无法表达同一 memory 经多次编辑后产生的多版本 episode 集合。
2. 编辑后的重新入图仍然沿用 `created_at` 作为 `reference_time`，并且查询阶段没有区分“当前有效版本”和“历史版本”，导致系统虽然保留了时序知识，却无法稳定实现“保留历史，但默认只回答最新版本”。

本设计目标是在不删除历史 Graphiti episode 的前提下，实现 A 策略：保留历史版本用于回溯/调试，但默认回答仅使用最新版本对应的 episode。

## 目标

### 功能目标

- 新增 `memory_graph_episodes` 表，支持一条 memory 对应多条 Graphiti episode 记录。
- 支持同一条 memory 的多次版本入图，每个版本可包含多个 chunk episode。
- 查询阶段仅允许 `is_latest=true` 的 episode 参与回答上下文。
- 编辑后重新入图时使用 `updated_at or created_at` 作为 `reference_time`，让新版本在时间语义上成立。
- 保留现有 `memories.graph_episode_uuid` 字段作为兼容字段，短期内继续表示“最新版本的第一个 episode uuid”。

### 非目标

- 本阶段不实现 Graphiti 侧历史 episode 的物理删除。
- 本阶段不实现历史版本 UI、手动回滚、`include_history` 调试开关。
- 本阶段不重构现有 Memory API 的主要响应结构。

## 设计原则

1. **Graphiti 负责原始时序知识存储与召回**：所有版本 episode 仍然保留在图中。
2. **应用数据库负责定义当前有效版本**：通过 `memory_graph_episodes.is_latest` 明确哪些 episode 可参与默认回答。
3. **检索偏新在应用层实现**：不依赖 Graphiti 隐式排序来表达业务上的“当前版本”。
4. **状态切换要具备原子语义**：新版本未完整成功前，旧版本仍保持 latest，避免空窗。
5. **兼容优先，渐进迁移**：第一阶段保留旧字段与旧接口，降低上线风险。

## 数据模型设计

### 现有表

保留 `memories` 表作为主业务表，不改变其主体职责。

保留以下字段：

- `graph_status`
- `graph_episode_uuid`
- `graph_error`
- `graph_added_at`

其中 `graph_episode_uuid` 在过渡阶段继续表示“当前 latest 版本的第一个 chunk episode uuid”。

### 新增表：`memory_graph_episodes`

建议字段：

- `id`: 主键
- `memory_id`: 外键，指向 `memories.id`
- `episode_uuid`: Graphiti 返回的 episode uuid
- `version`: memory 的图谱版本号，从 1 开始递增
- `chunk_index`: 当前版本内的 chunk 顺序，从 0 或 1 开始，保持实现内一致
- `is_latest`: 是否属于当前有效版本
- `reference_time`: 写入 Graphiti 时使用的 reference time
- `created_at`: 该条记录写入应用数据库的时间

### 语义约束

- 同一条 memory 可以有多个 version。
- 同一个 version 可以有多个 chunk episode。
- 同一时刻仅允许一个 version 集合的记录为 `is_latest=true`。
- 历史版本永久保留，默认不参与回答。

### 索引建议

- 唯一或强约束索引：`(memory_id, version, chunk_index)`
- 查询索引：`episode_uuid`
- 过滤索引：`(memory_id, is_latest)`

## 写入与版本流转设计

### 首次入图

首次入图时：

- `version = 1`
- `reference_time = memory.created_at`
- 每个 chunk 成功后都形成一条 `memory_graph_episodes` 记录
- 该版本的全部记录标记为 `is_latest=true`
- `memories.graph_episode_uuid` 写入本轮第一个 episode uuid
- `memories.graph_added_at` 写为成功完成时间

### 编辑后重新入图

当用户编辑 title 或 content 时，仍沿用现有逻辑将 memory 标记为：

- `graph_status = 'not_added'`
- `graph_error = None`

重新提交入图时：

- 新版本号 = 当前 memory 历史最大 version + 1
- `reference_time = memory.updated_at or memory.created_at`
- 通过 Graphiti 为每个 chunk 生成新的 episode
- 新版本 episode 全部成功后，再一次性执行 latest 切换：
  - 将旧版本记录批量更新为 `is_latest=false`
  - 将新版本记录批量更新为 `is_latest=true`

### 两阶段切换

为避免“新版本未成功、旧版本已失效”的问题，采用两阶段切换：

1. 先完成所有新版本 episode 的 Graphiti 写入。
2. 仅在全部成功后，再提交数据库状态切换：旧 latest 降级、新版本升级为 latest。

如果中途失败：

- 不改动旧版本 `is_latest`
- `memories.graph_status = 'failed'`
- 错误信息继续写入 `memories.graph_error`

这样可以确保默认回答始终至少有一个稳定版本可用。

## 检索与“偏新”过滤设计

### 原始召回

继续使用现有 Graphiti 搜索流程：

- 调用 `GraphitiClient.search(query, group_id, limit)`
- 保留 Graphiti 对图中所有历史 episode 的原始召回能力

### 应用层 latest 过滤

在 Graphiti 返回结果后，增加一层应用侧过滤：

1. 从搜索结果中提取关联的 `episode_uuid` 或等价 source episode 标识。
2. 查询 `memory_graph_episodes`，仅保留对应 `is_latest=true` 的记录。
3. 将过滤后的结果继续交给 `KnowledgeGraphService` 构建上下文与回答。

### 排序策略

- latest 过滤之后，默认保留 Graphiti 的原始相关性排序。
- 如需进一步增强，可在应用层加入轻量 tie-breaker：同相关度下，`reference_time` 较新的版本优先。

### 回退策略

如果 latest 过滤后结果为空：

- 默认视为“当前有效知识不足”，返回无足够证据的结果。
- 不自动混入历史版本内容。

后续若需要调试能力，可再单独设计 `include_history=true` 模式，但不纳入本阶段范围。

## 迁移与兼容策略

### 数据库迁移

新增 `memory_graph_episodes` 表及相关索引。

对于已有历史数据，采用保守兼容迁移：

- 对已有 `memories.graph_episode_uuid` 的记录，补一条最小兼容记录：
  - `version = 1`
  - `chunk_index = 0`
  - `is_latest = true`
  - `episode_uuid = memories.graph_episode_uuid`
  - `reference_time = memories.updated_at or memories.created_at`

这样可避免新检索过滤上线后，旧数据因为没有 episode 明细而完全失效。

### API 与 Schema 兼容

- 现有 Memory API 暂不强制变更。
- 继续返回 `graph_episode_uuid`，保持前后端兼容。
- 后续如需展示版本历史，可新增独立接口，例如：
  - `GET /memories/{id}/graph-episodes`

## 第一阶段实现范围

### 包含内容

- 新增 `memory_graph_episodes` 数据表、ORM 模型、migration
- ingest worker 支持记录多 episode、版本号、latest 切换
- 编辑后重新入图改用 `updated_at or created_at` 作为 `reference_time`
- 检索阶段增加 latest 过滤
- 保留兼容字段 `graph_episode_uuid`

### 不包含内容

- 历史版本 UI
- 手动回滚 latest 版本
- 历史版本参与回答的调试开关
- Graphiti 侧历史 episode 删除

## 测试策略

至少覆盖以下场景：

1. **首次入图**
   - 生成 `version=1`
   - 多 chunk 全部被记录为 `is_latest=true`

2. **编辑后重新入图**
   - 生成 `version=2`
   - 旧版记录变为 `is_latest=false`
   - 新版记录变为 `is_latest=true`

3. **新版本入图失败**
   - 旧版 latest 状态不变
   - memory 标记为 `failed`

4. **检索过滤**
   - 命中历史 episode 的结果会被过滤掉
   - 命中最新 episode 的结果可正常进入回答上下文

5. **兼容字段**
   - `memories.graph_episode_uuid` 始终返回当前 latest 版本的第一个主 episode uuid

## 风险与注意事项

1. **Graphiti 搜索结果可提取性风险**：需要确认 search 返回对象中能够稳定拿到 episode 关联标识；如果字段不稳定，可能需要额外适配层。
2. **兼容迁移不完整风险**：历史数据仅有单 episode uuid，无法还原完整 chunk/version 历史，这是可接受的过渡成本。
3. **版本切换事务边界**：要谨慎处理 Graphiti 外部调用与数据库事务边界，确保 latest 状态不会在失败时误切换。

## 推荐落地顺序

1. 建表与 ORM 模型
2. 兼容迁移旧数据
3. 改造 ingest worker 与 episode 记录逻辑
4. 改造编辑后重提的 `reference_time`
5. 在检索链路增加 latest 过滤
6. 增补自动化测试

## 最终结论

该方案实现了以下平衡：

- **图谱层保留历史**：满足 A 策略的时间演化需求
- **回答层只看最新**：满足“旧版本仅用于回溯/调试，不主动参与回答”
- **系统渐进演进**：通过保留 `graph_episode_uuid` 降低改造风险

这使得当前系统从“只有时序存储能力”升级为“有明确当前版本语义的可治理时序知识图谱系统”。