# Agent Knowledge Profile Overlay Implementation Plan

> Goal: 在 `personal-knowledge-base` 中为 Agentic RAG 增加一套基于 PostgreSQL 的全局知识画像 overlay，使知识图谱写入成功后可异步刷新画像，并在 `AgentNode` 运行时自动注入最新知识范围摘要。

## 1. 实施原则

1. 固定策略 prompt 不动，动态知识范围以 overlay 形式注入
2. 先打通“持久化 + 刷新任务 + 运行时读取”，再考虑可视化管理
3. 图谱写入路径不被画像刷新阻塞
4. 刷新失败不影响聊天主流程，始终允许回退到上一版 ready 或基础 prompt
5. 第一版只维护一份全局 profile，不引入多 group / 多知识库复杂度

## 2. P0 总目标

P0 完成后，系统应满足：

- PostgreSQL 中存在一份全局 `agent_knowledge_profile`
- 知识图谱写入成功后会异步触发画像刷新
- 10 秒内多次图谱写入只最终刷新一次
- 刷新任务会基于规则统计 + 模型压缩生成 4 类知识画像
- 最新 `ready` 画像会被渲染成 `rendered_overlay`
- `AgentNode` 每次启动时会自动读取最新 overlay 并拼接到固定 prompt
- 刷新失败时，聊天仍可用，并回退到上一版 ready 或基础 prompt

## 3. 重点改动文件

### 后端新增

```text
backend/app/db/models/agent_knowledge_profile.py
backend/app/db/repositories/agent_knowledge_profile_repository.py
backend/app/services/agent_knowledge_profile_service.py
backend/app/services/agent_knowledge_profile_refresh.py
```

### 后端重点修改

```text
backend/app/core/database.py
backend/app/services/agent_prompts.py
backend/app/workflow/nodes/agent_node.py
backend/app/services/knowledge_graph_service.py
backend/app/services/memory_service.py
backend/app/services/graphiti_client.py
```

### 测试文件

```text
backend/tests/services/test_agent_knowledge_profile_service.py
backend/tests/services/test_agent_knowledge_profile_refresh.py
backend/tests/workflow/nodes/test_agent_node.py
backend/tests/test_chat_api.py
```

> 注：具体文件名可根据现有项目风格微调，但职责边界应保持一致。

## 4. 数据模型阶段

### 阶段 1：建立知识画像表与仓储

**目标：** 在 PostgreSQL 中建立全局知识画像的持久化基础。

**任务：**

- 新增 `agent_knowledge_profiles` 表
- 建立对应 ORM/SQLAlchemy 模型
- 建立仓储方法：
  - `get_latest_ready_profile()`
  - `create_building_profile()`
  - `mark_profile_ready()`
  - `mark_profile_failed()`
  - `get_latest_profile()`

**建议字段：**

- `id`
- `profile_type`
- `major_topics`
- `high_frequency_entities`
- `high_frequency_relations`
- `recent_focuses`
- `rendered_overlay`
- `status`
- `error_message`
- `updated_at`

**测试：**

- 建表与读写测试
- `ready / building / failed` 状态流转测试
- 读取最新 ready 记录测试

**完成标准：**

- 能独立读写全局知识画像
- `AgentNode` 之后可直接依赖仓储读取 overlay

## 5. 候选统计阶段

### 阶段 2：实现规则统计候选提取

**目标：** 从当前知识图谱中抽出可供模型压缩的候选摘要。

**任务：**

- 提供一层候选抽取服务，返回结构化候选：
  - `top_entities`
  - `top_relations`
  - `recent_entities`
  - `recent_titles`
- `recent_focuses` 的窗口采用：
  - 最近 50 条成功写入知识图谱的内容
- 候选来源优先考虑：
  - 最近写入的图谱节点/边
  - 连接度高的实体
  - 高频关系

**实现建议：**

- 尽量基于已有 graphiti/图谱读取能力
- 不在这一层做模型总结
- 输出规模受控，避免后续压缩 prompt 过大

**测试：**

- 图谱非空时能产出合理候选
- 图谱很小时也能产出最小可用候选
- 没有足够图谱数据时返回空但不报错

**完成标准：**

- 可稳定输出候选摘要供模型压缩

## 6. 模型压缩阶段

### 阶段 3：实现知识画像生成与 overlay 渲染

**目标：** 基于候选摘要生成 4 类知识画像和最终 overlay。

**任务：**

- 新增知识画像生成 prompt
- 模型输出结构化 JSON：
  - `major_topics`
  - `high_frequency_entities`
  - `high_frequency_relations`
  - `recent_focuses`
- 后端校验输出：
  - 类型正确
  - 每类数量受控
  - 空值过滤
- 将结构化结果渲染成 `rendered_overlay`

**rendered_overlay 要求：**

