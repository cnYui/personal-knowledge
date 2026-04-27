# 2026-04-27 Graph 自动刷新联动设计

## 背景

- 当前文字上传只会创建 `memory`，不会自动触发知识图谱入图
- 当前 memories 页面支持手动调用 `POST /api/memories/{id}/add-to-graph`
- 当前 memories 列表已有前端轮询，能持续看到 `graph_status`
- 当前 graph 页面只会在页面挂载和窗口重新获得焦点时重新拉取 `graph-data`
- 当前缺少“某条 memory 入图完成后，主动让 graph 查询失效并刷新”的联动层

## 目标

同时覆盖两个场景：

1. graph 页面当前打开时，某条 memory 入图完成后，图谱自动刷新
2. graph 页面当前未打开时，用户之后切到 graph 页面，直接看到最新图谱，不需要手动刷新

## 非目标

- 不引入 WebSocket
- 不引入 SSE
- 不把 graph 页面改成高频定时轮询
- 不改变现有后端 `add-to-graph` 接口语义

## 现状问题

### 上传链路

- 上传页只调用上传接口，不会自动调用 `add-to-graph`
- 所以上传完成本身不代表已经进入知识图谱

### 入图链路

- memories 页面点击“加入知识图谱”后，只会发送一次入图请求
- 前端没有记录“哪些 memory 正在等待入图完成”
- 前端也没有在 `pending -> added` 时触发 `graph-data` 失效

### graph 页面链路

- graph 页面依赖 `useGraphData`
- 当前 query 配置只有：
  - `refetchOnMount: 'always'`
  - `refetchOnWindowFocus: true`
- 这能保证“之后进入 graph 页面能拿到最新数据”
- 但不能保证“graph 页面当前开着时自动同步最新入图结果”

## 方案选择

本次采用“前端事件驱动 + 现有状态接口联动”方案。

### 核心思路

- 继续复用 memories 的状态来源、查询 hook 和轮询机制
- 前端显式维护“正在等待入图完成的 memory 集合”
- 当轮询发现某条 memory 状态从 `pending` 变成 `added` 时：
  - 主动 `invalidateQueries(['graph-data'])`
  - 清理该 memory 的等待状态
- graph 页面保持现有 query 行为不变

这样可以同时满足：

- graph 页面开着时，`graph-data` 会被主动刷新
- graph 页面没开时，之后进入页面仍会因为 `refetchOnMount` 看到最新结果

实现说明：

- 最终不是复用 memories 页面组件里的那次查询实例
- 而是由全局协调层按需调用 `useMemories(undefined, { enabled })`
- 这样可以在不驻留 memories 页时仍监听 tracked memory 的状态变化
- 同时通过 `enabled` 避免 provider 挂载后产生常驻轮询

## 架构设计

### 1. 前端新增图谱刷新协调层

建议新增一个轻量协调层，最终拆成两部分：

- `useGraphRefreshCoordinator`
- `graphRefreshTracker`

职责：

- 记录前端当前正在等待入图完成的 memory id 集合
- 监听 memories 轮询结果
- 检测状态迁移
- 在满足条件时触发 `graph-data` 失效

其中：

- `graphRefreshTracker` 只负责纯状态机
- `useGraphRefreshCoordinator` 负责 provider、context、查询启停和 graph query 失效

该层不负责渲染，不负责发入图请求，不负责 graph 页面 UI。

### 2. 入图请求与协调层解耦

点击“加入知识图谱”后：

- 发送 `add-to-graph` 请求
- 请求成功后，将该 memory id 注册到“等待入图完成集合”

这一步只表示“开始关注这条 memory 的后续状态”，不表示立即刷新 graph。

### 3. 基于 memories 轮询结果做状态迁移检测

在每次 memories 轮询结果到达后：

- 如果某个被关注 memory 当前状态仍是 `pending`
  - 保持等待，不刷新 graph
- 如果状态变成 `added`
  - 触发 `invalidateQueries(['graph-data'])`
  - 从等待集合移除
- 如果状态变成 `failed`
  - 不刷新 graph
  - 从等待集合移除

这要求协调层能读到最新 memories 数据，并维护上一轮已关注集合。

### 4. graph 页面保持被动刷新

graph 页面不需要知道是哪条 memory 完成了入图。

它只需要继续依赖：

- React Query 的 graph query
- query 失效后的自动重拉
- 页面挂载时的自动拉取

