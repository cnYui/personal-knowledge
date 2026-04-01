# 模型配置与对话可观测性设计

## 1. 背景

当前 `personal-knowledge-base` 已经具备：

- 本地聊天页与流式输出
- 基于 `Canvas` 的第一版 Agentic RAG 运行时
- 基础 trace 面板
- 多处模型能力调用：
  - 对话回答
  - 知识图谱构建
  - 文本优化
  - 标题生成

但系统仍存在几类明显问题：

1. 模型配置分散在多个 service 中，存在硬编码与历史字段名混用
2. API Key 无法在页面中统一设置，只能手工改 `.env`
3. 新配置无法做到“保存后立即生效”
4. DeepSeek 等上游错误缺少统一映射，前端无法稳定提示用户
5. 聊天页在回答生成前只有“AI 正在思考...”，没有把执行轨迹可解释地展示出来

本次设计将这几个问题收束为一个子项目：建立全局模型配置中心，新增设置页，并升级聊天页的过程可观测性。

## 2. 目标

本次要完成以下目标：

1. 新增全局模型设置页面
2. 支持设置两个 API Key
   - 对话 API Key
   - 知识库构建 API Key
3. 设置值写回项目 `.env / 配置文件`
4. 保存后立即热更新后端运行时配置
5. 对话、知识构建等链路统一从运行时配置中心读取 Key
6. 统一治理 DeepSeek / 上游模型错误，并在前端弹窗提示
7. 聊天页把“AI 正在思考...”升级为灰色的执行轨迹摘要框
8. 保留现有图一中的详细 trace 面板
9. 顺手清理当前项目里明显的 API 配置硬编码和不规范入口

## 3. 非目标

本次不包含：

1. 多用户级配置隔离
2. 数据库存储模型配置
3. 原始模型思维链展示
4. Provider 市场式切换面板
5. 全量可配置 base_url / model 名称编辑器
6. 复杂权限与密钥管理系统

本次配置明确是 **本地单用户、全局项目级配置**。

## 4. 用户确认过的关键约束

### 4.1 配置作用域

- 项目是本地个人使用
- API Key 为全局项目配置
- 不按浏览器、不按用户隔离

### 4.2 持久化方式

- 配置写回项目 `.env / 配置文件`
- 不写数据库

### 4.3 生效方式

- 保存后立即生效
- 不要求手工重启后端

### 4.4 安全与展示

- 设置页中 API Key 默认掩码显示
- 用户可点击查看 / 编辑

### 4.5 “思维链”定义

这里展示的是：

- 系统执行轨迹
- 检索与工具步骤的可解释摘要

而不是：

- 模型原始推理内容

## 5. 总体方案

推荐采用“**运行时配置中心 + 设置 API + 前端设置页 + 统一错误映射 + 聊天过程摘要层**”的方案。

该方案的核心是把“配置从哪里来”和“当前运行时实际使用什么配置”分开：

- `.env` 作为持久化来源
- `ModelConfigService` 作为运行时生效配置中心

这比直接让每个 service 自己读取 `settings.openai_api_key` / `settings.deepseek_api_key` 更稳定，也更容易满足“立即生效”。

## 6. 架构设计

### 6.1 运行时配置中心

新增 `ModelConfigService`，负责：

1. 启动时从 `.env` 读取配置
2. 在内存中维护当前生效配置
3. 提供统一读取接口给各类模型调用方
4. 保存设置时：
   - 写回 `.env`
   - 刷新运行时缓存
   - 让新请求立即使用新配置

### 6.2 配置流转

整体流转如下：

```text
前端设置页保存
-> PUT /api/settings/model-config
-> 后端校验请求
-> 更新 .env
-> 刷新 ModelConfigService 运行时配置
-> 返回掩码后的当前生效配置
-> 前端提示保存成功
-> 后续聊天 / 知识构建请求立即使用新 Key
```

### 6.3 聊天页思考框

聊天页的可观测性分成两层：

1. **流式灰色过程框**
   - 出现在“AI 正在思考...”原位置
   - 低对比度展示当前执行阶段
   - 显示系统执行轨迹摘要

2. **最终详细 trace 面板**
   - 保留现有展开式 trace 面板
   - 在回答完成后继续展示完整细节

这两层的关系是：

- 灰色框负责“生成中”
- trace 面板负责“生成后复盘”

## 7. 后端模块设计

