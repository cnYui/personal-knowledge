import { Memory } from '../types/memory'

export const mockMemories: Memory[] = [
  {
    id: 'memory-001',
    title: 'Graphiti 的 Episode 设计',
    content:
      '每条知识建议作为一个 episode 写入，保留 created_at 与 valid_at。这样在事实发生变化时，可以通过 invalid_at 保留历史轨迹而不是直接覆盖。',
    created_at: '2026-03-20T09:00:00Z',
    updated_at: '2026-03-20T09:00:00Z',
  },
  {
    id: 'memory-002',
    title: 'Python 异步任务队列经验',
    content:
      '同一 group_id 的消息应串行处理，避免时序冲突；不同 group_id 可以并行处理，提高吞吐。FastAPI 返回 202 表示已入队，不代表处理完成。',
    created_at: '2026-03-21T03:15:00Z',
    updated_at: '2026-03-21T04:10:00Z',
  },
  {
    id: 'memory-003',
    title: 'BGE 模型选型结论',
    content:
      '中文和多语场景优先考虑 bge-m3 作为 embedding，bge-reranker-v2-m3 作为重排。召回与重排都要配置，避免只换 embedding 导致质量不稳定。',
    created_at: '2026-03-22T06:30:00Z',
    updated_at: '2026-03-22T06:45:00Z',
  },
  {
    id: 'memory-004',
    title: '多模态知识入库策略',
    content:
      '图片、音频、视频先转文本或结构化 JSON，再写入知识图谱。图谱构建入口统一走 add_episode，source 可标注为 text、json、message。',
    created_at: '2026-03-23T11:20:00Z',
    updated_at: '2026-03-23T11:55:00Z',
  },
  {
    id: 'memory-005',
    title: 'React Query 缓存策略',
    content:
      '列表查询用 queryKey 包含 keyword/tag。编辑和删除成功后 invalidateQueries({ queryKey: ["memories"] })，确保筛选后的列表也自动刷新。',
    created_at: '2026-03-24T01:10:00Z',
    updated_at: '2026-03-24T01:40:00Z',
  },
  {
    id: 'memory-006',
    title: '知识卡片转聊天气泡设计',
    content:
      '在 memories 页面使用一行一条的聊天气泡可提升浏览连续性。详情通过弹窗承载，避免路由切换造成上下文中断。',
    created_at: '2026-03-25T08:05:00Z',
    updated_at: '2026-03-25T08:05:00Z',
  },
  {
    id: 'memory-007',
    title: '删除操作安全原则',
    content:
      '删除记忆前必须二次确认，并在成功后给予明确反馈。删除失败时保留当前上下文，不关闭弹窗，方便用户重试。',
    created_at: '2026-03-26T02:12:00Z',
    updated_at: '2026-03-26T02:40:00Z',
  },
  {
    id: 'memory-008',
    title: 'TemporalGraph 对接预留字段',
    content:
      '加入知识图谱接口建议至少携带 memory_id、title、content、tags、importance、updated_at，方便后端做幂等与增量更新判断。',
    created_at: '2026-03-27T07:00:00Z',
    updated_at: '2026-03-27T07:00:00Z',
  },
  {
    id: 'memory-009',
    title: '标签规范建议',
    content:
      '标签建议控制在 3~6 个，优先使用主题词，不要用整句。这样筛选效率更高，也便于后续映射到知识图谱实体类型。',
    created_at: '2026-03-27T09:30:00Z',
    updated_at: '2026-03-27T10:05:00Z',
  },
  {
    id: 'memory-010',
    title: 'MVP 实施策略',
    content:
      '先做前端 mock + gateway 抽象，再接真实后端。这样 UI 可以先交付，后续只需替换 gateway 实现，不需要推翻页面交互。',
    created_at: '2026-03-28T01:00:00Z',
    updated_at: '2026-03-28T01:10:00Z',
  },
]
