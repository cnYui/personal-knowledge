# Long Memory Graph Ingestion Design

**Date:** 2026-04-05
**Status:** Approved
**Project:** Personal Knowledge Base

## Background

当前项目在“记忆管理”页面点击“加入知识图谱”后，会把整篇记忆内容作为单个 `episode_body` 直接提交给 Graphiti，再由 Graphiti 结合配置的知识构建模型抽取实体与关系并写入 Neo4j。

这条链路对短文本足够直接，但对长文章存在明显风险：

1. 输入内容没有长度上限，也没有预分段。
2. 后端将整篇文章一次性提交给模型，容易触发上游上下文限制、处理超时或抽取质量下降。
3. 当前 worker 以单次调用为粒度设置 90 秒超时，长文章更容易失败。
4. 前端只关心“这篇文章是否成功入图”，并不需要感知图谱内部 episode 的拆分细节。

因此需要在不改变前端主体验的前提下，为长文章增加自动分段入图能力。

## Goals

1. 为超长记忆增加后端自动分段入图能力。
2. 保持前端仍以“单篇文章”维度展示状态，不暴露 chunk 概念。
3. 降低长文章入图时的超时率、失败率和模型输入压力。
4. 保持现有接口不变，避免额外前端联动改造。
5. 将超时语义调整为“每个 chunk 单独超时”。

## Non-Goals

1. 不修改“记忆管理”页面的主交互模式。
2. 不在本期引入新的数据库表或 chunk 明细表。
3. 不在前端展示 chunk 级别进度。
4. 不在本期增加摘要压缩、主题拆解、用户手动切段等高级能力。
5. 不改变 Graphiti 内部实体/关系抽取机制，只改变提交方式。

## Approach Options

### Option 1: Backend Auto Chunking with Single Memory Status (Recommended)

后端在写入 Graphiti 前自动对长文分段，按 chunk 多次调用 `add_episode()`，但数据库和前端仍只维护单篇记忆级别的 `graph_status`。

优点：

- 对现有 API 和前端侵入最小
- 可以显著降低长文整段提交的失败率
- 保持用户认知简单，仍然是一篇文章、一个状态

缺点：

- 图谱内部会生成多个 episode
- 数据库中不保存 chunk 级别明细

### Option 2: Summarize Then Ingest

先对长文做一次摘要，再把摘要结果写入图谱。

优点：

- 实现看起来更直接
- 图谱内部 episode 数量较少

缺点：

- 容易丢失原文中的实体与关系细节
- 不适合以知识图谱为核心的抽取场景

### Option 3: Reject Long Inputs at Upload or Ingestion Time

当文章过长时直接拒绝，要求用户手动裁剪。

优点：

- 实现最简单

缺点：

- 用户体验差
- 让用户承担系统本可自动处理的复杂度

推荐采用 Option 1。

## Architecture

### High-Level Flow

```text
Frontend
  -> POST /api/memories/{id}/add-to-graph
  -> MemoryService marks memory as pending
  -> GraphitiIngestWorker dequeues memory
  -> GraphitiClient splits long content into chunks
  -> GraphitiClient calls Graphiti.add_episode() once per chunk
  -> Worker aggregates chunk results
  -> Memory graph_status becomes added or failed
```

### Key Principle

“前端按单篇文章展示，后端按多个 chunk 执行。”

也就是说：

1. 用户仍然只操作一条记忆。
2. `Memory.graph_status` 仍然只表示整篇文章的总体状态。
3. Graphiti 内部可以存在多个 episode，但这些 episode 对前端透明。

## Detailed Design

### 1. Chunking Strategy

在 `backend/app/services/graphiti_client.py` 中新增一个轻量分段器，按以下规则处理：

1. 只有当 `content` 超过阈值时才分段，短文保持原有单次写入行为。
2. 优先按自然段切分，其次按句号、问号、感叹号、分号等中文和英文标点切分。
3. 每个 chunk 目标长度控制在 1500 到 2500 字符之间。
4. 尽量避免把一句话拆开；如果单段本身过长，则进行保底硬切分。
5. 对超长文章设置最大 chunk 数上限，默认 8 到 10 段，推荐先取 8。

建议新增方法：

```python
split_memory_content(content: str) -> list[str]
```

该方法只负责返回 chunk 列表，不直接依赖数据库状态。

### 2. Graphiti Ingestion API

在 `GraphitiClient` 中新增：

```python
add_memory_in_chunks(
    memory_id: str,
    title: str,
    content: str,
    group_id: str,
    created_at: datetime,
) -> list[str]
```

行为：

1. 先调用 `split_memory_content(content)`。
2. 若只生成 1 个 chunk，则沿用当前单次 `add_episode()` 路径。
3. 若生成多个 chunk，则逐段调用 Graphiti。
4. 每个 chunk 使用同一篇文章的 `memory_id`、`group_id`、`created_at`。
5. 每个 chunk 的 `name` 使用 `"{title}（i/n）"` 或 `"{title} (i/n)"` 形式，便于图谱侧追踪。
6. 返回所有成功创建的 `episode_uuid` 列表。