这样 graph 渲染层保持单纯，不和 memories 状态管理耦合。

## 状态机

对单条 memory，前端协调层只关心以下迁移：

- `not_added -> pending`
  - 由用户触发入图请求后开始关注
- `pending -> pending`
  - 不刷新 graph
- `pending -> added`
  - 刷新 graph
  - 移除关注
- `pending -> failed`
  - 不刷新 graph
  - 移除关注

## 边界与异常处理

### 1. graph 页面开着但 memories 页面不在当前路由

只要协调层 provider 仍在全局挂载，graph 页面开着时就能触发 graph 刷新。

如果协调层只挂在 memories 页面内部，那么离开 memories 页后这条联动就会失效。

因此协调层不应只存在于 memories 页面组件内部，更适合放在：

- app provider 层
- 或共享业务 hook 层，由全局容器挂载

这是本次设计的关键点。

补充约束：

- 虽然 provider 全局挂载，但 memories 查询不能无条件常驻
- 只有存在 tracked memory 时才允许启用 memories 轮询
- tracked 集合清空后应停止该轮询

### 2. 页面刷新

页面刷新会丢失前端内存中的“等待集合”。

这是可接受的，因为：

- graph 页面本来就会在重新进入时重拉
- memories 页面本来就会轮询真实状态

本次不做等待集合持久化到 localStorage。

### 3. 批量入图

如果后续使用 batch-add-to-graph：

- 协调层仍按 memory id 集合处理
- 每条 memory 独立判定是否完成
- graph 刷新可以合并触发

建议做简单去抖，避免短时间连续多次 `invalidate graph-data`。

### 4. 重复点击入图

如果某条 memory 已在等待集合中：

- 不重复注册
- 不重复触发额外监听逻辑

### 5. 失败与限流

如果 memory 从 `pending` 进入 `failed`：

- 不刷新 graph
- 保留现有 toast / UI 错误提示机制
- 协调层仅负责清理等待状态

## 推荐实现拆分

### 前端

- `frontend/src/hooks/useMemories.ts`
  - 扩展 `enabled` 开关，避免全局 provider 造成常驻轮询
- 新增协调 hook
  - `frontend/src/hooks/useGraphRefreshCoordinator.ts`
- 新增纯状态机模块
  - `frontend/src/hooks/graphRefreshTracker.ts`
- `frontend/src/pages/MemoryManagementPage.tsx`
  - 在手动入图成功后注册待观察 memory
- `frontend/src/app/providers.tsx` 或更高层容器
  - 挂载协调层，确保不依赖当前是否停留在 memories 页面

### 不建议修改

- `frontend/src/pages/KnowledgeGraphPage.tsx`
  - 除非仅补极少量 query 配置
- 后端 memories / graph 路由
  - 当前接口语义已足够支持此方案

## 测试策略

### 前端单测

- tracker 纯逻辑在 `pending / added / failed / mixed` 状态下行为正确
- 协调层在 `pending -> added` 时触发一次 `invalidateQueries(['graph-data'])`
- 协调层在 `pending -> failed` 时不触发 graph 刷新
- 同一 memory 不重复注册
- 多条 memory 连续完成时刷新次数符合预期
- 无 tracked memory 时不启用 memories 查询
- `invalidateQueries` 挂起期间新增 tracked memory 不会被错误清空

### 联调验证

场景 1：

- 打开 graph 页面
- 再从 memories 页触发某条 memory 入图
- 入图完成后 graph 自动刷新

场景 2：

- 不打开 graph 页面
- 在 memories 页触发入图并等待完成
- 之后切到 graph 页面
- 首次进入直接看到新图谱

## tradeoff

### 选择该方案的原因

- 满足当前“正确版本”需求
- 不引入新的实时通信基础设施
- 复用已有 memories 轮询与 graph query
- 改动范围集中在前端状态协调层

### 明确认可的限制

- 实时性仍取决于 memories 轮询间隔
- 不是服务端主动推送
- 如果未来要求秒级、跨页面、跨设备实时同步，再考虑 SSE / WebSocket

## 结论

本次采用：

- memories 轮询作为状态来源
- 前端协调层作为事件桥接
- `invalidateQueries(['graph-data'])` 作为 graph 自动刷新的触发机制

这是当前代码结构下覆盖 `1 + 2` 目标的最小正确方案。
