# 长文章知识图谱入图实施计划

日期：2026-04-05

关联设计文档：

- `docs/superpowers/specs/2026-04-05-long-memory-graph-ingestion-design.md`

## 目标

在不改变前端主交互和 API 形态的前提下，为“加入知识图谱”流程增加长文章自动分段入图能力，降低超时和失败率，并保持前端仍按单篇文章展示状态。

## 阶段 1：分段策略与配置落地

### 目标

- 在后端引入可控的长文分段能力
- 将分段规则集中到 `GraphitiClient`，避免 worker 和 service 重复判断

### 任务

- 在 `backend/app/services/graphiti_client.py` 中新增分段常量与辅助函数
- 实现 `split_memory_content(content: str) -> list[str]`
- 规则按优先级处理：
  - 先判断是否超过长文阈值
  - 优先按自然段切
  - 其次按句号、问号、感叹号、分号等标点切
  - 最后对单段超长内容做保底硬切分
- 增加最大 chunk 数限制，超过上限时抛出明确异常

### 建议默认值

- 长文阈值：`>= 2500` 字符开始分段
- 目标 chunk 长度：`1500-2500` 字符
- 最大 chunk 数：`8`

### 验证

- 短文返回单 chunk
- 普通长文能稳定切成多个 chunk
- 超长自然段也能被切开
- 超过 chunk 上限时返回明确错误

## 阶段 2：GraphitiClient 分段入图能力

### 目标

- 让 `GraphitiClient` 具备“整篇文章按多个 chunk 入图”的统一入口

### 任务

- 在 `backend/app/services/graphiti_client.py` 中新增：
  - `add_memory_in_chunks(...) -> list[str]`
- 保持现有 `add_memory_episode(...)` 作为单 chunk 原子调用
- `add_memory_in_chunks(...)` 内部负责：
  - 调用 `split_memory_content`
  - 对每个 chunk 生成可追踪的标题，如 `标题（1/3）`
  - 顺序调用 `add_memory_episode(...)`
  - 收集所有成功返回的 `episode_uuid`

### 设计要求

- 短文路径仍然只调用一次 `add_memory_episode(...)`
- 长文路径按 chunk 顺序处理
- 本期不对外暴露 chunk 明细，不改 API schema

### 验证

- 短文路径与现有行为一致
- 长文路径能生成多个 episode
- 返回的 uuid 列表长度与成功 chunk 数一致

## 阶段 3：Worker 聚合状态与超时语义调整

### 目标

- 将当前“单次入图成功/失败”改为“整篇文章分段入图后的聚合成功/失败”
- 把 90 秒超时调整为单 chunk 粒度

### 任务

- 修改 `backend/app/workers/graphiti_ingest_worker.py`
- 将 `_process_memory(...)` 中的单次 `add_memory_episode` 调用替换为 `add_memory_in_chunks(...)`
- 将成功标准改为：
  - 所有 chunk 成功后再写 `graph_status='added'`
- 将失败标准改为：
  - 任一 chunk 失败则整篇 `graph_status='failed'`
- 保留 `graph_added_at`、`graph_error` 的现有职责
- `graph_episode_uuid` 兼容性处理为“保存首个成功 chunk 的 uuid”

### 超时与重试调整

- 保持 `90` 秒超时，但作用于单 chunk 调用
- 限流重试仍保留，粒度改为单 chunk
- 不再设置整篇文章总超时

### 验证

- 多 chunk 全成功时最终状态为 `added`
- 任一 chunk 超时/失败时最终状态为 `failed`
- 前端仍只看到单篇文章的最终状态

## 阶段 4：错误信息与兼容细节

### 目标

- 保证长文失败时用户能得到可理解的错误信息
- 保持现有前端页面无需改动也能正常工作

### 任务

- 为“超过自动分段上限”增加清晰错误文案
- 为单 chunk 超时沿用现有超时提示，但语义上表示某个分段处理失败
- 确认 `MemoryDetailDialog` 和 `MemoryBubbleItem` 在不改代码的情况下仍能展示失败信息
- 评估是否需要追加前端小优化：
  - 将超长失败提示改得更明确

### 首批建议

- 先不改前端逻辑
- 如果后端错误文案已经足够清晰，则前端仅复用现有展示

### 验证

- 失败信息在记忆管理页可读
- 不会暴露 chunk 技术细节给用户

## 阶段 5：测试与回归

### 目标

- 用最小测试投入覆盖核心风险点

### 任务

- 为 `GraphitiClient` 新增分段函数单元测试
- 为 worker 新增分段入图聚合测试
- 覆盖以下场景：
  - 短文单次入图
  - 长文多次入图
  - 中间某个 chunk 失败
  - 单 chunk 超时
  - 超过最大 chunk 数上限

### 回归检查

- 原有短文入图流程不受影响
- 现有 `POST /api/memories/{id}/add-to-graph` 不需要调整
- 现有前端状态展示不需要调整

## P0 范围

- `GraphitiClient` 分段函数
- `GraphitiClient` 分段入图函数
- worker 聚合状态更新
- 单 chunk 超时与重试
- 后端测试覆盖

## P1 范围

- 前端长文失败文案优化
- 可配置化 chunk 阈值通过 settings 暴露
- chunk 级日志与监控增强
- 记录 chunk 明细到数据库

## 建议顺序

1. 先实现 `split_memory_content`
2. 再实现 `add_memory_in_chunks`
3. 再接 worker 聚合逻辑
4. 再补错误处理
5. 最后补测试和长文样本验证

## 验收标准

- 长文章点击“加入知识图谱”后，不需要前端改动即可正常进入处理流程
- 长文不会再以单次大文本直接提交给 Graphiti
- 90 秒超时已变为单 chunk 粒度
- 前端仍只按单篇文章展示状态
- 长文入图失败率相较当前明显下降