### 7.1 新增模块

建议新增：

```text
backend/app/schemas/settings.py
backend/app/services/model_config_service.py
backend/app/routers/settings.py
backend/app/core/env_store.py
backend/app/core/model_errors.py
```

### 7.2 各模块职责

#### `model_config_service.py`

职责：

- 管理当前运行时生效配置
- 提供读取接口
- 提供刷新接口
- 提供保存并刷新接口

建议暴露：

- `get_dialog_config()`
- `get_knowledge_build_config()`
- `get_masked_config()`
- `update_config(...)`
- `reload()`

#### `env_store.py`

职责：

- 安全读写 `.env`
- 避免手写字符串替换造成格式破坏
- 负责：
  - 读取现有键值
  - 更新已有键
  - 缺失时追加新键

#### `settings.py`

定义前后端交互需要的 schema：

- `ModelConfigRead`
- `ModelConfigUpdate`
- `MaskedApiKey`
- `ModelConfigStatus`

#### `settings.py` router

新增 API：

- `GET /api/settings/model-config`
- `PUT /api/settings/model-config`

### 7.3 需要改造的现有模块

以下模块要改为通过配置中心读取模型配置，而不再直接散落读取原始设置：

- `backend/app/services/knowledge_graph_service.py`
- `backend/app/services/graphiti_client.py`
- `backend/app/services/text_optimizer.py`
- `backend/app/services/title_generator.py`

必要时还包括：

- 与聊天模型直接调用相关的 service
- 构图链路中直接依赖 `deepseek_api_key` 或 `openai_api_key` 的位置

## 8. 配置模型设计

### 8.1 页面上暴露的两个配置项

设置页面先只暴露两个用户心智清晰的字段：

1. **对话 API Key**
   - 用于聊天回答
   - 包括 AgentNode / KnowledgeGraphService 中的对话模型调用

2. **知识库构建 API Key**
   - 用于知识图谱构建 / 抽取 / 入图等过程
   - 包括 Graphiti 构图链路

### 8.2 与现有配置字段的映射

为了兼容当前项目现状，本次需要把现有字段映射收口：

- 当前对话相关能力大多依赖：
  - `openai_api_key`
  - `openai_base_url`
- 当前知识构建链路大多依赖：
  - `deepseek_api_key`
  - `deepseek_base_url`
  - `deepseek_model`

本次设置页展示为两个逻辑键：

- `dialog_api_key`
- `knowledge_build_api_key`

但后端写回 `.env` 时，需要映射到当前项目仍在使用的底层字段，以避免一次性改动过大。

建议映射如下：

- `dialog_api_key` -> 当前对话链默认使用的 `openai_api_key`
- `knowledge_build_api_key` -> 当前知识构建链默认使用的 `deepseek_api_key`

后续如需继续去历史化，再在 P1/P2 统一命名。

## 9. API 错误治理设计

### 9.1 问题

当前各 service 的异常处理方式并不统一：

- 有的直接抛异常
- 有的返回字符串错误
- 有的把上游错误原样透给前端

这会导致前端很难对 `402`、未配置 Key、网络错误做稳定提醒。

### 9.2 统一错误语义

新增统一模型错误类型，至少覆盖：

- `MODEL_API_KEY_MISSING`
- `MODEL_API_QUOTA_EXCEEDED`
- `MODEL_API_AUTH_FAILED`
- `MODEL_API_RATE_LIMITED`
- `MODEL_API_UPSTREAM_ERROR`
- `MODEL_API_NETWORK_ERROR`

并统一附带：

- `error_code`
- `message`
- `details`
- `provider`
- `retryable`

### 9.3 错误映射规则

至少覆盖以下场景：

1. 未配置 API Key
   - 提示：`尚未配置 API Key，请先前往设置页面完成配置。`

2. DeepSeek `402`
   - 提示：`当前 API Key 可用额度已用完，请更换 Key 或检查账号额度。`

3. 鉴权失败
   - 提示：`API Key 无效或鉴权失败，请检查设置中的 Key 是否正确。`

4. `429`
   - 提示：`请求过于频繁，请稍后再试。`

5. 上游 `5xx`
   - 提示：`模型服务暂时不可用，请稍后重试。`

6. 网络超时 / 连接失败
   - 提示：`无法连接模型服务，请检查网络或服务地址配置。`

### 9.4 前端提示策略