- 语气克制、简洁
- 明确这是自动生成的知识画像
- 提示 Agent：问题与这些内容相关时，优先考虑调用 `graph_retrieval_tool`

**测试：**

- 正常候选输入下生成画像成功
- 模型输出异常时会失败并记录错误
- `rendered_overlay` 格式稳定

**完成标准：**

- 可从候选摘要得到稳定的 4 类知识画像和 overlay 文本

## 7. 异步刷新阶段

### 阶段 4：挂载图谱写入后的异步刷新任务

**目标：** 在图谱写入成功后自动刷新知识画像，但不阻塞用户操作。

**任务：**

- 找到“重新提交到知识图谱 / 成功写入图谱”的后端成功路径
- 在成功路径后触发知识画像刷新任务
- 加入简单去抖/合并：
  - 10 秒内多次写图谱，只最终执行一次刷新
- 刷新任务的状态流转：
  - 创建 `building`
  - 成功后转 `ready`
  - 失败后转 `failed`

**实现建议：**

- 第一版可先使用应用内异步任务/后台协程
- 不必一开始引入额外任务队列
- 但要把任务逻辑与业务入口解耦，便于未来迁移

**测试：**

- 单次图谱写入会触发刷新
- 短时间多次写入只触发一次最终刷新
- 刷新失败不影响原图谱写入结果

**完成标准：**

- 图谱写入后画像可自动更新
- 用户不会因刷新任务而等待

## 8. 运行时注入阶段

### 阶段 5：AgentNode 注入动态知识画像 overlay

**目标：** 让 Agent 每次对话开始时自动获得最新知识库画像。

**任务：**

- 在 `AgentNode` 里引入知识画像读取服务
- 在构建 system prompt 时：
  - 加载固定策略 prompt
  - 读取最新 `ready` overlay
  - 拼接成运行时最终 prompt
- 如果没有 ready overlay：
  - 回退到固定 prompt

**注意：**

- 不在 `AgentNode` 中做刷新逻辑
- 只做读取和注入
- 保持 `AgentNode` 作为运行时消费者，不变成画像生成器

**测试：**

- 有 overlay 时，Agent 使用拼接后的 prompt
- 无 overlay 时，Agent 正常回退到固定 prompt
- overlay 变化后，新会话可读取新内容

**完成标准：**

- Agent 的起手判断能反映当前知识图谱知识范围

## 9. 容错与稳定性阶段

### 阶段 6：失败兜底和回退

**目标：** 确保画像刷新失败时不会影响聊天主流程。

**任务：**

- 刷新失败时：
  - 保存错误信息
  - 保留历史 ready profile
- 如果从未有成功 profile：
  - 回退到固定 prompt
- 增加日志：
  - refresh started
  - refresh success
  - refresh failed
  - prompt overlay loaded / fallback used

**测试：**

- 刷新异常时聊天仍然成功
- 数据库里有上一版 ready 时会继续使用
- 没有任何 ready 数据时仍能正常聊天

**完成标准：**

- 画像刷新成为增强项，而不是系统单点故障

## 10. API 与验证阶段

### 阶段 7：端到端联调与验证

**目标：** 验证从图谱写入到 Agent 起手判断变化的全链路效果。

**任务：**

- 完整跑通：
  - 记忆写入
  - 重新提交到知识图谱
  - 异步刷新知识画像
  - 新会话读取 overlay
- 做对比验证：
  - 刷新前的 prompt overlay
  - 刷新后的 prompt overlay
- 对话验证：
  - 最近新增知识被纳入 Agent 判断
  - 新增实体能影响检索重点

**完成标准：**

- 知识库变化后，Agent 起手行为可见地更贴合当前图谱

## 11. P1 扩展顺序

P0 完成后，P1 建议按以下顺序推进：

1. 前端展示当前知识画像
2. 增加手动重新生成画像按钮
3. 展示刷新状态和失败原因
4. 优化主题抽取和 recent focus 聚类质量
5. 如果未来出现多知识空间需求，再扩展到多 profile

## 12. 风险控制

### 风险 1：模型输出不稳定

控制：

- 先规则提取候选
- 模型只负责压缩总结
- 后端做结构校验和数量限制

### 风险 2：刷新过于频繁

控制：

- 10 秒去抖/合并
- 第一版只维护全局唯一 profile

### 风险 3：overlay 过长

控制：

- 每类最多固定数量项
- `rendered_overlay` 保持简洁

### 风险 4：图谱读取成本过高

控制：

- 第一版只拉有限候选
- recent 窗口固定为 50 条

## 13. 完成定义

P0 算完成，必须同时满足：

- PostgreSQL 中存在全局知识画像表与 ready 数据
- 图谱写入成功后异步触发画像刷新
- 10 秒内多次写图谱只最终刷新一次
- 最新 overlay 会被 `AgentNode` 自动注入
- 刷新失败不会阻塞聊天
- Agent 起手判断与检索重点能体现新近写入知识
