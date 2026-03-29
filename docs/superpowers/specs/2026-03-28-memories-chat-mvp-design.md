# Memories 聊天气泡页 MVP 设计

## 1. 背景与目标

当前 `memories` 页面采用卡片列表展示。新需求是将其改为“聊天气泡式一行一条”，并支持点击查看完整内容、编辑、删除、以及“加入知识图谱”入口。

后续将接入另一个“时序知识图谱”项目作为后端，因此本次 MVP 需要在不实现后端联通的前提下，预留稳定的前端调用边界。

本期目标：

- 在 `memories` 页面完成聊天气泡式列表展示（替代卡片样式）。
- 提供详情弹窗（非路由跳转），展示完整知识内容。
- 在详情弹窗支持编辑、删除和“加入知识图谱”按钮。
- 先使用前端模拟数据，但为后续真实后端接入保留接口抽象。

## 2. 范围与非目标

### 2.1 本期范围

- 前端 UI 改造（列表样式 + 详情弹窗）
- 模拟数据接入
- 数据访问层抽象（Gateway）
- “加入知识图谱”按钮占位行为（toast）

### 2.2 非目标

- 不实现真实时序知识图谱 API 联通
- 不实现知识图谱构建状态回流（任务状态、进度）
- 不实现图谱可视化
- 不实现新后端接口定义变更

## 3. 核心交互设计

### 3.1 Memories 列表页

- 每条知识以气泡方式单行展示。
- 气泡展示字段：标题、摘要（内容截断）、标签与更新时间（简化展示）。
- 点击气泡打开详情弹窗。
- 去除原卡片样式入口（`MemoryCard` 不再用于该页面）。

### 3.2 详情弹窗

弹窗内展示：

- 标题
- 完整内容
- 标签、重要度、创建/更新时间

弹窗动作：

- 编辑：复用现有编辑流程（可继续使用当前编辑表单能力）
- 删除：复用现有删除确认流程
- 加入知识图谱：本期调用占位方法并反馈成功提示

## 4. 数据层设计（MVP 可扩展版）

采用轻量 Gateway 抽象，避免 UI 未来大改。

### 4.1 抽象接口

定义 `MemoryGateway`（示意）：

- `listMemories(params)`
- `updateMemory(input)`
- `deleteMemory(id)`
- `addToKnowledgeGraph(memory)`

### 4.2 本期实现

- `MockMemoryGateway`：返回本地模拟知识数据，支持前端内存态更新与删除。
- `addToKnowledgeGraph`：返回成功并触发 toast（占位）。

### 4.3 后续实现（预留）

- `TemporalGraphGateway`：调用时序知识图谱后端。
- 切换方式：通过配置或注入替换 gateway 实现，页面组件无需重写。

## 5. 文件与模块调整建议

在现有 `frontend/src` 下：

- 新增 `mocks/memories.ts`
  - 提供 8~12 条模拟知识
- 新增 `components/memory/MemoryBubbleItem.tsx`
- 新增 `components/memory/MemoryBubbleList.tsx`
- 新增 `components/memory/MemoryDetailDialog.tsx`
- 新增 `services/memoryGateway.ts`
  - gateway 接口 + mock 实现 + 导出默认实例

改造：

- `pages/MemoryManagementPage.tsx`
  - 用气泡列表替换卡片列表
  - 管理详情弹窗开关和当前选中 memory
  - 触发“加入知识图谱”占位动作

可保留但不在该页使用：

- `components/memory/MemoryCard.tsx`

## 6. 状态与错误处理

- 列表加载：保留 Loading / Error 状态组件。
- mock 模式下仍保留统一错误边界，避免未来切换真实后端时改动大量 UI。
- “加入知识图谱”按钮：
  - 点击后禁用短暂状态
  - 成功提示“已加入知识图谱（模拟）”
  - 失败提示“加入失败，请重试”

## 7. 后续对接时序知识图谱的衔接方案

当后端准备好后，仅需：

1. 实现 `TemporalGraphGateway.addToKnowledgeGraph`，将 memory 映射为后端需要的载荷。
2. 将默认 gateway 从 mock 切换为 temporal 实现。
3. 视后端能力补充状态反馈（例如任务 id、处理进度）。

建议后端接口最小字段：

- `memory_id`
- `title`
- `content`
- `tags`
- `importance`
- `updated_at`

## 8. 验收标准（MVP）

满足以下即通过：

1. `/memories` 页面不再使用卡片，改为聊天气泡一行一条。
2. 点击气泡可打开详情弹窗并看到完整内容。
3. 详情弹窗可执行编辑、删除。
4. 详情弹窗包含“加入知识图谱”按钮，点击有明确反馈（占位）。
5. 页面使用模拟数据可完整跑通交互流程。
6. 数据层已具备 gateway 抽象，后续可替换为时序知识图谱实现。

## 9. 实施顺序

1. 建立 `MemoryGateway` 与 mock 数据
2. 实现气泡列表组件
3. 实现详情弹窗与操作按钮
4. 改造 `MemoryManagementPage` 连接新交互
5. 联调编辑/删除与占位“加入知识图谱”
6. 自测主要流程（浏览、查看、编辑、删除、加入图谱）