#### 聊天页

- 使用 Snackbar / Alert 弹窗提示
- 当前消息卡片保留简短错误说明

#### 设置页

- 保存失败就地提示
- key 校验失败时高亮对应输入框

#### 上传 / 知识构建页

- 若未配置知识库构建 API Key，直接弹窗提示
- 不再只在控制台报错

## 10. 聊天页过程摘要设计

### 10.1 展示目标

聊天生成过程中，灰色过程框展示的是“人话摘要”，而不是底层原始 JSON。

### 10.2 数据来源

直接复用现有 `agent_trace` 中已经存在或可补充的字段：

- `canvas.events`
- `tool_loop`
- `citation`
- `reference_store`

### 10.3 摘要示例

例如可映射为：

- 正在创建工作流
- Agent 正在分析问题
- 正在查询知识库
- 已找到 3 条图谱证据
- 正在组织最终回答
- 正在整理引用

### 10.4 与现有 trace 面板的关系

- 灰色过程框：生成时展示
- 详细 trace 面板：生成后保留

即：

- 不删除图一中的详细面板
- 只替换图二中的“AI 正在思考...”

## 11. 前端页面设计

### 11.1 设置页

新增一个设置页面，接入现有导航。

页面内容包括：

1. 对话 API Key
2. 知识库构建 API Key

每个配置项支持：

- 掩码显示
- 查看 / 隐藏切换
- 编辑
- 保存

保存后：

- 提示“已保存并立即生效”
- 不要求刷新页面

### 11.2 聊天页

当前 `KnowledgeChatPage` 中的：

- `AI 正在思考...`

替换为：

- 灰色执行轨迹摘要框

并继续保留：

- 最终消息内容
- 详细 trace 面板
- citation 展示

## 12. P0 / P1 排序

### 12.1 P0

必须先做：

1. 后端配置中心
2. 设置 API
3. 对话 / 知识构建链路改接配置中心
4. 统一错误映射
5. 设置页面
6. 聊天页灰色思考框

### 12.2 P1

后续增强项：

1. 设置页增加连接测试按钮
2. 支持更多 provider 配置
3. 支持 base_url / model 名称编辑
4. 更细的错误高亮与字段级校验
5. 更细粒度的过程动画和分阶段展示

## 13. 实施顺序

推荐按以下顺序实现：

1. `ModelConfigService`
2. `.env` 读写能力
3. `GET/PUT /api/settings/model-config`
4. 对话 / 构图链路迁移到配置中心
5. 统一错误映射
6. 设置页
7. 聊天页思考框

这个顺序可以保证：

- 先解决“配置能否正确保存并立即生效”
- 再解决“页面如何展示与提示”

## 14. 风险与控制

### 风险 1：写 `.env` 破坏已有配置格式

控制：

- 独立 `env_store.py`
- 不允许各处自行字符串替换

### 风险 2：配置保存后并未真正热更新

控制：

- 所有模型调用统一从 `ModelConfigService` 读取
- 明确禁止新的业务代码直接散读 `settings.*_api_key`

### 风险 3：错误文案仍然依赖上游原始返回

控制：

- 后端统一错误码
- 前端只消费错误语义，不直接依赖 DeepSeek 原文

### 风险 4：思考框展示过于技术化

控制：

- 灰色过程框只展示“人话摘要”
- 详细 JSON 信息仍放在最终 trace 面板中

## 15. 验收标准

本次设计完成后，应满足：

1. 用户可在设置页配置两个 API Key
2. API Key 默认掩码显示，可查看 / 编辑
3. 设置保存后立即生效，不需重启后端
4. 配置写回 `.env / 配置文件`
5. 聊天页在生成中显示灰色执行轨迹摘要框
6. 聊天页保留现有详细 trace 面板
7. DeepSeek `402`、缺少 Key、鉴权失败、限流、网络错误都有稳定前端提示
8. 明显的模型配置硬编码入口被统一收口

## 16. 结论

本次最合适的落地方式不是继续在现有 service 上打零散补丁，而是建立：

- 运行时配置中心
- 设置 API
- 设置页面
- 统一错误语义
- 对话过程摘要层

这样既能满足“本地个人项目、全局配置、写回 `.env`、立即生效”的约束，也能顺手把当前项目中模型配置的硬编码和不规范入口收掉，为后续继续扩展 provider 和模型设置留出稳定边界。