本期不新增 chunk 元数据表，也不对外暴露这些 uuid 明细。

### 3. Worker Behavior

`backend/app/workers/graphiti_ingest_worker.py` 由“单次提交”调整为“整篇文章分段提交”：

1. worker 取出 memory 后，调用 `GraphitiClient.add_memory_in_chunks(...)`。
2. 只要全部 chunk 都成功，才将该 memory 标记为 `added`。
3. 任一 chunk 失败，整篇 memory 标记为 `failed`。
4. 失败信息写入 `graph_error`，前端继续复用现有失败展示。

这样可保持现有的 `pending -> added / failed` 状态机不变。

### 4. Timeout and Retry Semantics

当前实现中的 90 秒超时，语义改为“每个 chunk 单独超时”。

具体规则：

1. 单个 chunk 调用 Graphiti 时沿用 90 秒超时。
2. 整篇文章不再设置单独总超时。
3. 限流重试也以下沉到单 chunk 调用为准。
4. 某个 chunk 在多次重试后仍失败，则整篇文章失败。

这样可以避免“文章拆成 5 段后总耗时超过 90 秒但每段其实都正常”的误判。

### 5. Error Handling

错误处理分为三类：

#### Retryable Errors

- 上游 429 限流
- 网络抖动
- 单 chunk 超时
- 临时性上游服务异常

这些错误保持现有重试策略，粒度调整为 chunk 级。

#### Non-Retryable Errors

- API Key 缺失
- 鉴权失败
- 配置错误

这类错误直接让整篇文章失败。

#### Over-Limit Errors

如果文章切分后仍超过最大 chunk 数上限，则直接失败并写入清晰错误：

```text
Graph build rejected: 文章过长，已超过自动分段上限，请先拆分后再入图。
```

这比继续无约束提交更可控。

### 6. Data Model Compatibility

本期不增加数据库字段，继续复用现有 `memories` 表字段：

- `graph_status`
- `graph_episode_uuid`
- `graph_error`
- `graph_added_at`

兼容策略：

1. `graph_status` 仍表示整篇文章级别的状态。
2. `graph_error` 仍表示整篇文章级别的失败原因。
3. `graph_added_at` 仍在整篇成功后写入。
4. `graph_episode_uuid` 为兼容历史字段，保存首个成功 chunk 的 `episode_uuid`。

之所以不新增 chunk 明细字段，是因为当前前端并不关心 chunk 维度，增加 schema 只会放大改动范围。

### 7. Frontend Impact

前端接口和交互保持不变：

1. 继续调用 `POST /api/memories/{id}/add-to-graph`
2. 继续显示 `处理中 / 已在图谱 / 失败`
3. 继续按单篇文章展示，不展示 chunk 数量和明细

可选增强：

- 当后端返回“文章过长，超过自动分段上限”时，前端展示更明确的失败文案。

该增强不是首批必须项。

## File-Level Changes

### Required

- `backend/app/services/graphiti_client.py`
  - 增加长文检测
  - 增加文本分段函数
  - 增加分段入图函数

- `backend/app/workers/graphiti_ingest_worker.py`
  - 将单次入图改为整篇分段入图
  - 将超时语义改为单 chunk
  - 统一聚合成功与失败状态

### Optional

- `frontend/src/components/memory/MemoryDetailDialog.tsx`
  - 优化长文失败提示

- `frontend/src/components/memory/MemoryBubbleItem.tsx`
  - 可选地对超长失败展示更友好的标签文案

## Testing Plan

本期最小测试集合如下：

### Unit Tests

1. `split_memory_content()` 对短文返回单 chunk。
2. `split_memory_content()` 对长文返回多个 chunk，且 chunk 长度接近目标范围。
3. 单自然段超长时能够触发保底硬切分。
4. 超过最大 chunk 数上限时抛出明确错误。

### Service / Worker Tests

1. 短文路径仍然只调用一次 Graphiti。
2. 长文路径会按 chunk 多次调用 Graphiti。
3. 所有 chunk 成功后，memory 最终状态为 `added`。
4. 任一 chunk 失败后，memory 最终状态为 `failed`。
5. 单 chunk 超时会写入可读错误信息。

### Regression Checks

1. 原有短文入图流程行为不变。
2. 前端不需要调整 API 调用方式。
3. 失败和重试提示继续可用。

## Rollout Notes

建议按以下顺序上线：

1. 先实现后端 chunking 和 worker 聚合逻辑。
2. 先用开发环境中的长文样本验证超时与失败率是否改善。
3. 如有需要，再补充前端的长文失败文案优化。

## Open Decisions Resolved

1. 前端是否展示 chunk 级状态：否。
2. 图谱内部是否允许一篇文章对应多个 episode：允许。
3. 90 秒超时按整篇还是按 chunk：按 chunk。
4. 是否新增数据库字段记录 chunk 明细：否。

## Summary

本设计通过“后端自动分段、前端保持单篇文章视图”的方式，在最小改造范围内提升长文章加入知识图谱的稳定性。它不改变现有 API，不引入新的前端复杂度，也不要求数据库 schema 扩张，同时为后续更细粒度的图谱构建优化保留了演进空间。
