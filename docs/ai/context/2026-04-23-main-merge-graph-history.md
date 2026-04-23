# 2026-04-23 main 分支合并冲突处理

## 背景

- `main` 已先合入 `agentic-rag-v2-mvp`
- 继续合入 `feature/graph-history-v2-v3` 时出现冲突
- 冲突集中在 graph history 相关服务、schema、repository 和测试

## 本次决策

- 保留 `main` 已有的 `relation_topic` minimal 模式，不接受回退到仅支持 `memory` 和 `entity`
- 吸收 `feature/graph-history-v2-v3` 的实体历史增强：
  - 实体历史聚合能力
  - 实体别名解析补强
  - `top_k_events` 约束相关行为
  - 更完整的实体历史测试覆盖
- 测试按并集保留，删除已过时的“`relation_topic` 不支持”断言

## 结果

- `GraphHistoryService` 同时支持 `memory`、`entity`、`relation_topic`
- `MemoryRepository` 保留现有查询接口，并补入 `list_by_entity_keyword`
- graph history 相关测试合并为当前行为的真实约束，避免后续分支再把 `relation_topic` 支持覆盖掉
